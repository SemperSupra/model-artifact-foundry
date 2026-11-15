package makehuman
import (
 "bytes"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestStageVerifiedZIP(t *testing.T){
 data:=fixture(t,[]testEntry{{"assets/","",os.ModeDir|0700},{"assets/viseme.target","1 0.1 0.2 0.3",0644}})
 rec,e:=check(t,data,DefaultZIPLimits());if e!=nil{t.Fatal(e)}
 par:=t.TempDir()
 root,e:=StageVerifiedZIP(bytes.NewReader(data),int64(len(data)),rec,par)
 if e!=nil{t.Fatal(e)}
 b,e:=os.ReadFile(filepath.Join(root,"assets","viseme.target"));if e!=nil{t.Fatal(e)}
 if string(b)!="1 0.1 0.2 0.3" {t.Fatalf("wrong staged bytes %q",b)}
 st,e:=os.Lstat(filepath.Join(root,"assets","viseme.target"));if e!=nil || !st.Mode().IsRegular(){t.Fatal("nonregular staged target")}
}
func TestStageFailClosedNoCommittedFiles(t *testing.T){
 data:=fixture(t,[]testEntry{{"regular.txt","ABC",0644}})
 rec,e:=check(t,data,DefaultZIPLimits());if e!=nil{t.Fatal(e)}
 parent:=t.TempDir()
 rec.Members[0].SHA256=strings.Repeat("0",64)
 if _,e=StageVerifiedZIP(bytes.NewReader(data),int64(len(data)),rec,parent);e==nil{t.Fatal("false member hash accepted")}
 entries,e:=os.ReadDir(parent);if e!=nil||len(entries)!=0{t.Fatalf("failed to clean staging after error: %v %v",entries,e)}
 rec,_=check(t,data,DefaultZIPLimits())
 rec.ArchiveSHA256=strings.Repeat("0",64)
 if _,e=StageVerifiedZIP(bytes.NewReader(data),int64(len(data)),rec,parent);e==nil{t.Fatal("false archive hash accepted")}
 if e=os.Symlink(parent,parent+"-link");e!=nil{t.Skipf("symlink unavailable: %v",e)}
 if _,e=StageVerifiedZIP(bytes.NewReader(data),int64(len(data)),rec,parent+"-link");e==nil{t.Fatal("symlinked extraction parent accepted")}
}
