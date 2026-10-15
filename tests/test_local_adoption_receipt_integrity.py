import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from adopt_local_artifact import adopt_file_records, verify_local_adoption_receipt

REV="0aee81d5fd9275c0582e545bf3a56944b1e75679"
D={
  "logical_id":"document/surya-layout2",
  "source":{"provider":"huggingface","repository":"datalab-to/surya_layout2"},
  "access":{"mode":"restricted"}
}
FILES=[
 {"path":"LICENSE","size_bytes":14744,"sha256":"a"*64},
 {"path":"model.safetensors","size_bytes":141988186,"sha256":"b"*64}
]
class LocalManifestReceiptVerification(unittest.TestCase):
    def receipt(self):
        r=adopt_file_records(D,copy.deepcopy(FILES),REV)
        return r,r["artifact_identity"]["digest"]
    def test_valid_canonical_received_content_identity(self):
        r,d=self.receipt()
        res=verify_local_adoption_receipt(r,d)
        self.assertEqual(res["result"],"RECEIPT_INTEGRITY_PASS_NOT_CACHE_BYTE_REHASH")
        self.assertEqual(res["artifact_identity"]["digest"],d)
        self.assertFalse(res["public_publish_allowed"])
    def test_forged_file_hash_with_unmodified_identity_rejected(self):
        r,d=self.receipt()
        r["files"][1]["sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"do not match"):
            verify_local_adoption_receipt(r,d)
    def test_legacy_hf_adopter_order_is_valid_but_swapped_order_changes_digest(self):
        # Existing native HF os.walk traversal is deterministic but may not
        # be globally alphabetic; the already-frozen digest hashes that order.
        record,d=self.receipt()
        ordered=copy.deepcopy(record)
        ordered["files"].reverse()
        from adopt_local_artifact import content_manifest_digest
        new_material={"schema_version":1,"logical_id":ordered["logical_id"],
                      "upstream":ordered["upstream"],"files":ordered["files"]}
        approved_digest=content_manifest_digest(new_material)
        ordered["artifact_identity"]["digest"]=approved_digest
        result=verify_local_adoption_receipt(ordered,approved_digest)
        self.assertEqual(result["artifact_identity"]["digest"],approved_digest)
        with self.assertRaises(ValueError):
            verify_local_adoption_receipt(ordered,d)

    def test_unexpected_canonical_but_unapproved_digest_rejected(self):
        r,d=self.receipt()
        with self.assertRaises(ValueError):
            verify_local_adoption_receipt(r,"sha256:"+"9"*64)
    def test_bad_paths_order_size_and_hold(self):
        bads=[]
        r,d=self.receipt()
        z=copy.deepcopy(r);z["files"][1]["path"]="../secret";bads.append(z)
        z=copy.deepcopy(r);z["files"].reverse();bads.append(z) # old headline digest now mismatches
        z=copy.deepcopy(r);z["files"][0]["size_bytes"]=True;bads.append(z)
        z=copy.deepcopy(r);z["files"][1]["size_bytes"]=-1;bads.append(z)
        z=copy.deepcopy(r);z["redistribution"]["public_publish_allowed"]=True;bads.append(z)
        z=copy.deepcopy(r);z["artifact_identity"]["kind"]="oci";bads.append(z)
        z=copy.deepcopy(r);z["access"]["mode"]="public";bads.append(z)
        z=copy.deepcopy(r);z["upstream"]["exact_revision"]="main";bads.append(z)
        z=copy.deepcopy(r);z["files"].append(copy.deepcopy(z["files"][0]));bads.append(z)
        z=copy.deepcopy(r);z["files"][1]["path"]="/etc/passwd";bads.append(z)
        z=copy.deepcopy(r);z["files"][1]["path"]="foo\\\\evil";bads.append(z)
        for i,bad in enumerate(bads):
            with self.subTest(i=i), self.assertRaises(ValueError):
                verify_local_adoption_receipt(bad,d)
if __name__=="__main__":unittest.main()
