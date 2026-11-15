"""Offline, first-party synthetic MakeHuman-like nested artifact hydration checks.

No upstream ZIP, model weights, private media or approved catalog is used.
Tests the generic Foundry verifier and optional HF projection (research only).
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("maf_nested_hydrate", ROOT / "tools" / "hydrate.py")
hydrate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hydrate)


class NestedArtifactHydrationTests(unittest.TestCase):
    def new_tree(self, root):
        data = {
            "human/base.mhm": b"original-synthetic-root-model\n",
            "targets/visemes/ah.target": b"0 0.01 0.02 0.03\n",
            "textures/skin/albedo.png": b"not-an-image-source-safe-fixture\n",
        }
        for rel, body in data.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        manifest = {"logical_id": "synthetic-original-nested-fixture", "files": [
            {"path": rel, "size_bytes": len(body),
             "sha256": hashlib.sha256(body).hexdigest()}
            for rel, body in sorted(data.items())
        ]}
        return manifest

    def test_valid_nested_and_flat_hydration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "model"
            root.mkdir()
            manifest = self.new_tree(root)
            hydrate.verify_model_dir(root, manifest)
            single = Path(tmp) / "single"
            single.mkdir()
            (single / "fixture.bin").write_bytes(b"fixture")
            hydrate.verify_model_dir(single, {
                "files": [{"path": "fixture.bin", "size_bytes": 7,
                           "sha256": hashlib.sha256(b"fixture").hexdigest()}]
            })

    def test_nested_content_tamper_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.new_tree(root)
            (root / "targets/visemes/ah.target").write_bytes(b"CORRUPT")
            with self.assertRaisesRegex(RuntimeError, "size mismatch|hash mismatch"):
                hydrate.verify_model_dir(root, manifest)

    def test_nested_extra_and_missing_members_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.new_tree(root)
            (root / "targets/visemes/unused.target").write_bytes(b"unknown")
            with self.assertRaisesRegex(RuntimeError, "file set mismatch"):
                hydrate.verify_model_dir(root, manifest)
            (root / "targets/visemes/unused.target").unlink()
            (root / "targets/visemes/ah.target").unlink()
            with self.assertRaisesRegex(RuntimeError, "file set mismatch"):
                hydrate.verify_model_dir(root, manifest)

    def test_extra_empty_directory_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.new_tree(root)
            (root / "unexpected-empty").mkdir()
            with self.assertRaisesRegex(RuntimeError, "parent set mismatch"):
                hydrate.verify_model_dir(root, manifest)

    def test_symlinked_nested_file_or_parent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "model"
            root.mkdir()
            manifest = self.new_tree(root)
            victim = root / "targets/visemes/ah.target"
            victim.unlink()
            try:
                victim.symlink_to(root / "human/base.mhm")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(RuntimeError, "symlinked"):
                hydrate.verify_model_dir(root, manifest)
            victim.unlink()
            (root / "targets/visemes").rmdir()
            (root / "targets").rmdir()
            (root / "targets").symlink_to(root / "human", target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "symlinked"):
                hydrate.verify_model_dir(root, manifest)

    def test_hardlinked_nested_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "model"
            root.mkdir()
            manifest = self.new_tree(root)
            source = root / "human/base.mhm"
            try:
                os.link(source, Path(tmp) / "external-hardlink")
            except OSError:
                self.skipTest("hardlinks unavailable")
            with self.assertRaisesRegex(RuntimeError, "hardlinked"):
                hydrate.verify_model_dir(root, manifest)

    def test_invalid_manifest_paths_and_aliases_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.new_tree(root)
            for name in ("../escape", "/absolute", "C:/drive", "targets\\bad", "a//b", "a/./b", "a/../b"):
                changed = json.loads(json.dumps(manifest))
                changed["files"][0]["path"] = name
                with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, "unsafe artifact path"):
                    hydrate.verify_model_dir(root, changed)
            changed = json.loads(json.dumps(manifest))
            changed["files"].append(dict(changed["files"][0]))
            with self.assertRaisesRegex(RuntimeError, "duplicate"):
                hydrate.verify_model_dir(root, changed)
            changed = json.loads(json.dumps(manifest))
            changed["files"].append({**changed["files"][0], "path": changed["files"][0]["path"].upper()})
            with self.assertRaisesRegex(RuntimeError, "portable-case-alias"):
                hydrate.verify_model_dir(root, changed)

    def test_nested_hf_cache_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "model"
            root.mkdir()
            manifest = self.new_tree(root)
            hydrate.verify_model_dir(root, manifest)
            cache_root = Path(tmp) / "cache"
            rev = "a" * 40
            output = hydrate.materialize_hf_cache_projection(
                cache_root, "synthetic/original-nested", "main", rev, root, manifest
            )
            self.assertTrue((output / "targets/visemes/ah.target").is_symlink())
            self.assertEqual((output / "targets/visemes/ah.target").read_bytes(),
                             b"0 0.01 0.02 0.03\n")
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                (root / "targets/visemes/ah.target").write_bytes(b"tampered")
                hydrate.verify_model_dir(root, manifest)


if __name__ == "__main__":
    unittest.main()
