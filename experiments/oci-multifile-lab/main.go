// Research-only multi-file OCI layer reconstruction; not an approved Model Artifact Foundry publisher or hydrator.
package main

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "regexp"
 "sort"
 "strings"
)

const schema = "maf-oci-multifile-lab/v1"
const maxManifestBytes int64 = 1_000_000
const maxFileBytes int64 = 9_000_000_000
const maxTotalBytes int64 = 200_000_000_000
const maxFileCount = 128
var safeToken = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`)
var shaValue = regexp.MustCompile(`^[0-9a-f]{64}$`)
var revisionValue = regexp.MustCompile(`^[0-9a-f]{40}$`)

type File struct { Name string `json:"name"`; Size int64 `json:"bytes"`; SHA string `json:"sha256"` }
type Manifest struct {
 Schema string `json:"schema"`
 LogicalID string `json:"logical_id"`
 Revision string `json:"upstream_revision"`
 Files []File `json:"files"`
}
type Selection struct {
 Schema string `json:"schema"`
 LogicalID string `json:"logical_id"`
 Revision string `json:"upstream_revision"`
 ManifestSHA string `json:"manifest_sha256"`
 State string `json:"state"`
}
func safeName(s string) bool { return safeToken.MatchString(s) && s!="." && s!=".." }
func safeLogical(s string) bool { x:=strings.Split(s,"/");return len(x)==2&&safeName(x[0])&&safeName(x[1]) }
func regular(path string) (os.FileInfo,error) {
 info,e:=os.Lstat(path);if e!=nil{return nil,e}
 if !info.Mode().IsRegular(){return nil,errors.New("nonregular file refused: "+filepath.Base(path))}
 return info,nil
}
func directory(path string)error {
 info,e:=os.Lstat(path);if e!=nil{return e}
 if !info.IsDir() || info.Mode() & os.ModeSymlink!=0 {return errors.New("non-directory input")}
 return nil
}
func digestFile(src string,dst io.Writer) (string,int64,error){
 f,e:=os.Open(src);if e!=nil{return "",0,e};defer f.Close()
 if stat,e:=f.Stat();e!=nil||!stat.Mode().IsRegular(){return "",0,errors.New("opened nonregular file")}
 h:=sha256.New()
 var sink io.Writer=h
 if dst!=nil {sink=io.MultiWriter(dst,h)}
 n,e:=io.Copy(sink,f)
 if e!=nil {return "",n,e}
 return hex.EncodeToString(h.Sum(nil)),n,nil
}
func checkManifest(m Manifest) error {
 if m.Schema!=schema||!safeLogical(m.LogicalID)||!revisionValue.MatchString(m.Revision)||len(m.Files)<1||len(m.Files)>maxFileCount{
  return errors.New("manifest schema/identity/file-count invalid")
 }
 var total int64
 last:=""
 for _,f:=range m.Files{
  if !safeName(f.Name)||f.Name=="manifest.json"||f.Name<=last||f.Size<1||f.Size>maxFileBytes||!shaValue.MatchString(f.SHA){
   return errors.New("manifest file field invalid")
  }
  if total>maxTotalBytes-f.Size {return errors.New("total bytes exceed admission bound")}
  total+=f.Size;last=f.Name
 }
 return nil
}
func checkDuplicates(data []byte) error {
 d:=json.NewDecoder(bytes.NewReader(data))
 var visit func()error
 visit=func()error{
  token,e:=d.Token();if e!=nil{return e}
  v,ok:=token.(json.Delim);if !ok{return nil}
  switch v{
  case '{':
   seen:=map[string]bool{}
   for d.More(){
    key,e:=d.Token();if e!=nil{return e}
    s,ok:=key.(string);if !ok||seen[s]{return errors.New("duplicate/invalid JSON object member")}
    seen[s]=true
    if e:=visit();e!=nil{return e}
   }
   end,e:=d.Token();if e!=nil||end!=json.Delim('}') {return errors.New("invalid JSON object end")}
  case '[':
   for d.More(){if e:=visit();e!=nil{return e}}
   end,e:=d.Token();if e!=nil||end!=json.Delim(']') {return errors.New("invalid JSON array end")}
  default:return errors.New("unexpected JSON delimiter")
  }
  return nil
 }
 if e:=visit();e!=nil{return e}
 if _,e:=d.Token();e!=io.EOF{return errors.New("trailing JSON tokens")}
 return nil
}
func parseManifest(data []byte)(Manifest,error){
 var m Manifest
 if len(data)==0||int64(len(data))>maxManifestBytes{return m,errors.New("manifest size out of bounds")}
 if e:=checkDuplicates(data);e!=nil{return m,e}
 decoder:=json.NewDecoder(bytes.NewReader(data));decoder.DisallowUnknownFields()
 if e:=decoder.Decode(&m);e!=nil{return m,e}
 if _,e:=decoder.Token();e!=io.EOF{return m,errors.New("trailing input")}
 if e:=checkManifest(m);e!=nil{return m,e}
 return m,nil
}
func readManifest(dir string)(Manifest,[]byte,error){
 var empty Manifest
 path:=filepath.Join(dir,"manifest.json")
 info,e:=regular(path);if e!=nil{return empty,nil,e}
 if info.Size()>maxManifestBytes{return empty,nil,errors.New("manifest exceeds byte limit")}
 b,e:=os.ReadFile(path);if e!=nil{return empty,nil,e}
 m,e:=parseManifest(b);return m,b,e
}
func inventory(dir string,m Manifest)error{
 if e:=directory(dir);e!=nil{return e}
 entries,e:=os.ReadDir(dir);if e!=nil{return e}
 if len(entries)!=len(m.Files)+1{return errors.New("unapproved or missing directory members")}
 allow:=map[string]bool{"manifest.json":true}
 for _,f:=range m.Files{allow[f.Name]=true}
 for _,entry:=range entries{
  if !allow[entry.Name()]{return errors.New("unexpected file in artifact")}
  if _,e:=regular(filepath.Join(dir,entry.Name()));e!=nil{return e}
 }
 return nil
}
func verifyDir(dir string,m Manifest)error{
 if e:=inventory(dir,m);e!=nil{return e}
 for _,row:=range m.Files{
  path:=filepath.Join(dir,row.Name)
  info,e:=regular(path);if e!=nil{return e}
  if info.Size()!=row.Size{return errors.New("size mismatch "+row.Name)}
  digest,n,e:=digestFile(path,nil)
  if e!=nil||n!=row.Size||digest!=row.SHA{return errors.New("SHA mismatch "+row.Name)}
 }
 return nil
}
func copyAndVerify(src,dst string,m Manifest,originalManifest []byte)error{
 if e:=os.WriteFile(filepath.Join(dst,"manifest.json"),originalManifest,0600);e!=nil{return e}
 for _,row:=range m.Files{
  from:=filepath.Join(src,row.Name)
  if _,e:=regular(from);e!=nil{return e}
  dest:=filepath.Join(dst,row.Name)
  out,e:=os.OpenFile(dest,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if e!=nil{return e}
  digest,n,cp:=digestFile(from,out)
  closeErr:=out.Close()
  if cp!=nil{return cp};if closeErr!=nil{return closeErr}
  if n!=row.Size||digest!=row.SHA{return errors.New("source changed or corrupted: "+row.Name)}
 }
 return verifyDir(dst,m)
}
func pack(src,out,logical,revision string)error{
 if !safeLogical(logical)||!revisionValue.MatchString(revision){return errors.New("invalid model identifier")}
 if e:=directory(src);e!=nil{return e}
 if _,e:=os.Lstat(out);e==nil{return errors.New("refuse existing pack output")}else if !os.IsNotExist(e){return e}
 list,e:=os.ReadDir(src);if e!=nil{return e}
 if len(list)<1||len(list)>maxFileCount{return errors.New("invalid source file count")}
 names:=make([]string,0,len(list))
 for _,entry:=range list{
  name:=entry.Name();if !safeName(name)||name=="manifest.json"{return errors.New("unsafe source file name")}
  if _,e:=regular(filepath.Join(src,name));e!=nil{return e}
  names=append(names,name)
 }
 sort.Strings(names)
 m:=Manifest{Schema:schema,LogicalID:logical,Revision:revision,Files:[]File{}}
 var total int64
 for _,name:=range names{
  p:=filepath.Join(src,name);info,e:=regular(p);if e!=nil{return e}
  if info.Size()<1||info.Size()>maxFileBytes||total>maxTotalBytes-info.Size(){return errors.New("file exceeds size bounds")}
  digest,n,e:=digestFile(p,nil);if e!=nil||n!=info.Size(){return errors.New("source changed during hash")}
  m.Files=append(m.Files,File{Name:name,Size:n,SHA:digest});total+=n
 }
 if e:=checkManifest(m);e!=nil{return e}
 b,e:=json.MarshalIndent(m,"","  ");if e!=nil{return e};b=append(b,'\n')
 if len(b)>int(maxManifestBytes){return errors.New("generated manifest exceeds byte bound")}
 stage,e:=os.MkdirTemp(filepath.Dir(out),".maf-pack-");if e!=nil{return e};defer os.RemoveAll(stage)
 if e:=copyAndVerify(src,stage,m,b);e!=nil{return e}
 return os.Rename(stage,out)
}
func atomicWrite(path string,b []byte)error{
 dir:=filepath.Dir(path)
 if e:=os.MkdirAll(dir,0700);e!=nil{return e}
 t,e:=os.CreateTemp(dir,".selected-");if e!=nil{return e}
 defer os.Remove(t.Name())
 if _,e:=t.Write(b);e!=nil{t.Close();return e}
 if e:=t.Sync();e!=nil{t.Close();return e}
 if e:=t.Close();e!=nil{return e}
 return os.Rename(t.Name(),path)
}
func hydrate(src,cache string)(string,bool,error){
 if e:=directory(src);e!=nil{return "",false,e}
 m,bytes,e:=readManifest(src);if e!=nil{return "",false,e}
 if e:=verifyDir(src,m);e!=nil{return "",false,e} // preflight before any selection side effect
 contentHash:=fmt.Sprintf("%x",sha256.Sum256(bytes))
 blobs:=filepath.Join(cache,"blobs")
 if e:=os.MkdirAll(blobs,0700);e!=nil{return "",false,e}
 final:=filepath.Join(blobs,contentHash)
 hit:=false
 if _,e:=os.Lstat(final);e==nil{
  if e:=verifyDir(final,m);e!=nil{return "",false,errors.New("existing cached blob corrupt: "+e.Error())}
  hit=true
 }else if !os.IsNotExist(e){return "",false,e}else{
  stage,e:=os.MkdirTemp(blobs,".staging-");if e!=nil{return "",false,e};defer os.RemoveAll(stage)
  if e:=copyAndVerify(src,stage,m,bytes);e!=nil{return "",false,e}
  if e:=os.Rename(stage,final);e!=nil{return "",false,e}
 }
 selection:=Selection{Schema:schema,LogicalID:m.LogicalID,Revision:m.Revision,
   ManifestSHA:contentHash,State:"RESEARCH_UNAPPROVED"}
 payload,e:=json.MarshalIndent(selection,"","  ");if e!=nil{return "",false,e};payload=append(payload,'\n')
 selectFile:=filepath.Join(cache,"selected",strings.ReplaceAll(m.LogicalID,"/","__")+".json")
 prior,e:=os.ReadFile(selectFile)
 if e==nil&&bytesEqual(prior,payload){return final,hit,nil}
 if e!=nil&&!os.IsNotExist(e){return "",false,e}
 if e:=atomicWrite(selectFile,payload);e!=nil{return "",false,e}
 return final,hit,nil
}
func bytesEqual(a,b []byte)bool{return bytes.Equal(a,b)}
func main(){
 if len(os.Args)<2{fmt.Fprintln(os.Stderr,"expected pack or hydrate");os.Exit(2)}
 f:=flag.NewFlagSet(os.Args[1],flag.ExitOnError)
 src:=f.String("src","","source directory");out:=f.String("out","","output directory")
 id:=f.String("id","synthetic/model","logical identifier");rev:=f.String("revision",strings.Repeat("a",40),"exact source revision")
 cache:=f.String("cache","","experimental cache directory")
 if e:=f.Parse(os.Args[2:]);e!=nil{os.Exit(2)}
 var e error
 switch os.Args[1]{
 case "pack":e=pack(*src,*out,*id,*rev)
 case "hydrate":
  var path string;var hit bool
  path,hit,e=hydrate(*src,*cache)
  if e==nil{fmt.Printf("MAF_MULTIFILE_LAB_RESULT={\"cached\":%t,\"source_only\":true,\"approved\":false,\"model_bytes_real\":false,\"path\":%q}\n",hit,path)}
 default:e=errors.New("invalid mode")
 }
 if e!=nil{fmt.Fprintln(os.Stderr,"FAIL_CLOSED:",e);os.Exit(1)}
}
