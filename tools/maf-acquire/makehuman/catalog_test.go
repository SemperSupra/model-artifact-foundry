package makehuman
import (
 "strings"
 "testing"
)
const demo=`{"4":{"username":"Joel Palmius","license":"CC0","title":"Basic female","type":"model","compatibility":"1.1.x","files":{"mhm":"http://files.makehumancommunity.org/sites/default/files/models/1/basic-female.mhm"}},"5":{"username":"Test user","license":"CC-BY","title":"Test hand morph","type":"target","files":{"target":"https://files.makehumancommunity.org/example.target"}}}`
func TestParseAndFilter(t *testing.T){
 a,e:=ParseCatalog(strings.NewReader(demo));if e!=nil {t.Fatal(e)}
 if len(a)!=2 || a[0].ID!="4" || a[0].Title!="Basic female" || a[0].Files["mhm"]==""{t.Fatalf("unexpected catalog: %+v",a)}
 b:=Search(a,Filter{Query:"female",Type:"model",License:"CC0"}); if len(b)!=1 || b[0].ID!="4"{t.Fatalf("filter mismatch %+v",b)}
 if len(Search(a,Filter{Query:"female",License:"CC-BY"}))!=0 {t.Fatal("license filter bypassed")}
 if len(Search(a,Filter{Author:"test user",Type:"target"}))!=1 {t.Fatal("author/type filtering failed")}
}
func TestMalformedAndBudget(t *testing.T){
 for _,s:=range []string{"",`[]`,`{}`,`{"bad/path":{"title":"T","type":"model"}}`,`{"1":false}`,`{"1":{"title":"T","type":"model","files":42}}`} {
  if _,e:=ParseCatalog(strings.NewReader(s));e==nil{t.Errorf("accepted invalid catalog %q",s)}
 }
 _,e:=ParseCatalog(strings.NewReader(strings.Repeat(" ",int(MaxCatalogBytes)+1)))
 if e==nil{t.Fatal("oversized input accepted")}
}
func TestNoImplicitDownloadOrApproval(t *testing.T){
 a,e:=ParseCatalog(strings.NewReader(demo));if e!=nil{t.Fatal(e)}
 if !strings.HasPrefix(a[0].Files["mhm"],"http://") {t.Fatal("original URL mutated; discovery metadata must be unaltered")}
 // Callers must invoke existing pinned verified MAF acquisition independently.
}
