// Package acquire implements bounded, exact-byte public model acquisition.
// It does not decide licensing, authorize gating, or produce a Foundry APPROVED identity.
package acquire

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"reflect"
	"regexp"
	"strings"
	"time"
)

var sha64 = regexp.MustCompile(`^[a-f0-9]{64}$`)
var sha40 = regexp.MustCompile(`^[a-f0-9]{40}$`)
var repo = regexp.MustCompile(`^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$`)

type Source struct {
	Provider   string `json:"provider"`
	Repository string `json:"repository"`
	Revision   string `json:"revision"`
	URL        string `json:"url,omitempty"`
	Access     string `json:"access"`
}
type File struct {
	Path     string `json:"path"`
	SHA256   string `json:"sha256"`
	MaxBytes int64  `json:"max_bytes"`
}
type Request struct {
	SchemaVersion           int    `json:"schema_version"`
	FoundryLogicalID        string `json:"foundry_logical_id"`
	SourceDeclarationSHA256 string `json:"source_declaration_sha256"`
	Source                  Source `json:"source"`
	Files                   []File `json:"files"`
	Promotion               string `json:"promotion"`
	LicenseEvidence         string `json:"license_evidence"`
}
type FileReceipt struct {
	Path   string `json:"path"`
	Bytes  int64  `json:"bytes"`
	SHA256 string `json:"sha256"`
}
type Receipt struct {
	Status        string        `json:"status"`
	Source        Source        `json:"source"`
	Files         []FileReceipt `json:"files"`
	FoundryStatus string        `json:"foundry_status"`
	IdentityKind  string        `json:"identity_kind"`
	Notes         string        `json:"notes"`
}

func safeRel(p string) bool {
	return p != "" && p == path.Clean(p) && !strings.HasPrefix(p, "/") && p != "." && p != ".." && !strings.HasPrefix(p, "../") && !strings.Contains(p, "\\") && !strings.Contains(p, ":") && !strings.Contains(p, "//")
}
func Validate(req Request) error {
	if req.SchemaVersion != 1 || req.Promotion != "candidate-only" {
		return errors.New("candidate-only schema version 1 required")
	}
	if !sha64.MatchString(req.SourceDeclarationSHA256) || len(req.FoundryLogicalID) < 3 || strings.ContainsAny(req.FoundryLogicalID, " \t\r\n\\") || strings.HasPrefix(req.FoundryLogicalID, "/") || strings.Contains(req.FoundryLogicalID, "..") {
		return errors.New("existing Foundry logical ID and independently pinned source declaration digest required")
	}
	if req.Source.Access != "public-ungated" {
		return errors.New("public actor cannot acquire gated/private source")
	}
	if req.LicenseEvidence != "independent-reviewed" {
		return errors.New("license/redistribution admission must be independently reviewed")
	}
	switch req.Source.Provider {
	case "huggingface":
		if !repo.MatchString(req.Source.Repository) || !sha40.MatchString(req.Source.Revision) || req.Source.URL != "" {
			return errors.New("HF origin requires repo and exact 40-hex revision, no custom endpoint")
		}
	case "github-release":
		if !repo.MatchString(req.Source.Repository) || !sha40.MatchString(req.Source.Revision) || req.Source.URL != "" {
			return errors.New("github release requires exact tag-target commit and repository")
		}
	case "https":
		if req.Source.Repository != "" || req.Source.Revision != "" || req.Source.URL != "" {
			return errors.New("HTTPS direct requests require per-file allowlisted URLs in a separate private adapter; no unbounded arbitrary fetch")
		}
	default:
		return errors.New("unknown provider")
	}
	if len(req.Files) == 0 || len(req.Files) > 16 {
		return errors.New("1 to 16 selected files required")
	}
	seen := map[string]bool{}
	var total int64
	for _, f := range req.Files {
		if !safeRel(f.Path) || seen[f.Path] || !sha64.MatchString(f.SHA256) || f.MaxBytes <= 0 || f.MaxBytes > 4*1024*1024*1024 {
			return fmt.Errorf("invalid selected file %q", f.Path)
		}
		if strings.HasSuffix(strings.ToLower(f.Path), ".pkl") || strings.HasSuffix(strings.ToLower(f.Path), ".pth") || strings.HasSuffix(strings.ToLower(f.Path), ".pt") {
			return fmt.Errorf("unsafe pickle-like file %q needs isolated approval", f.Path)
		}
		seen[f.Path] = true
		total += f.MaxBytes
		if total > 8*1024*1024*1024 {
			return errors.New("total byte budget exceeded")
		}
	}
	return nil
}

