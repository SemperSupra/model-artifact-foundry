import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adopt_local_artifact as local
import adopt_hf_native_snapshot as hf

REV = "0123456789abcdef0123456789abcdef01234567"
DECL = {
    "schema_version": 1,
    "logical_id": "synthetic/hf-snapshot",
    "source": {"provider": "huggingface", "repository": "fixture/model"},
    "access": {"mode": "restricted"},
    "acquisition_policy": {
        "mode": "consumer-authenticated-local", "public_harvest": False,
        "public_redistribution": False, "public_package_publication": False
    },
    "local_identity": {
        "require_exact_upstream_revision": True, "digest_kind": "content-manifest",
        "hash_algorithm": "sha256"
    }
}

class NativeHFAdoption(unittest.TestCase):
    def cache(self, temp):
        root=Path(temp)/"native-hub"
        repo=root/"models--fixture--model"
        snapshot=repo/"snapshots"/REV
        blob=repo/"blobs"
        snapshot.mkdir(parents=True)
        blob.mkdir(parents=True)
        (snapshot/"config.json").write_bytes(b'{"synthetic":true}')
        (blob/"weight-hash").write_bytes(b"synthetic-model-weight")
        (snapshot/"model.safetensors").symlink_to("../../blobs/weight-hash")
        return root, snapshot, blob

    def test_native_identity_equals_local_adoption_without_copy(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            root,snap,blob=self.cache(a)
            record=hf.adopt_native_snapshot(DECL,root,REV)
            normalized=Path(b)
            for item in record["files"]:
                target=normalized/item["path"]
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((snap/item["path"]).read_bytes())
            other=local.adopt(DECL,normalized,REV)
            self.assertEqual(record,other)
            self.assertEqual(record["artifact_identity"]["kind"],"content-manifest")
            self.assertFalse(record["redistribution"]["public_publish_allowed"])
            self.assertNotIn(a,json.dumps(record))
            self.assertNotIn(b,json.dumps(record))
            self.assertEqual(record, hf.adopt_native_snapshot(DECL,root,REV))

    def test_weight_mutation_changes_identity(self):
        with tempfile.TemporaryDirectory() as t:
            root,_,blob=self.cache(t)
            before=hf.adopt_native_snapshot(DECL,root,REV)
            (blob/"weight-hash").write_bytes(b"tamper")
            after=hf.adopt_native_snapshot(DECL,root,REV)
            self.assertNotEqual(before["artifact_identity"]["digest"],after["artifact_identity"]["digest"])

    def test_invalid_revision_repo_and_missing_snapshot_fail(self):
        with tempfile.TemporaryDirectory() as t:
            root,_,_=self.cache(t)
            with self.assertRaisesRegex(ValueError,"40-hex"):
                hf.adopt_native_snapshot(DECL,root,"main")
            bad=json.loads(json.dumps(DECL))
            bad["source"]["repository"]="../outside"
            with self.assertRaises(ValueError): hf.adopt_native_snapshot(bad,root,REV)
            with self.assertRaises(ValueError):
                hf.adopt_native_snapshot(DECL,root,"f"*40)

    def test_symlinks_must_stay_inside_known_blob_roots(self):
        with tempfile.TemporaryDirectory() as t:
            root,snap,_=self.cache(t)
            external=Path(t)/"secret";external.write_text("fake-secret")
            link=snap/"model.safetensors"
            link.unlink();link.symlink_to(external)
            with self.assertRaises(ValueError): hf.adopt_native_snapshot(DECL,root,REV)
            link.unlink();link.symlink_to("../../../../../secret")
            with self.assertRaises((ValueError, FileNotFoundError)):
                hf.adopt_native_snapshot(DECL,root,REV)
            link.unlink();link.symlink_to("config.json")
            with self.assertRaisesRegex(ValueError,"approved HF blobs"):
                hf.adopt_native_snapshot(DECL,root,REV)

    def test_symlinked_directory_and_non_hf_decl_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root,snap,_=self.cache(t)
            (snap/"alias").symlink_to(snap,target_is_directory=True)
            with self.assertRaises(ValueError): hf.adopt_native_snapshot(DECL,root,REV)
            bad=json.loads(json.dumps(DECL))
            bad["source"]["provider"]="https"
            with self.assertRaises(ValueError): hf.adopt_native_snapshot(bad,root,REV)

if __name__=="__main__":unittest.main()
