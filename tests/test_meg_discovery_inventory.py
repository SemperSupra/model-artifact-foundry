"""Read-only metadata audit: discovery does not equal Foundry acquisition."""
import json
from pathlib import Path
from urllib.parse import urlsplit
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "discovery/meg-iclr2026/artifacts.json"
ALLOWED_STATES = {"source_verified", "unlocated"}
ALLOWED_ROUTES = {
    "candidate-review-only", "hold-public-redistribution",
    "hold-license-and-hash", "hold-license-and-identity",
    "hold-redistribution", "hold-unavailable",
}


class MeGDiscoveryContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(FILE.read_text(encoding="utf-8"))
        cls.records = cls.manifest["artifact_records"]

    def test_discovery_never_claims_a_model_acquisition(self):
        doc = self.manifest
        self.assertEqual(doc["schema"], "foundry.discovery.meg-iclr2026/v1")
        self.assertEqual(doc["as_of"], "2026-11-12")
        policy = doc["foundry_policy"]
        for key in ("bytes_acquired", "oci_published", "promoted", "published_original_meg_weights_verified"):
            self.assertIs(policy[key], False)
        self.assertIs(policy["source_discovery_only"], True)

    def test_no_duplicate_or_unversioned_foundry_approval(self):
        ids = [x["id"] for x in self.records]
        self.assertGreaterEqual(len(ids), 15)
        self.assertEqual(len(ids), len(set(ids)))
        for record in self.records:
            with self.subTest(artifact=record["id"]):
                self.assertTrue(record["id"].startswith("meg/"))
                self.assertIn(record["status"], ALLOWED_STATES)
                self.assertIn(record["disposition"], ALLOWED_ROUTES)
                self.assertTrue(record["blocks"])
                self.assertNotIn("oci_digest", record)
                self.assertNotIn("candidate_manifest", record)
                self.assertNotIn("approved", record)
                self.assertNotIn("downloaded", record)
                if record["status"] == "unlocated":
                    self.assertIsNone(record["source"])
                    self.assertIsNone(record["provider"])
                    self.assertIsNone(record["revision"])
                    self.assertEqual(record["disposition"], "hold-unavailable")
                else:
                    self.assertEqual(urlsplit(record["source"]).scheme, "https")

    def test_pinned_public_model_revisions_and_license_separation(self):
        m = {r["id"]: r for r in self.records}
        phi = m["meg/pretrained/phi2"]
        self.assertEqual(phi["revision"], "810d367871c1d460086d9f82db8696f2e0a0fcd0")
        self.assertEqual(phi["license"], "MIT")
        bert = m["meg/pretrained/bert-base-uncased"]
        self.assertEqual(bert["revision"], "86b5e0934494bd15c9632b12f734a8a67f723594")
        self.assertEqual(bert["license"], "Apache-2.0")
        glm = m["meg/pretrained/glm-4-9b-chat"]
        self.assertEqual(glm["license"], "custom-glm-4")
        self.assertEqual(glm["disposition"], "hold-public-redistribution")

    def test_original_meg_outputs_remain_missing_not_substituted(self):
        rows = [r for r in self.records if r["type"] in (
            "author-checkpoint", "author-optimized-neurons", "author-derived-dataset"
        )]
        self.assertGreaterEqual(len(rows), 6)
        self.assertTrue(all(x["status"] == "unlocated" for x in rows))
        self.assertTrue(all(x["license"] is None for x in rows))
        self.assertEqual(self.manifest["global_search"]["author_outputs_verified_downloadable"], 0)

    def test_dataset_license_remains_explicitly_unverified(self):
        dataset = [r for r in self.records if r["type"] == "raw-benchmark"]
        self.assertEqual(len(dataset), 4)
        for r in dataset:
            self.assertIsNone(r["license"])
            self.assertIn(r["disposition"], ("hold-license-and-hash", "hold-license-and-identity"))

    def test_author_source_is_exact_and_unlicensed(self):
        author = next(r for r in self.records if r["id"] == "meg/code/author-method")
        self.assertEqual(author["revision"], self.manifest["upstream"]["commit"])
        self.assertIsNone(author["license"])
        self.assertEqual(author["disposition"], "hold-redistribution")


if __name__ == "__main__":
    unittest.main()
