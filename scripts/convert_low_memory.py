"""Resume GPT-OSS conversion with bounded memory and atomic per-tensor output shards.

Uses the upstream Picchio quantizers and the same INT4-gs64/INT8 scheme.
Reads BF16 rows through memmaps rather than making multiple full F32 copies.
The first two upstream-converted shards may be reused with --start-shard 2.
"""
import argparse
import gc
import hashlib
import json
import os
import struct
import sys
from pathlib import Path
import numpy as np
from safetensors.numpy import save_file

ROOT = Path('/mnt/GameDrive/tiny_dancer')
sys.path.insert(0, str(ROOT / 'vendor/picchio'))
from convert import quantize_int4, quantize_int8, FP4_LUT
from export_vocab import export_vocab

RAW = ROOT / 'models/gpt-oss-20b-original'
OUT = ROOT / 'models/gpt-oss-20b-picchio-int4'
DTYPES = {'BF16':np.uint16,'F16':np.float16,'F32':np.float32,'U8':np.uint8,'I8':np.int8}

def header(p):
    with p.open('rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]
        return json.loads(f.read(n)), 8 + n

def mapped(p, h, offset, key):
    m = h[key]
    return np.memmap(p, mode='r', dtype=DTYPES[m['dtype']], offset=offset+m['data_offsets'][0], shape=tuple(m['shape']))

def floating(array, dtype):
    if dtype == 'BF16': return (np.asarray(array).astype(np.uint32) << 16).view(np.float32)
    return np.asarray(array).astype(np.float32)

def quant8_chunks(array, dtype):
    rows, cols = array.shape
    q = np.empty((rows,cols),dtype=np.int8)
    scales = np.empty(rows,dtype=np.float32)
    for start in range(0,rows,1024):
        end=min(rows,start+1024)
        chunk=floating(array[start:end],dtype)
        q[start:end],scales[start:end]=quantize_int8(chunk)
    return q,scales

def save(tensors, p):
    temporary=p.with_suffix('.partial')
    save_file(tensors,str(temporary))
    temporary.replace(p)
    print(f'  Saved {p.name}: {p.stat().st_size/1e6:.1f} MB ({len(tensors)} tensors)',flush=True)

def merge_parts(shard_i):
    """The C loader expects contiguous model-NNNNN.safetensors filenames."""
    parts=sorted(OUT.glob(f'model-{shard_i:05d}-part-*.safetensors'))
    if not parts:return
    combined={};sources=[];base=0
    for p in parts:
        h,offset=header(p);length=0
        for key,m in h.items():
            if key=='__metadata__':continue
            if key in combined:raise RuntimeError('Duplicate merge key '+key)
            combined[key]={'dtype':m['dtype'],'shape':m['shape'],'data_offsets':[v+base for v in m['data_offsets']]}
            length=max(length,m['data_offsets'][1])
        sources.append((p,offset,length));base+=length
    encoded=json.dumps(combined,separators=(',',':')).encode()
    encoded+=b' '*((-len(encoded))%8)
    dest=OUT/f'model-{shard_i:05d}.safetensors';temp=dest.with_suffix('.partial')
    digest=hashlib.sha256()
    with temp.open('wb') as out:
        out.write(struct.pack('<Q',len(encoded)));out.write(encoded)
        for p,offset,length in sources:
            with p.open('rb') as f:
                f.seek(offset);remaining=length
                while remaining:
                    block=f.read(min(8*1024*1024,remaining))
                    if not block:raise RuntimeError('Unexpected source EOF')
                    digest.update(block);out.write(block);remaining-=len(block)
        out.flush();os.fsync(out.fileno())
    check=hashlib.sha256()
    with temp.open('rb') as f:
        f.seek(8+len(encoded))
        while block:=f.read(8*1024*1024):check.update(block)
    if check.digest()!=digest.digest():raise RuntimeError('Merged shard payload checksum mismatch')
    temp.replace(dest)
    for p in parts:p.unlink()
    print(f'Merged {len(parts)} parts to {dest.name}; payload checksum verified.',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start-shard',type=int,default=0);args=ap.parse_args()
    OUT.mkdir(exist_ok=True)
    (OUT/'INSTALL_COMPLETE').unlink(missing_ok=True)
    import shutil
    for name in ('config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','generation_config.json','LICENSE','USAGE_POLICY'):
        shutil.copy2(RAW/name,OUT/name)
    originals=sorted(RAW.glob('*.safetensors'))
    for shard_i,p in enumerate(originals):
        prior=OUT/f'model-{shard_i:05d}.safetensors'
        if shard_i<args.start_shard or prior.exists():
            if not prior.exists(): raise RuntimeError(f'Cannot resume: {prior} is missing')
            header(prior)
            print('Reusing',prior.name,flush=True)
            continue
        h,offset=header(p)
        print('Converting',p.name,flush=True)
        for i,key in enumerate(sorted(k for k in h if k!='__metadata__')):
            if key.endswith('_scales') and 'experts' in key: continue
            dest=OUT/f'model-{shard_i:05d}-part-{i:05d}.safetensors'
            if dest.exists():
                header(dest)
                print('Reusing',dest.name,flush=True)
                continue
            print(' ',key,h[key]['shape'],flush=True)
            a=mapped(p,h,offset,key)
            tensors={}
            if key.endswith('_blocks') and 'experts' in key:
                base=key[:-7]
                scale=mapped(p,h,offset,base+'_scales')
                experts,rows,nblocks,_=a.shape
                for e in range(experts):
                    block=np.asarray(a[e]).reshape(rows,nblocks*16)
                    codes=np.empty((rows,nblocks*32),dtype=np.uint8)
                    codes[:,0::2]=block&15;codes[:,1::2]=(block>>4)&15
                    values=FP4_LUT[codes]
                    sc=np.ldexp(np.ones_like(scale[e],dtype=np.float32),np.asarray(scale[e]).astype(np.int32)-127)
                    values.reshape(rows,nblocks,32)[:]*=sc[:,:,None]
                    q,qs=quantize_int4(values)
                    tensors[f'{base}.{e}']=q;tensors[f'{base}.{e}.qs']=qs
                del values,codes,sc,scale,block
            elif len(a.shape)==2 and ('embed_tokens' in key or 'lm_head' in key or 'self_attn' in key) and 'bias' not in key:
                tensors[key],tensors[key+'.qs']=quant8_chunks(a,h[key]['dtype'])
            else:
                tensors[key]=floating(a,h[key]['dtype'])
            save(tensors,dest)
            del tensors,a
            gc.collect()
        merge_parts(shard_i)
    # Check that every expected tensor exists exactly once and no MXFP4 blocks remain.
    expected=set()
    for p in originals:
        h,_=header(p)
        for key,m in h.items():
            if key=='__metadata__':continue
            if key.endswith('_scales') and 'experts' in key:continue
            if key.endswith('_blocks') and 'experts' in key:
                for e in range(m['shape'][0]): expected.update((key[:-7]+f'.{e}',key[:-7]+f'.{e}.qs'))
            else:
                expected.add(key)
                if len(m['shape'])==2 and ('embed_tokens' in key or 'lm_head' in key or 'self_attn' in key) and 'bias' not in key:
                    expected.add(key+'.qs')
    actual=set()
    for p in sorted(OUT.glob('*.safetensors')):
        h,_=header(p);keys=set(h)-{'__metadata__'}
        if keys&actual:raise RuntimeError(f'Duplicate output tensors in {p.name}')
        actual.update(keys)
    if actual!=expected: raise RuntimeError(f'Tensor coverage mismatch: missing={expected-actual}, extra={actual-expected}')
    export_vocab(str(OUT/'tokenizer.json'),str(OUT/'picchio_vocab.bin'))
    manifest={'original_shards':[p.name for p in originals],'output_shards':[p.name for p in sorted(OUT.glob('*.safetensors'))],
        'tensor_count':len(actual),'bytes':sum(p.stat().st_size for p in OUT.glob('*.safetensors')),
        'experts':'INT4 gs64','dense':'INT8 per-row','coverage_verified':True}
    (ROOT/'docs/model-conversion.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'INSTALL_COMPLETE').write_text('All expected tensors verified; vocabulary exported.\n')
    print('CONVERSION COMPLETE',manifest,flush=True)

if __name__=='__main__':main()
