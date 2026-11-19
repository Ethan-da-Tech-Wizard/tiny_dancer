# ==============================================================================
# app/patches.py - the apply_patch tool: small exact-context file edits
#
# Role in the app: app/tools.py runs apply_patch() in a worker thread for the
# model's apply_patch tool call. The format is a reduced version of the
# "*** Begin Patch" format models are trained on: Add File sections (full new
# content) and Update File sections made of @@ chunks with space/-/+ prefixed
# lines. Deleting or renaming files is deliberately unsupported (those need an
# explicit user-authorized tool).
#
# Design decisions: all-or-nothing. Every section is parsed and matched against
# the CURRENT file contents first (each context must match exactly once, so an
# ambiguous patch is rejected instead of guessing), every target is re-read to
# detect concurrent changes, backups of all existing files are copied, and only
# then are files replaced atomically one by one. If any replacement fails the
# already-applied files are rolled back from the backups.
#
# Limits: patch <= 60000 chars, <= 20 files, files <= 2 MB UTF-8, targets must
# be regular files inside the task folder (no '..', no symlinks).
#
# Tests: tests/test_patches.py.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0

"""Small, exact-context file edits using the familiar Begin Patch format."""
import os
import shutil
import uuid
from pathlib import Path


def apply_patch(patch, cwd, backups):
    """Validate and apply a multi-file patch atomically.

    Args:
        patch: patch text starting with '*** Begin Patch' and ending with
            '*** End Patch'.
        cwd: task folder; paths in the patch are relative to it and must stay inside.
        backups: folder under which a 'patch-<uuid>' backup tree is written.
    Returns:
        {'applied': True, 'files': [{'path', 'bytes', 'backup'}...]}.
    Raises:
        ValueError: any syntax, containment, matching or size problem. Nothing is
        modified when this is raised during validation.
        Exception: an I/O failure while writing; earlier files are rolled back first.
    Blocking file I/O, so callers run it with asyncio.to_thread.
    """
    # Phase 1: Pre-validation & parsing
    # Parse header boundaries and ensure patch payload adheres to standard syntax markers
    if not isinstance(patch,str) or len(patch)>60000:
        raise ValueError('patch must be text of at most 60000 characters')
    lines=patch.splitlines()
    if not lines or lines[0]!='*** Begin Patch' or lines[-1]!='*** End Patch':
        raise ValueError('Use *** Begin Patch and *** End Patch around Add File/Update File sections')
    root=Path(cwd).resolve();prepared=[];seen=set();index=1
    # One iteration per file section. The loop stops before the final
    # '*** End Patch' line.
    while index<len(lines)-1:
        header=lines[index];index+=1
        if header.startswith('*** Add File: '): action='add';name=header[14:]
        elif header.startswith('*** Update File: '): action='update';name=header[17:]
        else: raise ValueError('Supported sections are *** Add File: and *** Update File:; deletion/rename require explicit user-authorized tools')
        relative=Path(name)
        if not name or '..' in relative.parts:
            raise ValueError('Patch paths cannot be empty or contain ..')
        # The containment test below, not the spelling, is the security boundary.
        # File tools already use absolute paths. Accept the same spelling when
        # it resolves inside this task; the containment/symlink checks still apply.
        raw=root/relative;target=raw.resolve()
        if not target.is_relative_to(root) or raw.is_symlink() or target==root:
            raise ValueError('Patch target must be a regular file inside the task folder')
        # Two sections for one file would be applied against stale content.
        if target in seen: raise ValueError('Put all edits for a file in one section')
        seen.add(target)
        if len(seen)>20: raise ValueError('A patch can edit at most 20 files')
        body=[];body_start=index
        while index<len(lines)-1 and not lines[index].startswith(('*** Add File:','*** Update File:','*** Delete File:')):
            body.append(lines[index]);index+=1
        # Add File: content may be '+'-prefixed lines (the patch convention) or raw
        # lines, but not a mix, because a mix usually means the model forgot a prefix
        # on some lines and the file would silently lose or gain characters.
        if action=='add':
            if target.exists(): raise ValueError('Add File cannot replace an existing file')
            if not body: raise ValueError('Add File needs file content')
            prefixed=[line.startswith('+') for line in body]
            if any(prefixed) and not all(prefixed):
                missing=next(n for n,yes in enumerate(prefixed) if not yes)
                raise ValueError(f'Add File mixes formats at patch line {body_start+missing+1}: prefix every content line with +, including blank lines, or use wholly unprefixed literal content. write_file also accepts plain new-file content.')
            old=None;new='\n'.join(line[1:] if all(prefixed) else line for line in body)+'\n'
        else:
            if not body: raise ValueError('Update File needs at least one @@ edit chunk')
            if not target.is_file() or target.stat().st_size>2_000_000:
                raise ValueError('Update File requires an existing UTF-8 file under 2 MB')
            # 'old' is kept to verify nothing changed before writing and to build a backup.
            old=target.read_bytes();text=old.decode('utf-8');original=text.splitlines()
            output=[];cursor=0;part=0
            while part<len(body):
                marker=body[part]
                if not marker.startswith('@@'): raise ValueError('Start each update chunk with @@')
                # Optional text after @@ is a unique line used to skip ahead, which keeps
                # context short in long files.
                anchor=marker[2:].strip();part+=1
                if anchor:
                    matches=[n for n in range(cursor,len(original)) if original[n]==anchor]
                    if len(matches)!=1: raise ValueError('The @@ anchor must match exactly once after the previous chunk')
                    skip=matches[0]+1;output.extend(original[cursor:skip]);cursor=skip
                before=[];after=[];at_end=False
                while part<len(body) and not body[part].startswith('@@'):
                    line=body[part];part+=1
                    # Marks a chunk that must match at the very end of the file.
                    if line=='*** End of File': at_end=True;break
                    if not line or line[0] not in ' +-': raise ValueError('Chunk lines require a space, + or - prefix')
                    if line[0] in ' -': before.append(line[1:])
                    if line[0] in ' +': after.append(line[1:])
                # A pure insertion with no context cannot be placed; require something to
                # locate it.
                if not before and original: raise ValueError('Include unchanged context to locate inserted lines')
                # Exactly-once matching after the previous chunk: zero means the model's idea
                # of the file is stale, several means the edit location is ambiguous.
                matches=[n for n in range(cursor,len(original)-len(before)+1)
                         if original[n:n+len(before)]==before and (not at_end or n+len(before)==len(original))]
                if len(matches)!=1: raise ValueError('Patch context must match exactly once; re-read the relevant lines')
                position=matches[0];output.extend(original[cursor:position]);output.extend(after);cursor=position+len(before)
            # Preserve the file's own line endings and trailing newline so a patch does
            # not show up as a whole-file change in version control.
            output.extend(original[cursor:]);newline='\r\n' if '\r\n' in text else '\n'
            new=newline.join(output)+(newline if text.endswith('\n') else '')
            if old==new.encode('utf-8'): raise ValueError('Patch does not change the file')
        prepared.append({'path':target,'relative':target.relative_to(root),'old':old,'new':new.encode('utf-8')})
    if not prepared: raise ValueError('No file edits in patch')
    # Last check before changing anything: the file must still equal the bytes the
    # patch was prepared against (guards against edits between parse and write).
    # Validate every file before mutating any, and keep durable recovery copies.
    for item in prepared:
        p=item['path']
        if (p.read_bytes() if p.exists() else None)!=item['old']:
            raise ValueError('A file changed while checking the patch; read it again')
    # One backup folder per patch call, mirroring relative paths.
    folder=Path(backups)/('patch-'+uuid.uuid4().hex)
    for item in prepared:
        if item['old'] is not None:
            backup=folder/item['relative'];backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(item['path'],backup);item['backup']=backup
    applied=[]
    # Atomically write bytes to path via a temp sibling, preserving file mode.
    def replace(path,data,mode=None):
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            temp.write_bytes(data)
            if mode is not None: os.chmod(temp,mode)
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
    try:
        for item in prepared:
            mode=item['path'].stat().st_mode & 0o777 if item['old'] is not None else None
            replace(item['path'],item['new'],mode);applied.append(item)
    # Roll back: restore edited files from backups and delete files that this
    # patch created, then re-raise so the model sees the failure.
    except Exception:
        for item in reversed(applied):
            if item['old'] is None: item['path'].unlink(missing_ok=True)
            else: shutil.copy2(item['backup'],item['path'])
        raise
    return {'applied':True,'files':[{'path':str(i['path']),'bytes':len(i['new']),
             'backup':str(i['backup']) if 'backup' in i else None} for i in prepared]}
