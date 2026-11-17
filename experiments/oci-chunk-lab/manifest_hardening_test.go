package main

import (
    "os"
    "path/filepath"
    "strings"
    "testing"
)

// These are deliberately source-contract RED tests against the prior OCI lab.
// A digest check alone does not make an ambiguous JSON manifest safe to adopt.
func TestRejectAmbiguousOrUnboundedManifest(t *testing.T) {
    modes := []string{
        "duplicate-top-level-key",
        "duplicate-part-key",
        "unknown-top-level-field",
        "unknown-nested-part-field",
        "oversize-json-whitespace",
    }
    for _, mode := range modes {
        t.Run(mode, func(t *testing.T) {
            _, dir, dest := fixture(t)
            path := filepath.Join(dir, "manifest.json")
            raw, err := os.ReadFile(path)
            if err != nil { t.Fatal(err) }
            value := string(raw)
            switch mode {
            case "duplicate-top-level-key":
                value = strings.Replace(value, "\"schema\":", "\"schema\":\"maf-oci-chunk-lab/v1\", \"schema\":", 1)
            case "duplicate-part-key":
                value = strings.Replace(value, "\"sha256\":", "\"sha256\":\""+strings.Repeat("0", 64)+"\", \"sha256\":", 1)
            case "unknown-top-level-field":
                value = strings.Replace(value, "\"schema\":", "\"undocumented_authority\":\"approved\", \"schema\":", 1)
            case "unknown-nested-part-field":
                value = strings.Replace(value, "\"index\":", "\"external_path\":\"../escape\", \"index\":", 1)
            case "oversize-json-whitespace":
                value += strings.Repeat(" ", 3_000_010)
            }
            if value == string(raw) { t.Fatal("invalid test injection") }
            if err := os.WriteFile(path, []byte(value), 0600); err != nil { t.Fatal(err) }
            if err := restore(path, dir, dest); err == nil {
                t.Fatalf("accepted ambiguous or unbounded JSON: %s", mode)
            }
            if _, err := os.Lstat(dest); !os.IsNotExist(err) {
                t.Fatal("materialized output after manifest rejection")
            }
        })
    }
}
