// Experimental source-only OCI chunking. Does not publish GHCR artifacts.
package main
import("crypto/sha256";"encoding/hex";"encoding/json";"errors";"flag";"fmt";"io";"os";"path/filepath";"regexp")
const limit int64=9_000_000_000
const kind="maf-oci-chunk-lab/v1"
var safe=regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`)
var hex64=regexp.MustCompile(`^[0-9a-f]{64}$`)
type Part struct{Name string `json:"name"`;Index int `json:"index"`;Bytes int64 `json:"bytes"`;SHA string `json:"sha256"`}
type Bundle struct{Kind string `json:"schema"`;Logical string `json:"logical_id"`;Source string `json:"source_file"`;Max int64 `json:"part_max_bytes"`;Bytes int64 `json:"total_bytes"`;SHA string `json:"total_sha256"`;Parts []Part `json:"parts"`}
func token(s string)bool{return safe.MatchString(s)&&s!="."&&s!=".."}
func regular(path string)(os.FileInfo,error){i,e:=os.Lstat(path);if e!=nil{return nil,e};if !i.Mode().IsRegular(){return nil,errors.New("nonregular file rejected")};return i,nil}
func manifest(p string,m Bundle)error{b,e:=json.MarshalIndent(m,"","  ");if e!=nil{return e};return os.WriteFile(p,append(b,'\n'),0600)}
func split(src,dst,id string,n int64)error{
 if !token(id)||!token(filepath.Base(src))||n<1||n>limit{return errors.New("invalid source identity/chunk limit")}
 info,e:=regular(src);if e!=nil{return e};if info.Size()<1||info.Size()/n+1>10000{return errors.New("source size out of bounds")}
 if _,e:=os.Lstat(dst);e==nil{return errors.New("output exists")}else if !os.IsNotExist(e){return e}
 stage,e:=os.MkdirTemp(filepath.Dir(dst),".oci-stage-");if e!=nil{return e};defer os.RemoveAll(stage)
 f,e:=os.Open(src);if e!=nil{return e};defer f.Close()
 m:=Bundle{Kind:kind,Logical:id,Source:filepath.Base(src),Max:n,Bytes:info.Size(),Parts:[]Part{}}
 totalHash:=sha256.New();var used int64
 for i:=0;used<info.Size();i++{
  name:=fmt.Sprintf("part-%05d.bin",i)
  file,e:=os.OpenFile(filepath.Join(stage,name),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if e!=nil{return e}
  h:=sha256.New();count,copyErr:=io.CopyN(io.MultiWriter(file,h,totalHash),f,n);closeErr:=file.Close()
  if copyErr!=nil&&!errors.Is(copyErr,io.EOF){return copyErr};if closeErr!=nil{return closeErr};if count<1{return errors.New("short read")}
  m.Parts=append(m.Parts,Part{Name:name,Index:i,Bytes:count,SHA:hex.EncodeToString(h.Sum(nil))});used+=count
 }
 if used!=info.Size(){return errors.New("source changed while reading")}
 m.SHA=hex.EncodeToString(totalHash.Sum(nil))
 if e:=manifest(filepath.Join(stage,"manifest.json"),m);e!=nil{return e}
 return os.Rename(stage,dst)
}
func validate(m Bundle)error{
 if m.Kind!=kind||!token(m.Logical)||!token(m.Source)||!hex64.MatchString(m.SHA)||m.Max<1||m.Max>limit||m.Bytes<1||len(m.Parts)==0||len(m.Parts)>10000{return errors.New("manifest header rejected")}
 var total int64
 for i,p:=range m.Parts{
  if p.Name!=fmt.Sprintf("part-%05d.bin",i)||p.Index!=i||p.Bytes<1||p.Bytes>m.Max||!hex64.MatchString(p.SHA)||total>m.Bytes-p.Bytes{return errors.New("manifest part rejected")}
  total+=p.Bytes
 }
 if total!=m.Bytes{return errors.New("manifest length mismatch")}
 return nil
}
func restore(mpath,dir,dest string)error{
 if filepath.Base(mpath)!="manifest.json"{return errors.New("manifest name invalid")}
 if _,e:=regular(mpath);e!=nil{return e}
 info,e:=regular(mpath);if e!=nil{return e};if info.Size()>maxManifestBytes{return errors.New("manifest exceeds bounded size")}
 b,e:=os.ReadFile(mpath);if e!=nil{return e}
 m,e:=decodeStrictManifest(b);if e!=nil{return e};if e:=validate(m);e!=nil{return e}
 if _,e:=os.Lstat(dest);e==nil{return errors.New("refuse overwrite")}else if !os.IsNotExist(e){return e}
 allowed:=map[string]bool{"manifest.json":true};for _,p:=range m.Parts{allowed[p.Name]=true}
 entries,e:=os.ReadDir(dir);if e!=nil{return e}
 if len(entries)!=len(allowed){return errors.New("unexpected or missing member")}
 for _,ent:=range entries{if !allowed[ent.Name()]{return errors.New("unapproved member")}}
 tmp,e:=os.CreateTemp(filepath.Dir(dest),".restore-");if e!=nil{return e};defer os.Remove(tmp.Name());defer tmp.Close()
 h:=sha256.New();var total int64
 for _,p:=range m.Parts{
  fpath:=filepath.Join(dir,p.Name);info,e:=regular(fpath);if e!=nil{return e};if info.Size()!=p.Bytes{return errors.New("part size changed")}
  f,e:=os.Open(fpath);if e!=nil{return e};ph:=sha256.New();n,cp:=io.Copy(io.MultiWriter(tmp,h,ph),f);ce:=f.Close()
  if cp!=nil{return cp};if ce!=nil{return ce}
  if n!=p.Bytes||hex.EncodeToString(ph.Sum(nil))!=p.SHA{return errors.New("part SHA mismatch")};total+=n
 }
 if total!=m.Bytes||hex.EncodeToString(h.Sum(nil))!=m.SHA{return errors.New("whole file SHA mismatch")}
 if e:=tmp.Sync();e!=nil{return e};if e:=tmp.Close();e!=nil{return e}
 return os.Link(tmp.Name(),dest) // no overwriting existing selection
}
func main(){
 if len(os.Args)<2{os.Exit(2)};var e error
 switch os.Args[1]{
 case "split":
  f:=flag.NewFlagSet("split",flag.ExitOnError);src:=f.String("input","","");dst:=f.String("out","","");logical:=f.String("logical","synthetic","");max:=f.Int64("part-bytes",131072,"");f.Parse(os.Args[2:]);e=split(*src,*dst,*logical,*max)
 case "restore":
  f:=flag.NewFlagSet("restore",flag.ExitOnError);man:=f.String("manifest","","");parts:=f.String("parts","","");dst:=f.String("out","","");f.Parse(os.Args[2:]);e=restore(*man,*parts,*dst)
 default:e=errors.New("unknown mode")
 }
 if e!=nil{fmt.Fprintln(os.Stderr,"FAIL_CLOSED:",e);os.Exit(1)}
 fmt.Println("OCI_CHUNK_LAB_PASS")
}