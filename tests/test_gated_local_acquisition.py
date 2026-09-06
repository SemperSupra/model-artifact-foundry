import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


adopter = load_module("adopt_local_artifact", "tools/adopt_local_artifact.py")
DECLARATION_PATH = ROOT / "examples/gated/pyannote-speaker-diarization-3.1.json"
DECLARATION = json.loads(DECLARATION_PATH.read_text())


class GatedLocalAcquisitionTests(unittest.TestCase):
    def make_tree(self, root: Path):
        (root / "config.yaml").write_text("pipeline: synthetic\n", encoding="utf-8")
        (root / "models").mkdir()
        (root / "models" / "weights.bin").write_bytes(b"synthetic-gated-model-bytes")

    def test_content_identity_is_deterministic_and_path_independent(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            root_a = Path(a)
            root_b = Path(b)
            self.make_tree(root_a)
            self.make_tree(root_b)
            rec_a = adopter.adopt(DECLARATION, root_a, "abcdef1234567890")
            rec_b = adopter.adopt(DECLARATION, root_b, "abcdef1234567890")
            self.assertEqual(rec_a, rec_b)
            text = json.dumps(rec_a)
            self.assertNotIn(a, text)
            self.assertNotIn(b, text)
            self.assertNotIn("token", text.lower())
            self.assertEqual(rec_a["redistribution"]["public_publish_allowed"], False)

    def test_revision_changes_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_tree(root)
            first = adopter.adopt(DECLARATION, root, "abcdef1234567890")
            second = adopter.adopt(DECLARATION, root, "abcdef1234567891")
            self.assertNotEqual(first["artifact_identity"]["digest"], second["artifact_identity"]["digest"])

    def test_content_change_changes_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_tree(root)
            first = adopter.adopt(DECLARATION, root, "abcdef1234567890")
            (root / "models" / "weights.bin").write_bytes(b"different")
            second = adopter.adopt(DECLARATION, root, "abcdef1234567890")
            self.assertNotEqual(first["artifact_identity"]["digest"], second["artifact_identity"]["digest"])

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_tree(root)
            try:
                (root / "alias.bin").symlink_to(root / "models" / "weights.bin")
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(RuntimeError):
                adopter.adopt(DECLARATION, root, "abcdef1234567890")

    def test_gated_declaration_fails_closed(self):
        bad = json.loads(json.dumps(DECLARATION))
        bad["acquisition_policy"]["public_harvest"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "decl.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                adopter.load_declaration(p)


if __name__ == "__main__":
    unittest.main()
