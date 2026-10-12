"""Pinned, resumable official weights download. All assets live on GameDrive."""
import json
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

ROOT = Path('/mnt/GameDrive/tiny_dancer')
manifest = ROOT / 'docs/model-source.json'
if manifest.exists():
    source = json.loads(manifest.read_text())
else:
    info = HfApi().model_info('openai/gpt-oss-20b', files_metadata=True)
    source = {'repo': info.id, 'revision': info.sha, 'files': [
        {'name': f.rfilename, 'size': f.size} for f in info.siblings
        if '/' not in f.rfilename and (f.rfilename.endswith(('.safetensors', '.json', '.jinja'))
        or f.rfilename in ('LICENSE', 'README.md', 'USAGE_POLICY'))]}
    manifest.write_text(json.dumps(source, indent=2) + '\n')
print(json.dumps(source, indent=2), flush=True)
snapshot_download(source['repo'], revision=source['revision'],
    local_dir=ROOT / 'models/gpt-oss-20b-original',
    allow_patterns=[f['name'] for f in source['files']], max_workers=3)
print('DOWNLOAD COMPLETE', flush=True)
