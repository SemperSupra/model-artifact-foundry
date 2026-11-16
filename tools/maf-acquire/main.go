// Minimal source-only CLI; no network until explicitly passed -acquire-public-hf.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/SemperSupra/model-artifact-foundry/tools/maf-acquire/acquire"
	"os"
	"time"
)

func main() {
	manifest := flag.String("manifest", "", "immutable source request JSON")
	stage := flag.String("staging-dir", "", "empty temp dir")
	download := flag.Bool("acquire-public-hf", false, "execute official hf CLI for allowlisted public source; fail closed")
	flag.Parse()
	if *manifest == "" {
		fmt.Fprintln(os.Stderr, "-manifest required")
		os.Exit(2)
	}
	b, e := os.ReadFile(*manifest)
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(2)
	}
	r, e := acquire.Parse(b)
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(2)
	}
	if !*download {
		fmt.Println(`{"status":"PLAN_ONLY_NOT_DOWNLOADED","foundry_status":"NOT_ADOPTED"}`)
		return
	}
	if *stage == "" {
		fmt.Fprintln(os.Stderr, "-staging-dir required")
		os.Exit(2)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()
	rec, e := acquire.AcquireHF(ctx, r, *stage, acquire.ExecRunner)
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(3)
	}
	z, _ := json.MarshalIndent(rec, "", "  ")
	fmt.Println(string(z))
}
