package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/SemperSupra/model-artifact-foundry/tools/maf-acquire/makehuman"
)
func main(){
 src:=flag.String("archive","","verified source ZIP")
 parent:=flag.String("stage-parent","","fresh disposable staging parent")
 flag.Parse()
 if *src==""||*parent==""{fmt.Fprintln(os.Stderr,"-archive and -stage-parent required");os.Exit(2)}
 st,e:=os.Lstat(*src);if e!=nil||!st.Mode().IsRegular(){fmt.Fprintln(os.Stderr,"regular archive required");os.Exit(2)}
 f,e:=os.Open(*src);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)};defer f.Close()
 receipt,e:=makehuman.AuditZIP(f,st.Size(),makehuman.DefaultZIPLimits())
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
 root,e:=makehuman.StageVerifiedZIP(f,st.Size(),receipt,*parent)
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
 // Ephemeral path is local process output, never a public receipt.
 if e:=json.NewEncoder(os.Stdout).Encode(map[string]interface{}{
   "status":"STAGED_EPHEMERAL_NOT_ADOPTED",
   "archive_sha256":receipt.ArchiveSHA256,
   "member_count":len(receipt.Members),
   "total_unpacked_bytes":receipt.TotalUnpackedBytes,
   "staging_root":root,
 });e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
}
