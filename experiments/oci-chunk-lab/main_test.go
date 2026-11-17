package main
import("bytes";"encoding/json";"os";"path/filepath";"strings";"testing")
func fixture(t *testing.T)(string,string,string){
 t.Helper();dir:=t.TempDir();src:=filepath.Join(dir,"input.bin")
 if e:=os.WriteFile(src,bytes.Repeat([]byte("synthetic-fixture-0123456789"),6001),0600);e!=nil{t.Fatal(e)}
 parts:=filepath.Join(dir,"parts");if e:=split(src,parts,"test-model",16384);e!=nil{t.Fatal(e)}
 return src,parts,filepath.Join(dir,"restored.bin")
}
func TestRoundtripAndNoOverwrite(t *testing.T){
 src,parts,out:=fixture(t)
 if e:=restore(filepath.Join(parts,"manifest.json"),parts,out);e!=nil{t.Fatal(e)}
 a,_:=os.ReadFile(src);b,_:=os.ReadFile(out);if !bytes.Equal(a,b){t.Fatal("content mismatch")}
 if e:=restore(filepath.Join(parts,"manifest.json"),parts,out);e==nil{t.Fatal("replaced prior selected bytes")}
 if e:=split(src,parts,"test-model",1024);e==nil{t.Fatal("overwrote prior blob directory")}
}
func TestDenyTamper(t *testing.T){
 for _,mode:=range []string{"wrong-sha","missing","extra","symlink","swap","traversal","bad-length","bitflip"}{
  t.Run(mode,func(t *testing.T){
   _,dir,out:=fixture(t);mf:=filepath.Join(dir,"manifest.json");b,_:=os.ReadFile(mf);var m Bundle;json.Unmarshal(b,&m)
   switch mode{
   case "wrong-sha":m.Parts[0].SHA=strings.Repeat("0",64)
   case "missing":os.Remove(filepath.Join(dir,m.Parts[0].Name))
   case "extra":os.WriteFile(filepath.Join(dir,"intruder.bin"),[]byte("x"),0600)
   case "symlink":os.Remove(filepath.Join(dir,m.Parts[0].Name));os.Symlink(filepath.Join(dir,m.Parts[1].Name),filepath.Join(dir,m.Parts[0].Name))
   case "swap":m.Parts[0],m.Parts[1]=m.Parts[1],m.Parts[0]
   case "traversal":m.Parts[0].Name="../outside"
   case "bad-length":m.Bytes++
   case "bitflip":os.WriteFile(filepath.Join(dir,m.Parts[0].Name),[]byte("bad"),0600)
   }
   if mode=="wrong-sha"||mode=="swap"||mode=="traversal"||mode=="bad-length"{manifest(mf,m)}
   if e:=restore(mf,dir,out);e==nil{t.Fatalf("accepted attack %s",mode)}
   if _,e:=os.Lstat(out);!os.IsNotExist(e){t.Fatal("corrupt output exposed")}
  })
 }
}
func TestDenySourceSymlinkAndUnsafeIdentity(t *testing.T){
 src,_,_:=fixture(t);link:=filepath.Join(t.TempDir(),"input.bin");os.Symlink(src,link)
 if e:=split(link,filepath.Join(t.TempDir(),"chunks"),"test-model",1024);e==nil{t.Fatal("symlink allowed")}
 if e:=split(src,filepath.Join(t.TempDir(),"chunks"),"../escape",1024);e==nil{t.Fatal("unsafe logical ID")}
}