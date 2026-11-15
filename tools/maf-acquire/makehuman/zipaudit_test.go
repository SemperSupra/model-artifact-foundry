package makehuman

import (
 "archive/zip"
 "bytes"
 "os"
 "strings"
 "testing"
)

type testEntry struct {name string; body string; mode os.FileMode}
func fixture(t *testing.T,entries []testEntry) []byte {
 t.Helper()
 var b bytes.Buffer
 w:=zip.NewWriter(&b)
 for _,entry:=range entries {
  h:=&zip.FileHeader{Name:entry.name,Method:zip.Store}
  h.SetMode(entry.mode)
  f,e:=w.CreateHeader(h);if e!=nil{t.Fatal(e)}
  if _,e=f.Write([]byte(entry.body));e!=nil{t.Fatal(e)}
 }
 if e:=w.Close();e!=nil{t.Fatal(e)}
 return b.Bytes()
}
func check(t *testing.T, data []byte, limits ZIPLimits) (ZIPReceipt,error) {
 t.Helper()
 return AuditZIP(bytes.NewReader(data),int64(len(data)),limits)
}
func TestZIPAuditBoundedValid(t *testing.T) {
 b:=fixture(t,[]testEntry{
  {"targets/", "", os.ModeDir|0755},
  {"targets/shape.target","vertex offsets",0644},
  {"readme.txt","CC0 metadata not a license decision",0644},
 })
 rec,e:=check(t,b,DefaultZIPLimits())
 if e!=nil{t.Fatal(e)}
 if rec.Status!="ZIP_CRC_AND_SHA256_VERIFIED_NOT_APPROVED" || rec.FoundryStatus!="NOT_ADOPTED" || len(rec.Members)!=2 || rec.Members[0].Path!="readme.txt" {t.Fatalf("unexpected receipt: %#v",rec)}
 if len(rec.ArchiveSHA256)!=64 || len(rec.Members[0].SHA256)!=64 {t.Fatal("missing hashes")}
}
func TestZIPAuditNegativeControls(t *testing.T) {
 cases:=[]struct{name string; entries []testEntry}{
  {"parent traversal",[]testEntry{{"../outside","no",0644}}},
  {"absolute path",[]testEntry{{"/etc/passwd","no",0644}}},
  {"windows drive",[]testEntry{{"C:evil","no",0644}}},
  {"backslash",[]testEntry{{"folder\\evil","no",0644}}},
  {"dot path",[]testEntry{{"foo/./bar","no",0644}}},
  {"duplicate",[]testEntry{{"x","a",0644},{"x","b",0644}}},
  {"case alias",[]testEntry{{"X","a",0644},{"x","b",0644}}},
  {"symlink",[]testEntry{{"link","../outside",os.ModeSymlink|0777}}},
  {"file-directory alias",[]testEntry{{"x","a",0644},{"x/y","b",0644}}},
  {"only dirs",[]testEntry{{"folder/","",os.ModeDir|0755}}},
 }
 for _,tc:=range cases {
  t.Run(tc.name,func(t *testing.T) {
   b:=fixture(t,tc.entries)
   if _,e:=check(t,b,DefaultZIPLimits());e==nil{t.Fatal("unsafe ZIP accepted")}
  })
 }
}
func TestZIPAuditLimitsAndCRC(t *testing.T){
 b:=fixture(t,[]testEntry{{"x.txt","1234567890",0644}})
 limits:=DefaultZIPLimits()
 limits.MaxTotalBytes=4
 if _,e:=check(t,b,limits);e==nil {t.Fatal("failed to enforce total bound")}
 limits=DefaultZIPLimits()
 limits.MaxArchiveBytes=int64(len(b)-1)
 if _,e:=check(t,b,limits);e==nil {t.Fatal("failed to enforce archive bound")}
 limits=DefaultZIPLimits()
 limits.MaxMembers=0
 if _,e:=check(t,b,limits);e==nil {t.Fatal("failed to enforce member count")}
 corrupt:=append([]byte(nil),b...)
 idx:=bytes.Index(corrupt,[]byte("1234567890"))
 if idx<0{t.Fatal("fixture body missing")}
 corrupt[idx]^=0x1
 if _,e:=check(t,corrupt,limits);e==nil || !strings.Contains(e.Error(),"CRC") {t.Fatalf("CRC change unrecognized: %v",e)}
}
