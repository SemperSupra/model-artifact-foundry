"""No upstream network, no third-party models, no promotions or registry writes."""
from __future__ import annotations
import copy,hashlib,importlib.util,json,pathlib,os,tempfile,unittest,subprocess,shutil
ROOT=pathlib.Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('bridge',ROOT/'tools/maf-acquire/bridge_canonical.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
W=json.loads((ROOT/'examples/test-fixtures/r008-hf-public-safetensors.json').read_text())
PAYLOAD=b'original deterministic neutral fixture bytes'

def fixture():
    w=copy.deepcopy(W);w['files'][0]['sha256']=hashlib.sha256(PAYLOAD).hexdigest();w['files'][0]['max_bytes']=256
    d={'status':'STAGED_VERIFIED_NOT_PROMOTED','foundry_status':'CANDIDATE_ONLY','identity_kind':'file-sha256',
      'source':{'provider':w['source']['provider'],'repository':w['source']['repository'],'revision':w['source']['discovery_ref'],'access':'public-ungated'},
      'files':[{'path':'model.safetensors','sha256':w['files'][0]['sha256'],'bytes':len(PAYLOAD)}]}
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
        p=self.setup();w,r=fixture();r['files'][0]['sha256']='0'*64
        self.assertRaises(mod.Hold,mod.bridge,w,r,p)
    def test_source_revision_mismatch(self):
        p=self.setup();w,r=fixture();r['source']['revision']='b'*40
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
    def test_actual_go_cli_receipt_schema_with_fake_hf(self):
        """Run actual Go CLI against a local fake hf executable to catch JSON wire mismatch."""
        if not shutil.which('go'):self.skipTest('Go toolchain not installed')
        w,r=fixture();p=self.setup()
        with tempfile.TemporaryDirectory() as tmp:
            bindir=pathlib.Path(tmp)/'bin';bindir.mkdir()
            hf=bindir/'hf';hf.write_text("""#!/usr/bin/env python3
import pathlib,sys
args=sys.argv[1:]
assert args[0]=='download' and '--local-dir' in args
stage=pathlib.Path(args[args.index('--local-dir')+1]);stage.mkdir(parents=True,exist_ok=True)
(stage/'model.safetensors').write_bytes(b'original deterministic neutral fixture bytes')
""")
            hf.chmod(0o700)
            manifest={'schema_version':1,'foundry_logical_id':w['logical_id'],
                      'source_declaration_sha256':hashlib.sha256(json.dumps(w,sort_keys=True).encode()).hexdigest(),
                      'source':{'provider':'huggingface','repository':w['source']['repository'],
                                'revision':w['source']['discovery_ref'],'access':'public-ungated'},
                      'files':w['files'],'promotion':'candidate-only',
                      'license_evidence':'public-neutral-fixture-transport-only'}
            mf=pathlib.Path(tmp)/'request.json';mf.write_text(json.dumps(manifest))
            stage=pathlib.Path(tmp)/'stage';stage.mkdir()
            env={**os.environ,'PATH':str(bindir)+os.pathsep+os.environ['PATH']}
            z=subprocess.run(['go','run','.', '-manifest',str(mf),'-staging-dir',str(stage),'-acquire-public-hf'],
                             cwd=ROOT/'tools/maf-acquire',env=env,check=True,capture_output=True,text=True,timeout=60)
            out=json.loads(z.stdout)
            self.assertEqual(out['status'],'STAGED_VERIFIED_NOT_PROMOTED')
            self.assertEqual(mod.bridge(w,out,stage)['status'],'CANDIDATE_CONTENT_DIGEST_COMPUTED_ONLY_NOT_APPROVED')
    def test_missing_binary(self):
        p=self.setup();w,r=fixture();(p/'model.safetensors').unlink()
        self.assertRaises(FileNotFoundError,mod.bridge,w,r,p)

if __name__=='__main__':unittest.main()
