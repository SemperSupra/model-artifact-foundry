"""PST fixture dataset identity only: no data acquisition, promotion or PST parsing.

The consumer-owned corpus registries are reviewed separately. This public
contract intentionally does not reference any private consumer repository.
"""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECLARATION = ROOT / "examples" / "benchmarks" / "pst-bodu-pstsdk-four.json"
VALIDATOR = ROOT / "tools" / "validate_benchmark_declaration.py"
spec = importlib.util.spec_from_file_location("foundry_benchmark_validation", VALIDATOR)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

EXPECTED = {
    "unicode-v23-one-message": "9e77f0f7937768506f85eb33b7c114e23ddf3bc7fd5d85226fce56586a8e3618",
    "unicode-v23-zero-message": "3f2b8ebf011ca754b9c2017d264423e173ef1407f460bd4cefde4a6ccc041f8b",
    "ansi-v14-one-message": "587a1ae2785eb218d7d42a98d43ded546aa72670908269d7b3ab25a711a91871",
    "ansi-v14-zero-message": "f1ff591b7441f8fcf78cc6c65a78c5d168763338f2fcdf3df5745e742bd66d04",
}


class PstFixtureIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))

    def test_existing_foundry_validator_accepts_source_declaration(self):
        self.assertEqual(validator.validate(self.declaration), [])
        self.assertEqual(self.declaration["artifact_kind"], "dataset")
        self.assertEqual(self.declaration["materialization_mode"], "manifest-only")

    def test_four_distinct_sha_pinned_components_are_stable(self):
        observed = {
            c["name"]: c["source"]["sha256"]
            for c in self.declaration["components"]
        }
        self.assertEqual(observed, EXPECTED)
        self.assertEqual(len(observed), 4)
        self.assertEqual(len(set(observed.values())), 4)

    def test_sources_are_revision_pinned_and_not_tag_based(self):
        for c in self.declaration["components"]:
            with self.subTest(c["name"]):
                self.assertEqual(c["source"]["provider"], "github")
                revision = c["source"]["exact_revision"]
                self.assertEqual(len(revision), 40)
                self.assertTrue(all(ch in "0123456789abcdef" for ch in revision))
                self.assertIn("/blob/" + revision + "/", c["source"]["locator"])
                self.assertEqual(c["role"], "other")

    def test_public_mirror_and_promotion_not_implicitly_authorized(self):
        self.assertEqual(self.declaration["promotion_policy"]["mode"], "review-required")
        for c in self.declaration["components"]:
            with self.subTest(c["name"]):
                self.assertEqual(c["distribution"], "manifest-only")
                self.assertEqual(c["license"]["status"], "unresolved")
                self.assertFalse(c["license"]["redistribution_permitted"])
        attempted = copy.deepcopy(self.declaration)
        attempted["materialization_mode"] = "mirror"
        for c in attempted["components"]:
            c["distribution"] = "mirror"
        self.assertTrue(any(
            "mirrored component requires verified redistribution permission" in err
            for err in validator.validate(attempted)
        ))


if __name__ == "__main__":
    unittest.main()
