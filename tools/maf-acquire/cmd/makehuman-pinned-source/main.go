// makehuman-pinned-source is a one-source research proof for the *existing*
// Foundry acquire.FetchPinnedHTTPS path, not a general MakeHuman downloader.
package main

import (
 "context"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "time"

 "github.com/SemperSupra/model-artifact-foundry/tools/maf-acquire/acquire"
 "github.com/SemperSupra/model-artifact-foundry/tools/maf-acquire/makehuman"
)

const publisherURL = "https://files.makehumancommunity.org/functional/visemes01.zip"
const observedArchiveSHA256 = "f61f4f36bb4fe43486efa2a644eea9d6760e510bde10eecc97a4ddf28424e4d3"

// The digest is a verified previous public-runner OBSERVATION, not an
// independently publisher-attested checksum or a rights approval.
func run(directory string) error {
 if directory=="" {return errors.New("staging directory required")}
 info,err:=os.Lstat(directory)
 if err!=nil || !info.IsDir() || info.Mode()&os.ModeSymlink!=0 {
  return errors.New("safe precreated staging directory required")
 }
 entries,err:=os.ReadDir(directory)
 if err!=nil || len(entries)!=0 {return errors.New("staging directory must be empty")}
 dest:=filepath.Join(directory,"visemes01.zip")
 ctx,cancel:=context.WithTimeout(context.Background(),2*time.Minute)
 defer cancel()
 byteReceipt,err:=acquire.FetchPinnedHTTPS(
  ctx,nil,publisherURL,[]string{"files.makehumancommunity.org"},
  8<<20,observedArchiveSHA256,dest,
 )
 if err!=nil {return fmt.Errorf("pinned HTTPS byte transfer rejected: %w",err)}
 f,err:=os.Open(dest);if err!=nil{return err}
 defer f.Close()
 s,err:=f.Stat();if err!=nil{return err}
 archiveReceipt,err:=makehuman.AuditZIP(f,s.Size(),makehuman.DefaultZIPLimits())
 if err!=nil{return fmt.Errorf("ZIP audit rejected: %w",err)}
 if archiveReceipt.ArchiveSHA256!=byteReceipt.SHA256 {
  return errors.New("independent ZIP and HTTPS receipt digest mismatch")
 }
 result:=map[string]interface{}{
  "status":"STAGED_VERIFIED_NOT_ADOPTED",
  "foundry_status":"NOT_ADOPTED",
  "identity_kind":"observed-file-sha256-only",
  "source_url":publisherURL,
  "archive_sha256":archiveReceipt.ArchiveSHA256,
  "archive_bytes":archiveReceipt.ArchiveBytes,
  "member_count":len(archiveReceipt.Members),
  "total_unpacked_bytes":archiveReceipt.TotalUnpackedBytes,
  "limitations":[]string{
   "Observed source digest is not a publisher signature or approved origin record",
   "No extraction or asset execution",
   "No license, character compatibility, OCI, content-manifest, Drive custody, or publication acceptance",
  },
 }
 return json.NewEncoder(os.Stdout).Encode(result)
}
func main(){
 if len(os.Args)!=2 {fmt.Fprintln(os.Stderr,"usage: makehuman-pinned-source EMPTY_STAGING_DIR");os.Exit(2)}
 if err:=run(os.Args[1]);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(3)}
}
