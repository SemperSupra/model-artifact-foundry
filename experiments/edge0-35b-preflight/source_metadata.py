#!/usr/bin/env python3
"""Read-only MAF admission preflight for Edge0 35B pinned source lock; never downloads checkpoint bytes."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

EXPECTED_REPO = "Edge0/Edge0-35B-A3B-preview"
EXPECTED_REV = "e21098e7faa916a00f5493795f12f20497d032bb"
MAX_JSON_BYTES = 3_000_000
SHA = re.compile(r"^[0-9a-f]{64}$")
WEIGHT_PART = re.compile(r"^(?:model-\d{5}-of-\d{5}|lora_edge0_35b|prerouter_edge0_35b)\.safetensors$")
MAX_CANDIDATE_LAYER_BYTES = 9_000_000_000

def no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON member")
        obj[key] = value
    return obj

def parse_json(raw):
    return json.loads(raw, object_pairs_hook=no_duplicate_keys)

def load_json(p):
    f = pathlib.Path(p)
    if f.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("metadata too large")
    return parse_json(f.read_bytes())

def get_hf_meta():
    url = ("https://huggingface.co/api/models/" + EXPECTED_REPO +
           "/revision/" + EXPECTED_REV + "?blobs=true")
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "SemperSupra-MAF-read-only-source-preflight/1",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise ValueError("provider HTTP response not successful")
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("provider response not JSON")
        raw = response.read(MAX_JSON_BYTES+1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("provider JSON exceeds size gate")
    return parse_json(raw)

def validate(lock, meta):
    if not isinstance(lock, dict) or lock.get("repository") != EXPECTED_REPO or lock.get("revision") != EXPECTED_REV:
        raise ValueError("source lock repository/revision mismatch")
    files = lock.get("files")
    if not isinstance(files, dict) or len(files) != 11:
        raise ValueError("exact upstream 11-file lock inventory required")
    if not all(isinstance(p, str) and re.fullmatch(r"[a-zA-Z0-9._-]+", p)
               and SHA.fullmatch(h) for p,h in files.items()):
        raise ValueError("unsafe source file path or SHA")
    if len([n for n in files if WEIGHT_PART.fullmatch(n)]) != 6:
        raise ValueError("missing expected 4 base + 2 adapter weights")
    if not isinstance(meta, dict) or meta.get("sha") != EXPECTED_REV or meta.get("id") != EXPECTED_REPO:
        raise ValueError("provider metadata does not match exact source identity")
    if meta.get("private") is not False or meta.get("gated") not in (False,None) or meta.get("disabled") not in (False,None):
        raise ValueError("private/gated/disabled model is not public-retrievable")
    card = meta.get("cardData") or {}
    if not isinstance(card,dict) or str(card.get("license","")).lower() != "apache-2.0":
        raise ValueError("public license metadata absent or unexpected")
    siblings=meta.get("siblings")
    if not isinstance(siblings,list) or len(siblings)>2000:
        raise ValueError("invalid siblings listing")
    by_name = {}
    for row in siblings:
        if not isinstance(row,dict) or not isinstance(row.get("rfilename"),str):
            raise ValueError("invalid sibling")
        name=row["rfilename"]
        if name in by_name:
            raise ValueError("duplicate sibling names")
        by_name[name]=row
    if not set(files).issubset(by_name):
        raise ValueError("locked source file missing from provider listing")
    lfs_ok=[]
    unverified=[]
    rows=[]
    total=0
    for name in sorted(files):
        row=by_name[name]
        blob=row.get("lfs")
        size=row.get("size")
        if isinstance(blob,dict):
            digest=blob.get("sha256")
            size=blob.get("size",size)
            if digest != files[name]:
                raise ValueError("LFS SHA mismatch for "+name)
            if not isinstance(size,int) or size<1:
                raise ValueError("missing exact LFS size for "+name)
            lfs_ok.append(name)
        else:
            if WEIGHT_PART.fullmatch(name):
                raise ValueError("weight missing independent provider LFS SHA "+name)
            unverified.append(name)
        if isinstance(size,int) and size>=0:
            total+=size
        else:
            size=None
        rows.append({"name":name,"bytes":size,"lfs_sha_verified":name in lfs_ok,
                     "single_layer_under_9gb":size is not None and size < MAX_CANDIDATE_LAYER_BYTES})
    if len([x for x in lfs_ok if WEIGHT_PART.fullmatch(x)]) != 6:
        raise ValueError("not all weight tensors provider SHA verified")
    # This is a SOURCE metadata preflight, NOT redistribution authorization or bytes verified on disk.
    return {
        "schema": "maf-edge0-35b-source-metadata-preflight/v1",
        "source_repository": EXPECTED_REPO,
        "source_revision": EXPECTED_REV,
        "source_locked_files": len(files),
        "provider_lfs_sha_match": len(lfs_ok),
        "metadata_only_files": unverified,
        "weight_safetensors_lfs_verified": 6,
        "observed_known_file_bytes": total,
        "largest_locked_file_bytes": max((v["bytes"] or 0) for v in rows),
        "all_locked_files_under_9gb": all(v["single_layer_under_9gb"] for v in rows),
        "files": rows,
        "model_weights_downloaded": False,
        "redistribution_approved": False,
        "oci_published": False,
        "consumer_qualified": False,
    }


SMALL_BYTE_ALLOWLIST = frozenset({
    "chat_template.jinja", "config.json", "generation_config.json",
    "model.safetensors.index.json",
})
MAX_SMALL_FILE_BYTES = 300_000

def verify_small_bytes(lock, receipt, opener=urllib.request.urlopen):
    # Fetch *only* four tiny public metadata files. The ~19.7GB weights and
    # 20MB tokenizer are never downloaded; tokenizer has independently matched LFS metadata.
    missing = set(receipt["metadata_only_files"])
    if missing != SMALL_BYTE_ALLOWLIST:
        raise ValueError("unexpected files in small-byte allowlist: "+repr(sorted(missing)))
    rows = {row["name"]:row for row in receipt["files"]}
    checked=[]
    total=0
    for name in sorted(missing):
        size=rows[name]["bytes"]
        if not isinstance(size,int) or not (0 < size <= MAX_SMALL_FILE_BYTES):
            raise ValueError("unbounded or unknown small-file size for "+name)
        url=("https://huggingface.co/" + EXPECTED_REPO + "/resolve/" +
             EXPECTED_REV + "/" + name + "?download=true")
        request=urllib.request.Request(url,headers={
            "User-Agent":"SemperSupra-MAF-read-only-small-file-hash/1"})
        with opener(request,timeout=20) as stream:
            payload=stream.read(MAX_SMALL_FILE_BYTES+1)
        if len(payload)!=size or hashlib.sha256(payload).hexdigest()!=lock["files"][name]:
            raise ValueError("exact small-file SHA256/size mismatch for "+name)
        checked.append(name)
        total+=len(payload)
    receipt["small_file_byte_sha256_verified"]=checked
    receipt["small_file_verified_bytes"]=total
    receipt["eleven_locked_hashes_cross_verified"]=(receipt["provider_lfs_sha_match"]==7 and
                                                      len(checked)==4)
    return receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--lock",required=True)
    p.add_argument("--fetch-small",action="store_true")
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--metadata")
    group.add_argument("--live",action="store_true")
    args=p.parse_args()
    lock=load_json(args.lock)
    meta=get_hf_meta() if args.live else load_json(args.metadata)
    receipt=validate(lock,meta)
    if args.fetch_small:
        if not args.live:raise ValueError("--fetch-small requires exact live metadata")
        receipt=verify_small_bytes(lock,receipt)
    receipt["gha_sha"]=os.getenv("GITHUB_SHA")
    receipt["model_source_lock_sha256"]=hashlib.sha256(pathlib.Path(args.lock).read_bytes()).hexdigest()
    line="MAF_EDGE0_READONLY_PREFLIGHT="+json.dumps(receipt,sort_keys=True,separators=(",",":"))
    print(line,flush=True)
    summary=os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f:f.write(line+"\n")

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("MAF_PREFLIGHT_FAIL_CLOSED: "+str(e),file=sys.stderr)
        raise SystemExit(1)
