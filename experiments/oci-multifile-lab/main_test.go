package main
import (
 "bytes"
 "crypto/sha256"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
var fileNames=[]string{
 "chat_template.jinja","config.json","generation_config.json",
 "lora_edge0_35b.safetensors","model-00001-of-00004.safetensors",
 "model-00002-of-00004.safetensors","model-00003-of-00004.safetensors",
 "model-00004-of-00004.safetensors","model.safetensors.index.json",
 "prerouter_edge0_35b.safetensors","tokenizer.json",
}
func fixture(t *testing.T)(string,string,string){
 t.Helper();root:=t.TempDir();src:=filepath.Join(root,"source");os.Mkdir(src,0700)
 for i,n:=range fileNames {
  data:=bytes.Repeat([]byte(fmt.Sprintf("SYNTHETIC-ONLY-%02d-",i)),64*(i+1))
  if e:=os.WriteFile(filepath.Join(src,n),data,0600);e!=nil{t.Fatal(e)}
 }
 packed:=filepath.Join(root,"packed")
 if e:=pack(src,packed,"synthetic/eleven-files",strings.Repeat("c",40));e!=nil{t.Fatal(e)}
 return src,packed,filepath.Join(root,"cache")
}
func selectFile(cache string)string{return filepath.Join(cache,"selected","synthetic__eleven-files.json")}
func TestFullElevenFileRoundTripAndOfflineIdempotence(t *testing.T){
 src,packed,cache:=fixture(t)
 dest,hit,e:=hydrate(packed,cache);if e!=nil||hit{t.Fatalf("first hydrate: %v %t",e,hit)}
 m,b,e:=readManifest(dest);if e!=nil||len(m.Files)!=11||len(b)==0{t.Fatal("missing exact 11 file manifest")}
 if e:=verifyDir(dest,m);e!=nil{t.Fatal(e)}
 for _,name:=range fileNames{
  a,e:=os.ReadFile(filepath.Join(src,name));if e!=nil{t.Fatal(e)}
  b,e:=os.ReadFile(filepath.Join(dest,name));if e!=nil||!bytes.Equal(a,b){t.Fatal("not bit-exact source and cache")}
 }
 prior,_:=os.ReadFile(selectFile(cache))
 again,hit,e:=hydrate(packed,cache)
 if e!=nil||!hit||again!=dest{t.Fatalf("second hydrate should be offline no-op: %v, %t",e,hit)}
 after,_:=os.ReadFile(selectFile(cache));if !bytes.Equal(prior,after){t.Fatal("selection changed on idempotent no-op")}
}
func TestAllTamperClassesPreserveSelected(t *testing.T){
 modes:=[]string{"bitflip","missing","extra","symlink","duplicate-key","unknown-field","oversize-manifest","bad-path","wrong-size","wrong-sha"}
 for _,mode:=range modes{t.Run(mode,func(t *testing.T){
  _,good,cache:=fixture(t)
  _,_,e:=hydrate(good,cache);if e!=nil{t.Fatal(e)}
  prior,_:=os.ReadFile(selectFile(cache))
  bad:=filepath.Join(t.TempDir(),"bad")
  if e:=os.Mkdir(bad,0700);e!=nil{t.Fatal(e)}
  for _,name:=range append(append([]string{},fileNames...),"manifest.json"){
   b,e:=os.ReadFile(filepath.Join(good,name));if e!=nil{t.Fatal(e)}
   if e:=os.WriteFile(filepath.Join(bad,name),b,0600);e!=nil{t.Fatal(e)}
  }
  mf:=filepath.Join(bad,"manifest.json")
  row:=filepath.Join(bad,fileNames[0])
  data,_:=os.ReadFile(mf)
  switch mode{
  case "bitflip":os.WriteFile(row,[]byte("X"),0600)
  case "missing":os.Remove(row)
  case "extra":os.WriteFile(filepath.Join(bad,"unexpected.bin"),[]byte("X"),0600)
  case "symlink":os.Remove(row);os.Symlink(filepath.Join(bad,fileNames[1]),row)
  case "duplicate-key":data=bytes.Replace(data,[]byte("\u0022schema\u0022:"),[]byte("\u0022schema\u0022:\u0022maf-oci-multifile-lab/v1\u0022, \u0022schema\u0022:"),1)
  case "unknown-field":data=bytes.Replace(data,[]byte("\u0022schema\u0022:"),[]byte("\u0022unapproved\u0022:true, \u0022schema\u0022:"),1)
  case "oversize-manifest":data=append(data,bytes.Repeat([]byte(" "),int(maxManifestBytes))...)
  case "bad-path":data=bytes.Replace(data,[]byte("\u0022name\u0022: \u0022chat_template.jinja\u0022"),[]byte("\u0022name\u0022: \u0022../escape\u0022"),1)
  case "wrong-size":data=bytes.Replace(data,[]byte("\u0022bytes\u0022: 1152"),[]byte("\u0022bytes\u0022: 999"),1)
  case "wrong-sha":
   m,_,_:=readManifest(good);m.Files[0].SHA=strings.Repeat("0",64);data,_=json.Marshal(m)
  }
  if mode=="duplicate-key"||mode=="unknown-field"||mode=="oversize-manifest"||mode=="bad-path"||mode=="wrong-size"||mode=="wrong-sha"{
   if e:=os.WriteFile(mf,data,0600);e!=nil{t.Fatal(e)}
  }
  if _,_,e:=hydrate(bad,cache);e==nil{t.Fatal("malicious candidate accepted")}
  after,_:=os.ReadFile(selectFile(cache));if !bytes.Equal(prior,after){t.Fatal("selected model changed on failed hydration")}
 })}
}
func TestRejectNonRegularSourceAndUnsafeID(t *testing.T){
 src,_,_:=fixture(t)
 if e:=pack(src,filepath.Join(t.TempDir(),"out"),"../unsafe",strings.Repeat("c",40));e==nil{t.Fatal("unsafe ID accepted")}
 if e:=pack(src,filepath.Join(t.TempDir(),"out"),"synthetic/eleven-files","main");e==nil{t.Fatal("mutable upstream revision accepted")}
 if e:=os.Symlink(filepath.Join(src,fileNames[0]),filepath.Join(src,"foreign.bin"));e!=nil{t.Fatal(e)}
 if e:=pack(src,filepath.Join(t.TempDir(),"out"),"synthetic/eleven-files",strings.Repeat("c",40));e==nil{t.Fatal("source symlink accepted")}
}
func TestRejectCorruptExistingBlobWithoutSelectionChange(t *testing.T){
 _,packed,cache:=fixture(t)
 dest,_,e:=hydrate(packed,cache);if e!=nil{t.Fatal(e)}
 prior,_:=os.ReadFile(selectFile(cache))
 if e:=os.WriteFile(filepath.Join(dest,fileNames[0]),[]byte("corrupt"),0600);e!=nil{t.Fatal(e)}
 if _,_,e:=hydrate(packed,cache);e==nil{t.Fatal("bad content-addressed cache silently trusted")}
 after,_:=os.ReadFile(selectFile(cache));if !bytes.Equal(prior,after){t.Fatal("selection changed")}
}
func TestReversibleDigestCoexistence(t *testing.T){
 src,first,cache:=fixture(t);old,_,e:=hydrate(first,cache);if e!=nil{t.Fatal(e)}
 next:=filepath.Join(t.TempDir(),"next")
 if e:=pack(src,next,"synthetic/eleven-files",strings.Repeat("d",40));e!=nil{t.Fatal(e)}
 latest,hit,e:=hydrate(next,cache);if e!=nil||hit||latest==old{t.Fatal("new revision did not create new blob")}
 if e:=directory(old);e!=nil{t.Fatal("prior verified digest lost")}
 sel,_:=os.ReadFile(selectFile(cache));var receipt Selection
 if e:=json.Unmarshal(sel,&receipt);e!=nil||receipt.Revision!=strings.Repeat("d",40){t.Fatal("selection did not update")}
}
func TestManifestCanonicalIdentity(t *testing.T){
 _,packed,_:=fixture(t);_,b,e:=readManifest(packed);if e!=nil{t.Fatal(e)}
 h:=fmt.Sprintf("%x",sha256.Sum256(b))
 if len(h)!=64||!shaValue.MatchString(h){t.Fatal("invalid content digest")}
}
