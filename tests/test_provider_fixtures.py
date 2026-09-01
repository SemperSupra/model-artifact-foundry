from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from capture_provider_metadata import hf_url, sensitive_findings  # noqa: E402


class ProviderFixtureTests(unittest.TestCase):
    def _fixture(self, relative: str):
        return json.loads((ROOT / "fixtures/raw" / relative).read_text(encoding="utf-8"))

    def test_sensitive_scanner_does_not_flag_tokenizer_metadata(self) -> None:
        self.assertEqual([], sensitive_findings({"tokenizer": "Qwen", "tokenizer_config": {}}))

    def test_sensitive_scanner_flags_real_secret_surfaces(self) -> None:
        self.assertTrue(sensitive_findings({"authorization": "Bearer example-secret-material"}))

    def test_hf_main_url_requests_blob_metadata(self) -> None:
        self.assertEqual(
            "https://huggingface.co/api/models/vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315?blobs=true",
            hf_url("vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315", "main"),
        )

    def test_hf_exact_revision_url(self) -> None:
        url = hf_url("owner/model", "a3c224bdd97ed6de15baef3524eb590c480e0d78")
        self.assertIn("/revision/a3c224bdd97ed6de15baef3524eb590c480e0d78?blobs=true", url)

    def test_hf_source_revision_moved_without_model_payload_drift(self) -> None:
        corrected = self._fixture("huggingface/kv-ground-fe756329.json")
        current = self._fixture("huggingface/kv-ground-main.json")
        self.assertEqual("fe7563292bb52ab6c235fc3c87157e6a14017479", corrected["sha"])
        self.assertEqual("a3c224bdd97ed6de15baef3524eb590c480e0d78", current["sha"])
        self.assertNotEqual(corrected["sha"], current["sha"])
        self.assertEqual("cc-by-nc-sa-4.0", corrected["cardData"]["license"])
        self.assertEqual("cc-by-nc-sa-4.0", current["cardData"]["license"])
        before = {item["rfilename"]: item for item in corrected["siblings"]}
        after = {item["rfilename"]: item for item in current["siblings"]}
        self.assertEqual(set(before), set(after))
        payload_paths = [
            "config.json", "preprocessor_config.json", "tokenizer.json", "tokenizer_config.json",
            "model-00001-of-00004.safetensors", "model-00002-of-00004.safetensors",
            "model-00003-of-00004.safetensors", "model-00004-of-00004.safetensors",
        ]
        for path in payload_paths:
            with self.subTest(path=path):
                self.assertEqual(before[path], after[path])
        self.assertNotEqual(before["README.md"], after["README.md"])

    def test_hf_weight_shards_have_content_hashes(self) -> None:
        fixture = self._fixture("huggingface/kv-ground-fe756329.json")
        siblings = {item["rfilename"]: item for item in fixture["siblings"]}
        expected = {
            "model-00001-of-00004.safetensors": "f164eb94dc6450a8159138c2397e46048da8b44f470783c892dfe2575980f3a6",
            "model-00002-of-00004.safetensors": "f9f313c965fb5ef82ddc511c3e94b9ff3d12cb611a3a0e63b7fa88c413cf16b4",
            "model-00003-of-00004.safetensors": "c312efb2b5b0102241993b3cbdba194f73aac57e9932c8438760190721709fc9",
            "model-00004-of-00004.safetensors": "cf80b49638fabf9e58cea8d9f523cbdfd7696260b87bcfcc4b6f820ee62f8cfc",
        }
        for path, sha256 in expected.items():
            with self.subTest(path=path):
                self.assertEqual(sha256, siblings[path]["lfs"]["sha256"])

    def test_civitai_live_version_exposes_provider_file_identity(self) -> None:
        fixture = self._fixture("civitai/model-version-128713.json")
        self.assertEqual(128713, fixture["id"])
        self.assertEqual(4384, fixture["modelId"])
        self.assertEqual("DreamShaper", fixture["model"]["name"])
        self.assertEqual("Published", fixture["status"])
        self.assertEqual(1, len(fixture["files"]))
        file_info = fixture["files"][0]
        self.assertEqual("dreamshaper_8.safetensors", file_info["name"])
        self.assertEqual("SafeTensor", file_info["metadata"]["format"])
        self.assertEqual("879DB523C30D3B9017143D56705015E15A2CB5628762C11D086FED9538ABD7FD", file_info["hashes"]["SHA256"])

    def test_civitai_legacy_dependency_disappearance_is_preserved(self) -> None:
        fixture = self._fixture("civitai/model-version-131508.status.json")
        self.assertEqual(131508, fixture["request"]["model_version_id"])
        self.assertEqual(404, fixture["http_status"])
        self.assertEqual("http-status-observation", fixture["kind"])

    def test_sanitized_ollama_fixture_has_strong_local_representation_identity(self) -> None:
        fixture = self._fixture("ollama/kv-ground-8b.tags.json")
        self.assertEqual(1, len(fixture["models"]))
        model = fixture["models"][0]
        self.assertRegex(model["digest"], r"^[0-9a-f]{64}$")
        self.assertEqual("gguf", model["details"]["format"])
        self.assertEqual("Q4_K_M", model["details"]["quantization_level"])

    def test_all_public_fixtures_are_json_and_secret_free(self) -> None:
        json_files = sorted((ROOT / "fixtures/raw").rglob("*.json"))
        self.assertTrue(json_files)
        for path in json_files:
            with self.subTest(path=path):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual([], sensitive_findings(value))


if __name__ == "__main__":
    unittest.main()
