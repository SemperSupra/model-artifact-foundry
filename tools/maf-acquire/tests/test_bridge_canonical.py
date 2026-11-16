"""No upstream network, no third-party models, no promotions or registry writes."""
from __future__ import annotations
import copy,hashlib,importlib.util,json,pathlib,os,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('bridge',ROOT/'tools/maf-acquire/bridge_canonical.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
W=json.loads((ROOT/'examples/test-fixtures/r008-hf-public-safetensors.json').read_text())
PAYLOAD=b'original deterministic neutral fixture bytes'

def fixture():
    w=copy.deepcopy(W);w['files'][0]['sha256']=hashlib.sha256(PAYLOAD).hexdigest();w['files'][0]['max_bytes']=256
    d={'Status':'STAGED_VERIFIED_NOT_PROMOTED','FoundryStatus':'CANDIDATE_ONLY','IdentityKind':'file-sha256',
      'Source':{'provider':w['source']['provider'],'repository':w['source']['repository'],'revision':w['source']['discovery_ref'],'access':'public-ungated'},
      'Files':[{'path':'model.safetensors','sha256':w['files'][0]['sha256'],'bytes':len(PAYLOAD)}]}
    return w,d

class Bridge(unittest.TestCase):
    def setup(self):
        t=tempfile.TemporaryDirectory();p=pathlib.Path(t.name);(p/'model.safetensors').write_bytes(PAYLOAD)
        self.addCleanup(t.cleanup);return p
    def test_canonical_matches_existing_foundry_function(self):
        p=self.setup();w,r=fixture();result=mod.bridge(w,r,p)
        self.assertEqual(result['status'],'CANDIDATE_CONTENT_DIGEST_COMPUTED_ONLY_NOT_APPROVED')
        self.assertFalse(result['adopted'])
        self.assertRegex(result['canonical_content_manifest_digest'],r'^sha256:[a-f0-9]{64}$')
    def test_go_claim_alone_insufficient(self):
        p=self.setup();w,r=fixture();r['Files'][0]['sha256']='0'*64
        self.assertRaises(mod.Hold,mod.bridge,w,r,p)
    def test_source_revision_mismatch(self):
        p=self.setup();w,r=fixture();r['Source']['revision']='b'*40
        self.assertRaises(mod.Hold,mod.bridge,w,r,p)
    def test_mutated_bytes(self):
        p=self.setup();w,r=fixture();(p/'model.safetensors').write_bytes(b'altered')
        self.assertRaises(mod.Hold,mod.bridge,w,r,p)
    def test_no_self_approved(self):
        p=self.setup();w,r=fixture();w['approval']='APPROVED'
        self.assertRaises(mod.Hold,mod.bridge,w,r,p)
    def test_no_symlink(self):
        p=self.setup();w,r=fixture();(p/'model.safetensors').unlink();(p/'model.safetensors').symlink_to('/etc/hosts')
        self.assertRaises(mod.Hold,mod.bridge,w,r,p)
    def test_no_external_hardlink(self):
        p=self.setup();w,r=fixture();outside=self.setup();(p/'model.safetensors').unlink();os.link(outside/'model.safetensors',p/'model.safetensors')
        self.assertRaises(mod.Hold,mod.bridge,w,r,p)
    def test_missing_binary(self):
        p=self.setup();w,r=fixture();(p/'model.safetensors').unlink()
        self.assertRaises(FileNotFoundError,mod.bridge,w,r,p)

if __name__=='__main__':unittest.main()
