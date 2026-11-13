"""Offline independent RED oracle: selected cache must not be deleted during repair.

Only original tiny synthetic bytes; fake ORAS, no authentication or network.
"""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def import_hydrator():
    spec = importlib.util.spec_from_file_location("foundry_hydrate_under_test", ROOT / "tools" / "hydrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CacheReplacementRed(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="maf-cache-red-")
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.cache = self.root / "cache"
        self.bundle = self.root / "upstream-bundle"
        self.bundle.mkdir()
        self.hydrator = import_hydrator()
        self.logical_id = "fixture/small"
        self.digest = "sha256:" + "0" * 64
        model_data = b"MAF original public synthetic test payload\n"
        archive = self.bundle / "model.tar.gz"
        with tarfile.open(archive, mode="w:gz") as tar:
            entry = tarfile.TarInfo(name="weights.bin")
            entry.size = len(model_data)
            tar.addfile(entry, io.BytesIO(model_data))
        manifest = {
            "schema_version": 1,
            "logical_id": self.logical_id,
            "upstream": {"exact_revision": "fixture-revision-20261113"},
            "archive": {"sha256": sha(archive.read_bytes())},
            "files": [{"path": "weights.bin", "size_bytes": len(model_data), "sha256": sha(model_data)}],
        }
        (self.bundle / "bundle-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.bundle / "NOTICE.txt").write_text("Synthetic test only\n", encoding="utf-8")
        self.catalog = self.root / "catalog.json"
        self.catalog.write_text(json.dumps({"artifacts": {self.logical_id: {
            "approved_digest": self.digest,
            "oci_repository": "ghcr.io/example.invalid/original-synthetic",
            "upstream_exact_revision": "fixture-revision-20261113",
        }}}), encoding="utf-8")
        self.calls = []

    def fake_oras(self, args, check=False):
        self.assertEqual(args[1], "pull")
        self.assertEqual(args[2], "ghcr.io/example.invalid/original-synthetic@" + self.digest)
        dest = Path(args[-1])
        self.calls.append(tuple(args))
        for source in self.bundle.iterdir():
            shutil.copy2(source, dest / source.name)
        return subprocess.CompletedProcess(args, 0)

    def hydrate(self):
        with mock.patch.object(self.hydrator.subprocess, "run", side_effect=self.fake_oras):
            return self.hydrator.hydrate(self.catalog, self.logical_id, self.cache, "oras")

    def test_red_selected_cache_path_must_not_be_removed_during_marker_repair(self):
        first = self.hydrate()
        self.assertTrue((first / "weights.bin").is_file())
        selected = self.cache / "selected" / "fixture__small.json"
        self.assertTrue(selected.is_file())
        final_dir = first.parent
        # Simulate marker loss after consumer selection, while bytes are still intact.
        (final_dir / ".verified.json").unlink()
        removed = []
        original_rmtree = shutil.rmtree

        def observe_deletion(path, *args, **kwargs):
            if Path(path) == final_dir:
                removed.append(str(path))
            return original_rmtree(path, *args, **kwargs)

        with mock.patch.object(self.hydrator.shutil, "rmtree", side_effect=observe_deletion):
            self.hydrate()
        self.assertFalse(removed, "SELECTED_CACHE_DELETION: repair removed an in-use stable digest path")

    def test_control_verified_warm_cache_requires_no_oras(self):
        first = self.hydrate()
        with mock.patch.object(self.hydrator.subprocess, "run", side_effect=AssertionError("warm hit contacted registry")):
            again = self.hydrator.hydrate(self.catalog, self.logical_id, self.cache, "oras")
        self.assertEqual(first, again)

    def test_control_changed_model_bytes_fail_integrity(self):
        first = self.hydrate()
        (first / "weights.bin").write_bytes(b"tampered-bytes")
        with self.assertRaisesRegex(RuntimeError, "(size mismatch|hash mismatch)"):
            self.hydrator.hydrate(self.catalog, self.logical_id, self.cache, "oras")


if __name__ == "__main__":
    unittest.main()