// Verify reads no more than a bounded number of bytes and rejects symlinks/oversized files.
func Verify(p string, f File) (FileReceipt, error) {
	fi, e := os.Lstat(p)
	if e != nil {
		return FileReceipt{}, e
	}
	if !fi.Mode().IsRegular() {
		return FileReceipt{}, errors.New("nonregular/symlink input")
	}
	// This source-only intake is Linux-hosted today. Fail closed on other
	// platforms if their file metadata cannot prove exclusive inode custody.
	// A matching hash alone never makes an external hardlink safe to adopt.
	v := reflect.ValueOf(fi.Sys())
	if v.Kind() != reflect.Ptr || v.IsNil() || v.Elem().Kind() != reflect.Struct {
		return FileReceipt{}, errors.New("filesystem link count unavailable")
	}
	linkCount := v.Elem().FieldByName("Nlink")
	if !linkCount.IsValid() || !linkCount.CanUint() || linkCount.Uint() != 1 {
		return FileReceipt{}, errors.New("external hardlink custody or unverifiable link count")
	}
	if fi.Size() > f.MaxBytes {
		return FileReceipt{}, fmt.Errorf("size exceeds budget: %d", fi.Size())
	}
	h := sha256.New()
	r, e := os.Open(p)
	if e != nil {
		return FileReceipt{}, e
	}
	defer r.Close()
	opened, e := r.Stat()
	if e != nil || !os.SameFile(fi, opened) {
		return FileReceipt{}, errors.New("file identity changed during open")
	}
	n, e := io.Copy(h, io.LimitReader(r, f.MaxBytes+1))
	if e != nil {
		return FileReceipt{}, e
	}
	if n > f.MaxBytes {
		return FileReceipt{}, errors.New("byte budget exceeded")
	}
	sum := hex.EncodeToString(h.Sum(nil))
	if sum != f.SHA256 {
		return FileReceipt{}, errors.New("digest mismatch")
	}
	return FileReceipt{Path: f.Path, Bytes: n, SHA256: sum}, nil
}

type Runner func(context.Context, string, ...string) error

func ExecRunner(ctx context.Context, name string, args ...string) error {
	c := exec.CommandContext(ctx, name, args...)
	c.Stdout = io.Discard
	c.Stderr = io.Discard
	return c.Run()
}

// verifyStagedAncestorPath rejects any symbolic-link parent created by the
// downloader between the trusted empty staging root and one selected file.
// Checking Lstat only on the final file is insufficient.
func verifyStagedAncestorPath(root, relative string) error {
	parent := filepath.Dir(filepath.FromSlash(relative))
	if parent == "." {
		return nil
	}
	cur := root
	for _, part := range strings.Split(parent, string(filepath.Separator)) {
		cur = filepath.Join(cur, part)
		info, err := os.Lstat(cur)
		if err != nil {
			return err
		}
		if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("unsafe staged ancestor directory: %s", relative)
		}
	}
	return nil
}

// AcquireHF delegates transfer to the official, pinned hf CLI; never runs upstream code.
// Caller must provide a newly created empty workdir to prevent stale file substitution.
func AcquireHF(ctx context.Context, req Request, dir string, run Runner) (Receipt, error) {
	if e := Validate(req); e != nil {
		return Receipt{}, e
	}
	if req.Source.Provider != "huggingface" {
		return Receipt{}, errors.New("HF-only transfer")
	}
	st, e := os.Lstat(dir)
	if e != nil || !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
		return Receipt{}, errors.New("safe staging directory required")
	}
	entries, e := os.ReadDir(dir)
	if e != nil {
		return Receipt{}, e
	}
	if len(entries) != 0 {
		return Receipt{}, errors.New("staging directory not empty")
	}
	args := []string{"download", req.Source.Repository}
	for _, f := range req.Files {
		args = append(args, f.Path)
	}
	args = append(args, "--revision", req.Source.Revision, "--local-dir", dir)
	if e := run(ctx, "hf", args...); e != nil {
		return Receipt{Status: "WAIT_TRANSFER_OR_ACCESS", Source: req.Source, FoundryStatus: "NOT_ADOPTED", IdentityKind: "none", Notes: "no verified completed download"}, e
	}
	out := Receipt{Status: "STAGED_VERIFIED_NOT_PROMOTED", Source: req.Source, FoundryStatus: "CANDIDATE_ONLY", IdentityKind: "file-sha256", Notes: "not a Foundry identity; run existing Foundry adopt/verification and rights gates independently"}
	for _, f := range req.Files {
		if e := verifyStagedAncestorPath(dir, f.Path); e != nil {
			return Receipt{Status: "HOLD_UNSAFE_CUSTODY", Source: req.Source, FoundryStatus: "NOT_ADOPTED", IdentityKind: "none"}, e
		}
		rec, e := Verify(filepath.Join(dir, filepath.FromSlash(f.Path)), f)
		if e != nil {
			return Receipt{Status: "HOLD_INVALID_BYTES", Source: req.Source, FoundryStatus: "NOT_ADOPTED", IdentityKind: "none"}, e
		}
		out.Files = append(out.Files, rec)
	}
	return out, nil
}

