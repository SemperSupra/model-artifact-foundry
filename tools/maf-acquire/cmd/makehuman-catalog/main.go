// makehuman-catalog is a read-only offline discovery helper for MAF.
package main
import (
 "encoding/json"
 "flag"
 "fmt"
 "os"
 "github.com/SemperSupra/model-artifact-foundry/tools/maf-acquire/makehuman"
)
func main(){
 catalog:=flag.String("catalog","","downloaded archived assets.json; read-only")
 query:=flag.String("q","","case-insensitive substring search")
 typ:=flag.String("type","","asset type exact filter")
 license:=flag.String("license","","exact license filter (e.g. CC0)")
 author:=flag.String("author","","exact author filter")
 flag.Parse()
 if *catalog=="" {fmt.Fprintln(os.Stderr,"-catalog required; no implicit network access");os.Exit(2)}
 f,e:=os.Open(*catalog);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)};defer f.Close()
 a,e:=makehuman.ParseCatalog(f);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 output:=struct{Status string `json:"status"`;FoundryStatus string `json:"foundry_status"`;Count int `json:"count"`;Assets []makehuman.Asset `json:"assets"`}{Status:"DISCOVERY_ONLY_NOT_DOWNLOADED",FoundryStatus:"NOT_ADOPTED",Assets:makehuman.Search(a,makehuman.Filter{Query:*query,Type:*typ,License:*license,Author:*author})}
 output.Count=len(output.Assets)
 if e:=json.NewEncoder(os.Stdout).Encode(output);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
}
