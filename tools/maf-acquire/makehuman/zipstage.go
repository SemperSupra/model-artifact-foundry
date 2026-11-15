package makehuman

import (
 "archive/zip"
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "strings"
)

// StageVerifiedZIP extracts an already audited research archive into a new,
// isolated private temporary directory. Caller must manage returned directory.
// This is NOT a Foundry adoption/promotion or license/security decision.
func StageVerifiedZIP(r io.ReaderAt, n int64, audit ZIPReceipt, parent string) (_ string, err error) {
 st,e:=os.Lstat(parent)
 if e!=nil || !st.IsDir() || st.Mode()&os.ModeSymlink!=0 {
  return "",errors.New("trusted non-symlink extraction parent required")
 }
 if n<=0 || audit.ArchiveBytes!=n || len(audit.Members)==0 || len(audit.ArchiveSHA256)!=64 {
  return "",errors.New("archive size/receipt invalid")
 }
 // Validate archive unchanged between prior audit and staging.
 archiveHash:=sha256.New()
 if _,e=io.Copy(archiveHash,io.NewSectionReader(r,0,n));e!=nil{return "",e}
 if hex.EncodeToString(archiveHash.Sum(nil))!=audit.ArchiveSHA256 {
  return "",errors.New("archive changed after initial audit")
 }
 zr,e:=zip.NewReader(r,n);if e!=nil{return "",e}
 expected:=make(map[string]ZIPMember,len(audit.Members))
 for _,m:=range audit.Members {
  if !safeZIPPath(m.Path) || m.Bytes<0 || len(m.SHA256)!=64 || expected[m.Path].Path!="" {
   return "",errors.New("invalid/duplicate audited member")
  }
  expected[m.Path]=m
 }
 root,e:=os.MkdirTemp(parent,".maf-mh-staging-")
 if e!=nil{return "",e}
 defer func(){if err!=nil{_ = os.RemoveAll(root)}}()
 matched:=0
 for _,f:=range zr.File {
  if !safeZIPPath(f.Name) || f.Flags&1!=0 || f.Mode()&os.ModeSymlink!=0 ||
    (!f.Mode().IsRegular() && !f.Mode().IsDir()) {
   return "",fmt.Errorf("unsafe changed ZIP member %q",f.Name)
  }
  rel:=strings.TrimSuffix(f.Name,"/")
  target:=filepath.Join(root,filepath.FromSlash(rel))
  within,e:=filepath.Rel(root,target)
  if e!=nil || within==".." || strings.HasPrefix(within,".."+string(os.PathSeparator)) {
   return "",fmt.Errorf("ZIP staging escape: %q",f.Name)
  }
  if strings.HasSuffix(f.Name,"/"){
   if !f.Mode().IsDir() {return "",errors.New("ZIP directory metadata mismatch")}
   if e:=os.MkdirAll(target,0700);e!=nil{return "",e}
   continue
  }
  m,ok:=expected[f.Name];if !ok{return "",fmt.Errorf("unlisted ZIP member: %q",f.Name)}
  if uint64(m.Bytes)!=f.UncompressedSize64 {return "",fmt.Errorf("member count mismatch for %q",f.Name)}
  if e:=os.MkdirAll(filepath.Dir(target),0700);e!=nil{return "",e}
  out,e:=os.OpenFile(target,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
  if e!=nil{return "",e}
  in,e:=f.Open()
  if e!=nil{out.Close();return "",e}
  h:=sha256.New()
  got,copyErr:=io.Copy(io.MultiWriter(out,h),io.LimitReader(in,m.Bytes+1))
  closeSrcErr:=in.Close()
  syncErr:=out.Sync()
  closeDestErr:=out.Close()
  if copyErr!=nil{return "",copyErr}
  if closeSrcErr!=nil{return "",closeSrcErr}
  if syncErr!=nil{return "",syncErr}
  if closeDestErr!=nil{return "",closeDestErr}
  if got!=m.Bytes || hex.EncodeToString(h.Sum(nil))!=m.SHA256 {
   return "",fmt.Errorf("staged content changed for %q",f.Name)
  }
  matched++
 }
 if matched!=len(expected){return "",errors.New("audited ZIP member missing during staging")}
 return root,nil
}