// GitHubReleaseURL constructs a pinned repository release-asset locator only.
// Resolving a tag to a commit does not pin the binary; exact SHA256 verification is mandatory.
func GitHubReleaseURL(ownerRepo, tag, asset string) (string, error) {
	if !repo.MatchString(ownerRepo) || tag == "" || strings.ContainsAny(tag, "/?#\\\r\n") || !safeRel(asset) || strings.Contains(asset, "/") {
		return "", errors.New("invalid release locator")
	}
	return "https://github.com/" + ownerRepo + "/releases/download/" + tag + "/" + asset, nil
}

// FetchPinnedHTTPS downloads only from an exact allowlisted HTTPS origin with a
// pinned digest and a bounded byte budget. Tampered/partial results never land
// in the candidate path. Redirects must stay within the explicit host allowlist.
func FetchPinnedHTTPS(ctx context.Context, transport http.RoundTripper, rawurl string, allowedHosts []string, maxBytes int64, wantSHA, destination string) (FileReceipt, error) {
	u, err := url.Parse(rawurl)
	if err != nil || u.Scheme != "https" || u.User != nil || u.Hostname() == "" || u.Fragment != "" || !sha64.MatchString(wantSHA) || maxBytes <= 0 || maxBytes > 4*1024*1024*1024 {
		return FileReceipt{}, errors.New("invalid immutable HTTPS acquisition parameters")
	}
	hostOK := func(host string) bool {
		for _, allowed := range allowedHosts {
			if host == allowed {
				return true
			}
		}
		return false
	}
	if !hostOK(u.Hostname()) {
		return FileReceipt{}, errors.New("HTTPS source host not explicitly admitted")
	}
	client := &http.Client{Transport: transport, Timeout: 2 * time.Minute,
		CheckRedirect: func(r *http.Request, via []*http.Request) error {
			if len(via) > 3 || r.URL.Scheme != "https" || !hostOK(r.URL.Hostname()) {
				return errors.New("redirect outside allowed HTTPS hosts")
			}
			return nil
		},
	}
	req, err := http.NewRequestWithContext(ctx, "GET", rawurl, nil)
	if err != nil {
		return FileReceipt{}, err
	}
	res, err := client.Do(req)
	if err != nil {
		return FileReceipt{}, err
	}
	defer res.Body.Close()
	if res.StatusCode != 200 || res.ContentLength > maxBytes {
		return FileReceipt{}, fmt.Errorf("HTTP status or size denied: %d", res.StatusCode)
	}
	if destination == "" {
		return FileReceipt{}, errors.New("destination missing")
	}
	if _, e := os.Lstat(destination); e == nil {
		return FileReceipt{}, errors.New("destination already exists")
	} else if !os.IsNotExist(e) {
		return FileReceipt{}, e
	}
	parent := filepath.Dir(destination)
	if st, e := os.Lstat(parent); e != nil || !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
		return FileReceipt{}, errors.New("unsafe staging parent")
	}
	tmp, err := os.CreateTemp(parent, ".foundry-*.partial")
	if err != nil {
		return FileReceipt{}, err
	}
	defer os.Remove(tmp.Name())
	defer tmp.Close()
	h := sha256.New()
	n, err := io.Copy(io.MultiWriter(tmp, h), io.LimitReader(res.Body, maxBytes+1))
	if err != nil {
		return FileReceipt{}, err
	}
	if n > maxBytes || hex.EncodeToString(h.Sum(nil)) != wantSHA {
		return FileReceipt{}, errors.New("source bytes failed budget/digest")
	}
	if err := tmp.Sync(); err != nil {
		return FileReceipt{}, err
	}
	if err := tmp.Close(); err != nil {
		return FileReceipt{}, err
	}
	if err := os.Rename(tmp.Name(), destination); err != nil {
		return FileReceipt{}, err
	}
	return FileReceipt{Path: u.Hostname() + u.EscapedPath(), Bytes: n, SHA256: wantSHA}, nil
}
func Parse(b []byte) (Request, error) {
	var r Request
	d := json.NewDecoder(strings.NewReader(string(b)))
	d.DisallowUnknownFields()
	if e := d.Decode(&r); e != nil {
		return r, e
	}
	return r, Validate(r)
}
