#!/usr/bin/env python3
"""Validate a rights-held, immutable MeG publisher source-location plan.

Metadata only: no HTTP request, original data bytes, OCI publishing,
authorization granting, model execution, or checkpoint extraction.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import urllib.parse

SOURCE_HOST="proceedings.iclr.cc"
OUTER="d8abdd06a77318d0af5f6f3414092eafe3b29a3fe10eb890704d6c237c760d71"
INNER="10f0cad94529f9d1522a34dad9379e6f7e15ea51f9500180fe4f892edffde088"
PREFIX="data_for_our_MeG/"
SHA=re.compile(r"^[a-f0-9]{64}$")
MAX_FILE=100_000_000
MAX_TOTAL=600_000_000

class InvalidIntakePlan(ValueError):
    pass

def validate(plan: dict) -> dict:
    if not isinstance(plan,dict) or plan.get("schema")!="model-artifact-foundry.meg-publisher-source-plan/v1":
        raise InvalidIntakePlan("UNRECOGNIZED_PLAN_SCHEMA")
    if plan.get("state")!="PREHARVEST_RIGHTS_HOLD":
        raise InvalidIntakePlan("UNAPPROVED_STATE")
    url=urllib.parse.urlsplit(plan.get("source_url",""))
    if (url.scheme!="https" or url.hostname!=SOURCE_HOST or url.username or url.password
        or url.query or url.fragment
        or not url.path.endswith("/7926a9c34166da5a6a681cc0fe6d8a28-Supplemental-Conference.zip")):
        raise InvalidIntakePlan("UNAPPROVED_SOURCE_LOCATION")
    if plan.get("outer_sha256")!=OUTER or plan.get("inner_sha256")!=INNER:
        raise InvalidIntakePlan("IMMUTABLE_SOURCE_HASH_CHANGED")
    if plan.get("inner_path")!="code_and_data_for_our_MeG/data_for_our_MeG.zip":
        raise InvalidIntakePlan("UNAPPROVED_NESTED_ARCHIVE")
    if plan.get("outer_compressed_bytes")!=81010254:
        raise InvalidIntakePlan("SOURCE_BYTE_SIZE_CHANGED")
    if plan.get("original_trained_checkpoints_present") is not False:
        raise InvalidIntakePlan("FALSE_CHECKPOINT_DISCOVERY_CLAIM")
    rights=plan.get("rights",{})
    expected_rights={
        "redistribution_rights_verified":False,
        "source_local_inspection_only":True,
        "public_oci_publication_allowed":False,
        "private_acquisition_requires_review":True,
    }
    if rights!=expected_rights:
        raise InvalidIntakePlan("UNAPPROVED_RIGHTS_PROMOTION")
    fulfillment=plan.get("fulfillment",{})
    if fulfillment!={"downloaded_into_foundry":False,"oci_manifest_created":False,
                     "consumer_hydration_allowed":False,"approved":False}:
        raise InvalidIntakePlan("UNSUPPORTED_ACQUISITION_CLAIM")
    files=plan.get("originals")
    if not isinstance(files,list) or len(files)!=18:
        raise InvalidIntakePlan("MISSING_OR_EXTRA_SOURCE_MEMBERS")
    paths=set()
    total=0
    for item in files:
        if not isinstance(item,dict) or set(item)!={"archive_path","sha256","bytes"}:
            raise InvalidIntakePlan("UNEXPECTED_MEMBER_FIELDS")
        path=item["archive_path"]
        if not isinstance(path,str) or not path.startswith(PREFIX) or "\\" in path:
            raise InvalidIntakePlan("UNSAFE_MEMBER_PATH")
        relative=path[len(PREFIX):]
        parsed=PurePosixPath(relative)
        if (parsed.is_absolute() or ".." in parsed.parts or "." in parsed.parts
            or not relative or relative.startswith("/") or path in paths):
            raise InvalidIntakePlan("UNSAFE_OR_DUPLICATE_MEMBER")
        paths.add(path)
        if not isinstance(item["sha256"],str) or not SHA.fullmatch(item["sha256"]):
            raise InvalidIntakePlan("INVALID_MEMBER_DIGEST")
        size=item["bytes"]
        if type(size) is not int or not 0<size<=MAX_FILE:
            raise InvalidIntakePlan("INVALID_MEMBER_SIZE")
        total+=size
        if total>MAX_TOTAL:
            raise InvalidIntakePlan("UNBOUNDED_SOURCE_PAYLOAD")
    if total!=453026585:
        raise InvalidIntakePlan("TOTAL_SOURCE_BYTES_MISMATCH")
    required={"raw_data/rephrase.prompt","edit_data/phi2_zsre_edit.json",
              "new_split_data/zsre_for_bert_train.json","train_familiar/zsre_phi2_fake_id_class.json"}
    if not all(PREFIX+x in paths for x in required):
        raise InvalidIntakePlan("MISSING_CRITICAL_MECHANISM_INPUTS")
    return {
        "schema":"model-artifact-foundry.meg-publisher-intake-validation/v1",
        "state":"PASS_PREHARVEST_RIGHTS_HOLD",
        "source_sha256":OUTER,"member_count":len(files),"total_member_bytes":total,
        "rights_granted":False,"downloaded":False,"oci_approved":False,
        "science_reproduced":False,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--plan",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(validate(json.loads(args.plan.read_text(encoding="utf-8"))),sort_keys=True))

if __name__=="__main__":main()
