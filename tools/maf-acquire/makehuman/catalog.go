// Package makehuman normalizes the archived MakeHuman community asset JSON.
// It does not download, install, license-approve, or promote files.
package makehuman

import (
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "sort"
 "strings"
)

const MaxCatalogBytes int64 = 64 << 20

type Asset struct {
 ID string `json:"id"`
 Title string `json:"title"`
 Type string `json:"type"`
 Author string `json:"author"`
 License string `json:"license"`
 Compatibility string `json:"compatibility,omitempty"`
 Description string `json:"description,omitempty"`
 // File URLs are discovery hints, not trusted acquisition sources or immutable identities.
 Files map[string]string `json:"files"`
}
type upstreamAsset struct {
 Title string `json:"title"`
 Type string `json:"type"`
 Username string `json:"username"`
 License string `json:"license"`
 Compatibility string `json:"compatibility"`
 Description string `json:"description"`
 Files map[string]string `json:"files"`
}
func ParseCatalog(reader io.Reader) ([]Asset, error) {
 limited := io.LimitReader(reader, MaxCatalogBytes+1)
 data, err := io.ReadAll(limited)
 if err != nil { return nil, err }
 if int64(len(data)) > MaxCatalogBytes { return nil, errors.New("catalog exceeds 64 MiB input budget") }
 var raw map[string]json.RawMessage
 if err := json.Unmarshal(data, &raw); err != nil { return nil, fmt.Errorf("invalid MakeHuman catalog: %w", err) }
 if len(raw) == 0 { return nil, errors.New("empty MakeHuman catalog") }
 if len(raw) > 200000 { return nil, errors.New("asset record count exceeds budget") }
 out := make([]Asset,0,len(raw))
 for id, value := range raw {
  if id == "" || len(id)>64 || strings.ContainsAny(id,"\\/ \t\r\n") { return nil,fmt.Errorf("invalid asset ID %q",id) }
  var u upstreamAsset
  if err := json.Unmarshal(value,&u); err != nil { return nil,fmt.Errorf("asset %q: %w",id,err) }
  if strings.TrimSpace(u.Title)=="" || strings.TrimSpace(u.Type)=="" { continue }
  files:=map[string]string{}
  for k,url:=range u.Files { if len(k)<=64 && len(url)<=2048 && strings.TrimSpace(url)!="" {files[k]=url} }
  out=append(out,Asset{ID:id,Title:u.Title,Type:u.Type,Author:u.Username,License:u.License,Compatibility:u.Compatibility,Description:u.Description,Files:files})
 }
 sort.Slice(out,func(i,j int)bool{return out[i].ID<out[j].ID})
 return out,nil
}
type Filter struct {Query string; Type string; License string; Author string}
func Search(assets []Asset, filter Filter) []Asset {
 out:=[]Asset{}
 q:=strings.ToLower(strings.TrimSpace(filter.Query))
 for _,a:=range assets {
  if filter.Type!="" && !strings.EqualFold(a.Type,filter.Type) {continue}
  if filter.License!="" && !strings.EqualFold(a.License,filter.License) {continue}
  if filter.Author!="" && !strings.EqualFold(a.Author,filter.Author) {continue}
  text:=strings.ToLower(a.Title+" "+a.Type+" "+a.Description+" "+a.Author)
  if q!="" && !strings.Contains(text,q) {continue}
  out=append(out,a)
 }
 return out
}
