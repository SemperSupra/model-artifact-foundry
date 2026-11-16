#!/usr/bin/env python3
"""Public, test-only R008 identity bridge into existing Foundry content-manifest code.

Rehashes staging bytes and joins official Go acquisition receipt to a pinned
public fixture witness; imports canonical_identity_material/content_manifest_digest
from Foundry tools/adopt_local_artifact.py. Never calls adoption, publishes,
authenticates model rights, runs model code, or promotes a candidate.
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, re, stat, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from adopt_local_artifact import canonical_identity_material, content_manifest_digest

_SHA = re.compile(r'[0-9a-f]{64}\Z')
_REV = re.compile(r'[0-9a-f]{40}\Z')

class Hold(ValueError):
    pass


def safe_file(stage: pathlib.Path, rel: str, max_bytes: int) -> tuple[int, str]:
    """Read only a regular, non-symlink, non-hardlinked file under real stage dirs."""
    if not isinstance(rel,str) or not rel or rel.startswith('/') or '\\' in rel or '//' in rel or any(s in ('.','..','') for s in rel.split('/')):
        raise Hold('unsafe relative path')
    if type(max_bytes) is not int or max_bytes < 1 or max_bytes > 2*1024*1024:
        raise Hold('unbounded test file')
    base=stage.absolute()
    if not base.is_dir() or base.is_symlink():
        raise Hold('staging directory missing or symlinked')
    current=base
    for part in rel.split('/')[:-1]:
        current=current/part
        if current.is_symlink() or not current.is_dir():
            raise Hold('symlinked/non-directory ancestor')
    filename=current/rel.split('/')[-1]
    st=os.lstat(filename)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_size>max_bytes:
        raise Hold('unsafe staged member/link/size')
    fd=os.open(filename, os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    try:
        fst=os.fstat(fd)
        if (fst.st_dev,fst.st_ino)!=(st.st_dev,st.st_ino) or fst.st_nlink!=1 or not stat.S_ISREG(fst.st_mode):
            raise Hold('changed stage member after lstat')
        h=hashlib.sha256();n=0
        with os.fdopen(os.dup(fd),'rb') as inp:
            while True:
                chunk=inp.read(min(1048576,max_bytes+1-n))
                if not chunk:break
                h.update(chunk);n+=len(chunk)
                if n>max_bytes:raise Hold('byte budget exceeded')
        if n!=fst.st_size:raise Hold('staged member modified during read')
        return n,h.hexdigest()
    finally:
        os.close(fd)


def bridge(witness:dict, receipt:dict,stage:pathlib.Path)->dict:
    if witness.get('schema_version')!='maf-public-neutral-fixture/r008' or witness.get('status')!='TEST_ONLY_NOT_APPROVED_NOT_MIRRORABLE':raise Hold('not a neutral fixture')
    if witness.get('approval')!='DENIED' or witness.get('package_publication') is not False or witness.get('license_admission')!='UNVERIFIED_NOT_FOR_REDISTRIBUTION':raise Hold('fixture cannot carry approval')
    src=witness.get('source',{})
    if src.get('provider')!='huggingface' or not _REV.fullmatch(str(src.get('discovery_ref',''))):raise Hold('fixture not pinned')
    if receipt.get('status')!='STAGED_VERIFIED_NOT_PROMOTED' or receipt.get('foundry_status')!='CANDIDATE_ONLY' or receipt.get('identity_kind')!='file-sha256':raise Hold('Go source receipt falsely elevated')
    from_go=receipt.get('source',{})
    if from_go.get('provider')!=src['provider'] or from_go.get('repository')!=src['repository'] or from_go.get('revision')!=src['discovery_ref'] or from_go.get('access')!='public-ungated':raise Hold('Go source mismatch')
    files=witness.get('files')
    if not isinstance(files,list) or len(files)!=1:raise Hold('fixture expects one selected file')
    if not isinstance(receipt.get('files'),list) or len(receipt['files'])!=len(files):raise Hold('Go file count mismatch')
    rows=[]
    for item, got in zip(files,receipt['files']):
        if not _SHA.fullmatch(item.get('sha256','')):raise Hold('witness digest invalid')
        if type(item.get('max_bytes')) is not int:raise Hold('witness byte cap invalid')
        n,sha=safe_file(stage,item['path'],item['max_bytes'])
        if n!=got.get('bytes') or sha!=item['sha256'] or sha!=got.get('sha256') or item['path']!=got.get('path'):
            raise Hold('independent selected-file byte witness mismatch')
        rows.append({'path':item['path'],'size_bytes':n,'sha256':sha})
    material=canonical_identity_material(witness,src['discovery_ref'],rows)
    digest=content_manifest_digest(material)
    return {'schema_version':'maf-r008-test-bridge/1','status':'CANDIDATE_CONTENT_DIGEST_COMPUTED_ONLY_NOT_APPROVED',
        'logical_id':witness['logical_id'],'source_revision':src['discovery_ref'],
        'original_file_sha256':rows[0]['sha256'],'files':rows,'canonical_content_manifest_digest':digest,
        'adopted':False,'approved':False,'published':False,'private_bytes':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--witness',type=pathlib.Path,required=True)
    p.add_argument('--go-receipt',type=pathlib.Path,required=True)
    p.add_argument('--stage',type=pathlib.Path,required=True)
    args=p.parse_args();w=json.loads(args.witness.read_text());r=json.loads(args.go_receipt.read_text())
    print(json.dumps(bridge(w,r,args.stage),sort_keys=True,indent=2))

if __name__=='__main__': main()
