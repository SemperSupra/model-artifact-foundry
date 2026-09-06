import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


matcher = load_module("compatibility_match_gated", "tools/compatibility_match.py")
BASE_ARTIFACT = json.loads((ROOT / "examples/compatibility/faster-whisper-tiny-v2.json").read_text())
ENV = json.loads((ROOT / "examples/compatibility/environment-linux-x86_64-cpu-ctranslate2.json").read_text())


class IdentityKindTests(unittest.TestCase):
    def private_overlay(self, kind=None):
        overlay = {
            "schema_version": 1,
            "artifact_digest": BASE_ARTIFACT["artifact_digest"],
            "records": [{
                "profile_id": "synthetic-private-proof",
                "environment": {
                    "platform": {"os_family": "linux", "architecture": "x86_64"},
                    "accelerator": {"backend": "cpu", "vendor": None, "model_class": None, "memory_mib": None},
                    "runtime": {"family": "ctranslate2", "framework_version": "4.6.0", "backend_runtime_version": None},
                },
                "validation": {"claim": "privately-validated", "result": "passed"},
            }],
        }
        if kind is not None:
            overlay["artifact_identity_kind"] = kind
        return overlay

    def test_legacy_artifact_and_overlay_default_to_oci(self):
        result = matcher.match(BASE_ARTIFACT, ENV, self.private_overlay())
        self.assertEqual(result["artifact_identity_kind"], "oci")
        self.assertEqual(result["result"], "privately-validated")

    def test_legacy_oci_overlay_does_not_upgrade_content_manifest(self):
        artifact = json.loads(json.dumps(BASE_ARTIFACT))
        artifact["artifact_identity_kind"] = "content-manifest"
        result = matcher.match(artifact, ENV, self.private_overlay())
        self.assertEqual(result["artifact_identity_kind"], "content-manifest")
        self.assertEqual(result["result"], "publicly-validated")

    def test_content_manifest_overlay_can_upgrade_content_manifest(self):
        artifact = json.loads(json.dumps(BASE_ARTIFACT))
        artifact["artifact_identity_kind"] = "content-manifest"
        result = matcher.match(artifact, ENV, self.private_overlay("content-manifest"))
        self.assertEqual(result["artifact_identity_kind"], "content-manifest")
        self.assertEqual(result["result"], "privately-validated")


if __name__ == "__main__":
    unittest.main()
