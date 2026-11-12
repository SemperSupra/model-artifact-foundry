"""Hostile metadata-only Foundry MeG source-plan validation."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"tools/validate_meg_publisher_intake.py"
PLAN=ROOT/"discovery/meg-iclr2026/publisher-intake-plan.json"
spec=importlib.util.spec_from_file_location("meg_intake",SRC)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SourcePlanTests(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads(PLAN.read_text(encoding="utf-8"))
    def test_exact_source_and_rights_hold_pass(self):
        rec=mod.validate(self.doc)
        self.assertEqual(rec["state"],"PASS_PREHARVEST_RIGHTS_HOLD")
        self.assertEqual(rec["member_count"],18)
        self.assertEqual(rec["total_member_bytes"],453026585)
        self.assertFalse(rec["rights_granted"])
        self.assertFalse(rec["downloaded"])
        self.assertFalse(rec["oci_approved"])
    def test_reject_source_and_rights_mutation(self):
        cases=[
            lambda p:p.update(state="APPROVED"),
            lambda p:p.update(outer_sha256="0"*64),
            lambda p:p.update(inner_sha256="f"*64),
            lambda p:p.update(source_url="http://proceedings.iclr.cc/bad.zip"),
            lambda p:p.update(source_url="https://evil.example/data.zip"),
            lambda p:p.update(original_trained_checkpoints_present=True),
            lambda p:p["rights"].update(public_oci_publication_allowed=True),
            lambda p:p["rights"].update(redistribution_rights_verified=True),
            lambda p:p["fulfillment"].update(downloaded_into_foundry=True),
            lambda p:p["fulfillment"].update(consumer_hydration_allowed=True),
            lambda p:p["fulfillment"].update(approved=True),
        ]
        for i,mut in enumerate(cases):
            p=copy.deepcopy(self.doc)
            mut(p)
            with self.subTest(i=i),self.assertRaises(mod.InvalidIntakePlan):
                mod.validate(p)
    def test_reject_member_path_duplication_and_oversized(self):
        cases=[
            lambda p:p["originals"][0].update(archive_path="data_for_our_MeG/../escape"),
            lambda p:p["originals"][0].update(archive_path="/etc/passwd"),
            lambda p:p["originals"][0].update(archive_path=p["originals"][1]["archive_path"]),
            lambda p:p["originals"][0].update(sha256="bad"),
            lambda p:p["originals"][0].update(bytes=100000001),
            lambda p:p["originals"].pop(),
        ]
        for i,mut in enumerate(cases):
            p=copy.deepcopy(self.doc)
            mut(p)
            with self.subTest(i=i),self.assertRaises(mod.InvalidIntakePlan):
                mod.validate(p)
    def test_not_reconstructed_weights(self):
        self.assertTrue(all("safetensors" not in x["archive_path"] for x in self.doc["originals"]))
        self.assertTrue(self.doc["rights"]["private_acquisition_requires_review"])
        self.assertFalse(self.doc["fulfillment"]["oci_manifest_created"])

if __name__=="__main__":unittest.main()
