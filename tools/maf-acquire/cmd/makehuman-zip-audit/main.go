// makehuman-zip-audit is an offline, non-extracting ZIP integrity inspector.
package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/SemperSupra/model-artifact-foundry/tools/maf-acquire/makehuman"
)
func main(){
 archive:=flag.String("archive","","input ZIP; never extracts or installs assets")
 flag.Parse()
 if *archive==""{fmt.Fprintln(os.Stderr,"-archive required");os.Exit(2)}
 st,e:=os.Lstat(*archive)
 if e!=nil || !st.Mode().IsRegular(){fmt.Fprintln(os.Stderr,"regular file required");os.Exit(2)}
 f,e:=os.Open(*archive);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)};defer f.Close()
 rec,e:=makehuman.AuditZIP(f,st.Size(),makehuman.DefaultZIPLimits())
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
 if e:=json.NewEncoder(os.Stdout).Encode(rec);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
}
