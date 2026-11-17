import copy
import unittest
import source_metadata as subject

WEIGHTS=[
 "lora_edge0_35b.safetensors",
 "model-00001-of-00004.safetensors",
 "model-00002-of-00004.safetensors",
 "model-00003-of-00004.safetensors",
 "model-00004-of-00004.safetensors",
 "prerouter_edge0_35b.safetensors"]
SMALL=["chat_template.jinja","config.json","generation_config.json","model.safetensors.index.json","tokenizer.json"]

def fixture():
    names=WEIGHTS+SMALL
    lock={"repository":subject.EXPECTED_REPO,"revision":subject.EXPECTED_REV,
          "files":{name:format(i+1,"064x") for i,name in enumerate(names)}}
    siblings=[]
    for name in names:
        row={"rfilename":name,"size":2048}
        if name in WEIGHTS:
            row["lfs"]={"size":2048,"sha256":lock["files"][name]}
        siblings.append(row)
    meta={"id":subject.EXPECTED_REPO,"sha":subject.EXPECTED_REV,
          "private":False,"gated":False,"disabled":False,
          "cardData":{"license":"apache-2.0"},"siblings":siblings}
    return lock,meta

class Validate(unittest.TestCase):
    def test_normal_metadata_is_partial_not_promotion(self):
        a,b=fixture()
        result=subject.validate(a,b)
        self.assertEqual(result["source_locked_files"],11)
        self.assertEqual(result["weight_safetensors_lfs_verified"],6)
        self.assertEqual(len(result["metadata_only_files"]),5)
        self.assertFalse(result["redistribution_approved"])
        self.assertFalse(result["oci_published"])
    def reject(self,mutate):
        a,b=fixture();mutate(a,b)
        with self.assertRaises(ValueError):subject.validate(a,b)
    def test_wrong_revision(self):
        self.reject(lambda a,b:b.update(sha="f"*40))
    def test_wrong_repository(self):
        self.reject(lambda a,b:b.update(id="attacker/repo"))
    def test_missing_lock_member(self):
        self.reject(lambda a,b:a["files"].pop(SMALL[0]))
    def test_wrong_lfs_sha(self):
        self.reject(lambda a,b:b["siblings"][0]["lfs"].update(sha256="e"*64))
    def test_missing_weight_lfs(self):
        self.reject(lambda a,b:b["siblings"][0].pop("lfs"))
    def test_gated(self):
        self.reject(lambda a,b:b.update(gated="auto"))
    def test_license_mismatch(self):
        self.reject(lambda a,b:b["cardData"].update(license="unknown"))
    def test_duplicate_sibling(self):
        self.reject(lambda a,b:b["siblings"].append(copy.deepcopy(b["siblings"][0])))
    def test_missing_provider_file(self):
        self.reject(lambda a,b:b["siblings"].pop())
    def test_invalid_size(self):
        self.reject(lambda a,b:b["siblings"][0]["lfs"].update(size=-1))
    def test_path_traversal(self):
        self.reject(lambda a,b:a["files"].update({"../escape":a["files"].pop(SMALL[0])}))
    def test_duplicate_json_field(self):
        with self.assertRaises(ValueError):
            subject.parse_json(b'{"a":1,"a":2}')
    def test_proposed_layer_requires_size(self):
        a,b=fixture();b["siblings"][-1].pop("size")
        result=subject.validate(a,b)
        self.assertFalse(result["all_locked_files_under_9gb"])
    def test_manifest_size_bound(self):
        a,b=fixture();b["siblings"][0]["lfs"]["size"]=9_000_000_001
        result=subject.validate(a,b)
        self.assertFalse(result["all_locked_files_under_9gb"])

    def test_small_verified_payloads(self):
        import hashlib
        import io
        import urllib.parse
        a,b=fixture()
        payloads={}
        for row in b["siblings"]:
            if row["rfilename"] in subject.SMALL_BYTE_ALLOWLIST:
                name=row["rfilename"]
                data=("exact-public-"+name).encode()
                payloads[name]=data
                row["size"]=len(data)
                a["files"][name]=hashlib.sha256(data).hexdigest()
        def read(req,timeout):
            name=urllib.parse.unquote(urllib.parse.urlsplit(req.full_url).path.rsplit("/",1)[-1])
            return io.BytesIO(payloads[name])
        r=subject.validate(a,b)
        r=subject.verify_small_bytes(a,r,opener=read)
        self.assertTrue(r["eleven_locked_hashes_cross_verified"])
        self.assertEqual(r["small_file_verified_bytes"],sum(len(x) for x in payloads.values()))
    def test_small_file_byte_tampering_rejected(self):
        import hashlib
        import io
        a,b=fixture()
        for row in b["siblings"]:
            if row["rfilename"] in subject.SMALL_BYTE_ALLOWLIST:
                payload=row["rfilename"].encode()
                row["size"]=len(payload)
                a["files"][row["rfilename"]]=hashlib.sha256(payload).hexdigest()
        r=subject.validate(a,b)
        with self.assertRaises(ValueError):
            subject.verify_small_bytes(a,r,opener=lambda request,timeout:io.BytesIO(b"wrong"))
    def test_small_file_unknown_size_rejected(self):
        import io
        a,b=fixture()
        for row in b["siblings"]:
            if row["rfilename"]=="chat_template.jinja":
                row.pop("size")
        r=subject.validate(a,b)
        with self.assertRaises(ValueError):
            subject.verify_small_bytes(a,r,opener=lambda request,timeout:io.BytesIO(b"anything"))
if __name__=="__main__":unittest.main()
