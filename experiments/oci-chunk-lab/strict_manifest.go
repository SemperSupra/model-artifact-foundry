package main

import (
    "bytes"
    "encoding/json"
    "errors"
    "fmt"
    "io"
)

const maxManifestBytes int64 = 3_000_000

// rejectDuplicateKeys scans the whole JSON tree, rather than trusting
// Go's permissive last-key-wins decoding for content provenance.
func rejectDuplicateKeys(data []byte) error {
    d := json.NewDecoder(bytes.NewReader(data))
    var walk func() error
    walk = func() error {
        token, err := d.Token()
        if err != nil { return err }
        delim, ok := token.(json.Delim)
        if !ok { return nil } // scalar
        switch delim {
        case '{':
            keys := map[string]struct{}{}
            for d.More() {
                keyToken, err := d.Token()
                if err != nil { return err }
                key, ok := keyToken.(string)
                if !ok { return errors.New("object member key is not a string") }
                if _, exists := keys[key]; exists {
                    return fmt.Errorf("duplicate JSON object member: %s", key)
                }
                keys[key] = struct{}{}
                if err := walk(); err != nil { return err }
            }
            end, err := d.Token()
            if err != nil || end != json.Delim('}') {
                return errors.New("invalid JSON object terminator")
            }
        case '[':
            for d.More() {
                if err := walk(); err != nil { return err }
            }
            end, err := d.Token()
            if err != nil || end != json.Delim(']') {
                return errors.New("invalid JSON array terminator")
            }
        default:
            return errors.New("unexpected JSON delimiter")
        }
        return nil
    }
    if err := walk(); err != nil { return err }
    if _, err := d.Token(); err != io.EOF {
        return errors.New("trailing JSON tokens or decoding error")
    }
    return nil
}

// decodeStrictManifest disallows duplicate/unknown fields, multiple top-level
// values, and oversized JSON. This is experiment-only, not a Foundry v1 parser.
func decodeStrictManifest(data []byte) (Bundle,error) {
    var result Bundle
    if len(data)==0 || int64(len(data)) > maxManifestBytes {
        return result, errors.New("manifest byte size exceeds bounded limit")
    }
    if err:=rejectDuplicateKeys(data); err!=nil { return result, err }
    d:=json.NewDecoder(bytes.NewReader(data))
    d.DisallowUnknownFields()
    if err:=d.Decode(&result);err!=nil{return result,err}
    if _,err:=d.Token();err!=io.EOF{return result,errors.New("extra JSON content")}
    return result,nil
}
