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
    def test_sensitive_scanner_does_not_flag_tokenizer_metadata(self) -> None:
        self.assertEqual([], sensitive_findings({"tokenizer": "Qwen", "tokenizer_config": {}}))

    def test_sensitive_scanner_flags_real_secret_surfaces(self) -> None:
        findings = sensitive_findings({"authorization": "Bearer example-secret-material"})
        self.assertTrue(findings)

    def test_hf_main_url_requests_blob_metadata(self) -> None:
        self.assertEqual(
            "https://huggingface.co/api/models/vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315?blobs=true",
            hf_url("vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315", "main"),
        )

    def test_hf_exact_revision_url(self) -> None:
        url = hf_url("owner/model", "a3c224bdd97ed6de15baef3524eb590c480e0d78")
        self.assertIn("/revision/a3c224bdd97ed6de15baef3524eb590c480e0d78?blobs=true", url)

    def test_sanitized_ollama_fixture_has_strong_local_representation_identity(self) -> None:
        fixture = json.loads(
            (ROOT / "fixtures/raw/ollama/kv-ground-8b.tags.json").read_text(encoding="utf-8")
        )
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
