from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from normalize_hf_observation import canonical_json, normalize_hf_observation, stable_evidence_ref  # noqa: E402


def load(name: str):
    path = ROOT / "fixtures/raw/huggingface" / name
    return json.loads(path.read_text(encoding="utf-8"))


class HfObservationTests(unittest.TestCase):
    def observation(self, stem: str):
        return normalize_hf_observation(
            load(stem + ".json"),
            load(stem + ".json.provenance.json"),
            fixture_ref="fixtures/raw/huggingface/" + stem + ".json",
            provenance_ref="fixtures/raw/huggingface/" + stem + ".json.provenance.json",
        )

    def test_current_main_exact_identity(self) -> None:
        observation = self.observation("kv-ground-main")
        self.assertEqual("a3c224bdd97ed6de15baef3524eb590c480e0d78", observation["resolved"]["source_revision"])
        self.assertEqual("repository_commit", observation["resolved"]["identity_strength"])

    def test_corrected_weight_exact_identity(self) -> None:
        self.assertEqual(
            "fe7563292bb52ab6c235fc3c87157e6a14017479",
            self.observation("kv-ground-fe756329")["resolved"]["source_revision"],
        )

    def test_observed_at_comes_from_evidence_not_wall_clock(self) -> None:
        provenance = load("kv-ground-main.json.provenance.json")
        self.assertEqual(provenance["captured_at"], self.observation("kv-ground-main")["observed_at"])

    def test_absolute_paths_become_repository_relative_evidence_refs(self) -> None:
        path = Path("/tmp/other-checkout/fixtures/raw/huggingface/kv-ground-main.json")
        self.assertEqual("fixtures/raw/huggingface/kv-ground-main.json", stable_evidence_ref(path))

    def test_files_are_sorted_and_weight_hashes_preserved(self) -> None:
        observation = self.observation("kv-ground-fe756329")
        paths = [item["path"] for item in observation["files"]]
        self.assertEqual(sorted(paths), paths)
        weights = {
            item["path"]: item["lfs"]["sha256"]
            for item in observation["files"]
            if item["path"].endswith(".safetensors") and "lfs" in item
        }
        self.assertEqual(4, len(weights))
        self.assertEqual(
            "f164eb94dc6450a8159138c2397e46048da8b44f470783c892dfe2575980f3a6",
            weights["model-00001-of-00004.safetensors"],
        )

    def test_license_remains_declared_metadata_not_legal_conclusion(self) -> None:
        license_evidence = self.observation("kv-ground-main")["declared_license"]
        self.assertEqual("cc-by-nc-sa-4.0", license_evidence["value"])
        self.assertEqual("declared-metadata-only", license_evidence["interpretation"])

    def test_source_revision_change_does_not_collapse_file_evidence(self) -> None:
        before_observation = self.observation("kv-ground-fe756329")
        after_observation = self.observation("kv-ground-main")
        self.assertNotEqual(
            before_observation["resolved"]["source_revision"],
            after_observation["resolved"]["source_revision"],
        )
        before = {item["path"]: item for item in before_observation["files"]}
        after = {item["path"]: item for item in after_observation["files"]}
        self.assertNotEqual(before["README.md"], after["README.md"])
        for path in [
            "config.json",
            "preprocessor_config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "model-00001-of-00004.safetensors",
            "model-00002-of-00004.safetensors",
            "model-00003-of-00004.safetensors",
            "model-00004-of-00004.safetensors",
        ]:
            with self.subTest(path=path):
                self.assertEqual(before[path], after[path])

    def test_canonical_output_is_byte_deterministic(self) -> None:
        observation = self.observation("kv-ground-main")
        first = canonical_json(observation).encode("utf-8")
        second = canonical_json(observation).encode("utf-8")
        self.assertEqual(first, second)

    def test_schema_file_is_versioned_and_matches_minimum_contract(self) -> None:
        schema = json.loads((ROOT / "schemas/model-observation-v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(1, schema["properties"]["schema_version"]["const"])
        self.assertEqual("huggingface", schema["properties"]["provider"]["const"])
        self.assertIn("resolved", schema["required"])
        self.assertIn("files", schema["required"])


if __name__ == "__main__":
    unittest.main()
