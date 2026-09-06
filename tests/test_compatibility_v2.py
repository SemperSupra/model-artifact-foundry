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


matcher = load_module("compatibility_match", "tools/compatibility_match.py")
linter = load_module("public_metadata_lint", "tools/public_metadata_lint.py")
ARTIFACT = json.loads((ROOT / "examples/compatibility/faster-whisper-tiny-v2.json").read_text())
ENV = json.loads((ROOT / "examples/compatibility/environment-linux-x86_64-cpu-ctranslate2.json").read_text())


class CompatibilityTests(unittest.TestCase):
    def test_public_validation_matches_existing_faster_whisper_proof(self):
        result = matcher.match(ARTIFACT, ENV)
        self.assertEqual(result["result"], "publicly-validated")
        self.assertEqual(result["artifact_digest"], "sha256:f2d664ae986b0b0598037a9f0b929fd0b0b748871474a06c84658c1f2a1a4b42")

    def test_hard_backend_mismatch_is_incompatible(self):
        env = json.loads(json.dumps(ENV))
        env["accelerator"]["backend"] = "metal"
        result = matcher.match(ARTIFACT, env)
        self.assertEqual(result["result"], "incompatible")

    def test_missing_required_version_is_unqualified(self):
        env = json.loads(json.dumps(ENV))
        env["runtime"]["framework_version"] = None
        result = matcher.match(ARTIFACT, env)
        self.assertEqual(result["result"], "unqualified")

    def test_private_pass_upgrades_matching_environment_only(self):
        overlay = {
            "schema_version": 1,
            "artifact_digest": ARTIFACT["artifact_digest"],
            "records": [{
                "profile_id": "private-cpu-proof-v1",
                "environment": {
                    "platform": {"os_family": "linux", "architecture": "x86_64"},
                    "accelerator": {"backend": "cpu", "vendor": None, "model_class": None, "memory_mib": None, "driver_version": None},
                    "runtime": {"family": "ctranslate2", "framework_version": "4.6.0", "backend_runtime_version": None, "container_digest": None},
                },
                "validation": {"claim": "privately-validated", "result": "passed"},
            }],
        }
        result = matcher.match(ARTIFACT, ENV, overlay)
        self.assertEqual(result["result"], "privately-validated")

        different = json.loads(json.dumps(ENV))
        different["runtime"]["framework_version"] = "4.7.0"
        result = matcher.match(ARTIFACT, different, overlay)
        self.assertNotEqual(result["result"], "privately-validated")

    def test_wrong_digest_private_overlay_does_not_upgrade(self):
        overlay = {"schema_version": 1, "artifact_digest": "sha256:" + "0" * 64, "records": []}
        result = matcher.match(ARTIFACT, ENV, overlay)
        self.assertEqual(result["result"], "publicly-validated")


class PrivacyLintTests(unittest.TestCase):
    def test_clean_public_metadata_passes(self):
        text = '{"repository":"Systran/faster-whisper-tiny","runtime":"ctranslate2"}'
        self.assertEqual(linter.lint_text(text), [])

    def test_local_configuration_leaks_are_detected(self):
        text = 'HOME=/home/alice\nserver=192.168.1.20\ndevice=GPU-12345678-1234-1234-1234-123456789abc\n'
        kinds = {item["kind"] for item in linter.lint_text(text)}
        self.assertIn("environment-dump", kinds)
        self.assertIn("unix-home-path", kinds)
        self.assertIn("rfc1918-ip", kinds)
        self.assertIn("gpu-device-uuid", kinds)


if __name__ == "__main__":
    unittest.main()
