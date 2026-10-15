#!/usr/bin/env python3
"""Check a frozen Foundry receipt against separately authorized exact digest.

This does not touch/cache/download model bytes and is NOT a compatibility,
license or redistribution grant. Use provider-native adopter beforehand to
rehash actual local bytes; this verifies receipt integrity in a distinct step.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from adopt_local_artifact import verify_local_adoption_receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",type=Path,required=True)
    p.add_argument("--expected-digest",required=True)
    a=p.parse_args()
    print(json.dumps(verify_local_adoption_receipt(
        json.loads(a.receipt.read_text(encoding="utf-8")),a.expected_digest),sort_keys=True))

if __name__=="__main__":main()
