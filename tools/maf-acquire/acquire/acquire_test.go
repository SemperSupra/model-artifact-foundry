package acquire

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func req() Request {
	data := sha256.Sum256([]byte("synthetic public bytes"))
	return Request{1, "tts/synthetic/public", strings.Repeat("b", 64), Source{Provider: "huggingface", Repository: "example/public-model", Revision: strings.Repeat("a", 40), Access: "public-ungated"}, []File{{"sub/model.onnx", hex.EncodeToString(data[:]), 256}}, "candidate-only", "independent-reviewed"}
}
func TestAcceptPinned(t *testing.T) {
	if e := Validate(req()); e != nil {
		t.Fatal(e)
	}
}
func TestNoGated(t *testing.T) {
	r := req()
	r.Source.Access = "gated"
	if Validate(r) == nil {
		t.Fatal("gated accepted")
	}
}
func TestNoMutable(t *testing.T) {
	r := req()
	r.Source.Revision = "main"
	if Validate(r) == nil {
		t.Fatal("mutable accepted")
	}
}
func TestNoOverbudget(t *testing.T) {
	r := req()
	r.Files[0].MaxBytes = 5 << 30
	if Validate(r) == nil {
		t.Fatal("budget accepted")
	}
}
func TestNoTraversal(t *testing.T) {
	for _, p := range []string{"../foo", "x/../foo", "/etc/passwd", "x\\evil", "x//y"} {
		r := req()
		r.Files[0].Path = p
		if Validate(r) == nil {
			t.Fatal(p)
		}
	}
}
func TestNoUnsafeWeights(t *testing.T) {
	r := req()
	r.Files[0].Path = "bad.pth"
	if Validate(r) == nil {
		t.Fatal("pickle accepted")
	}
}
func TestNoDuplicate(t *testing.T) {
	r := req()
	r.Files = append(r.Files, r.Files[0])
	if Validate(r) == nil {
		t.Fatal("duplicate")
	}
}
func TestNoPublicPromotion(t *testing.T) {
	r := req()
	r.Promotion = "approved"
	if Validate(r) == nil {
		t.Fatal("self-approved")
	}
}
func TestNoUnreviewedLicense(t *testing.T) {
	r := req()
	r.LicenseEvidence = "metadata-only"
	if Validate(r) == nil {
		t.Fatal("unreviewed license")
	}
}
func TestRejectUnknown(t *testing.T) {
	r := req()
	b := `{"schema_version":1,"bogus":42}`
	_, e := Parse([]byte(b))
	if e == nil {
		t.Fatal(r)
	}
}
func TestSyntheticHFDownload(t *testing.T) {
	dir := t.TempDir()
	r := req()
	called := false
	run := func(ctx context.Context, n string, args ...string) error {
		called = true
		if n != "hf" || args[0] != "download" {
			t.Fatal(n, args)
		}
		p := filepath.Join(dir, "sub")
		if e := os.MkdirAll(p, 0700); e != nil {
			return e
		}
		return os.WriteFile(filepath.Join(p, "model.onnx"), []byte("synthetic public bytes"), 0600)
	}
	z, e := AcquireHF(context.Background(), r, dir, run)
	if e != nil || !called || z.Status != "STAGED_VERIFIED_NOT_PROMOTED" || len(z.Files) != 1 {
		t.Fatal(z, e)
	}
}
func TestBadDownloadedBytes(t *testing.T) {
	dir := t.TempDir()
	r := req()
	_, e := AcquireHF(context.Background(), r, dir, func(_ context.Context, _ string, _ ...string) error {
		p := filepath.Join(dir, "sub")
		os.MkdirAll(p, 0700)
		return os.WriteFile(filepath.Join(p, "model.onnx"), []byte("tampered"), 0600)
	})
	if e == nil {
		t.Fatal("checksum didn't reject")
	}
}
func TestRejectOccupiedStage(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "stale"), []byte("x"), 0600)
	r := req()
	_, e := AcquireHF(context.Background(), r, dir, func(_ context.Context, _ string, _ ...string) error { return nil })
	if e == nil {
		t.Fatal("stale bytes")
	}
}
func TestNoHTTPSFallback(t *testing.T) {
	r := req()
	r.Source.Provider = "https"
	r.Source.Repository = "https://evil.example"
	if Validate(r) == nil {
		t.Fatal("unbounded https")
	}
}
func TestReleaseLocator(t *testing.T) {
	u, e := GitHubReleaseURL("example/model", "v1.2.3", "model.onnx")
	if e != nil || !strings.Contains(u, "/releases/download/") {
		t.Fatal(u, e)
	}
	_, e = GitHubReleaseURL("example/model", "v1.2.3", "../bad")
	if e == nil {
		t.Fatal("traversal release")
	}
}

func TestHTTPSPinnedSynthetic(t *testing.T) {
	server := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("synthetic public bytes")) }))
	defer server.Close()
	u, _ := url.Parse(server.URL)
	sha := sha256.Sum256([]byte("synthetic public bytes"))
	out := filepath.Join(t.TempDir(), "model.onnx")
	got, e := FetchPinnedHTTPS(context.Background(), server.Client().Transport, server.URL+"/model.onnx", []string{u.Hostname()}, 100, hex.EncodeToString(sha[:]), out)
	if e != nil || got.Bytes != 22 {
		t.Fatal(got, e)
	}
	if _, e := os.Stat(out); e != nil {
		t.Fatal(e)
	}
}
func TestHTTPSWrongDigestNoFile(t *testing.T) {
	server := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("tampered")) }))
	defer server.Close()
	u, _ := url.Parse(server.URL)
	out := filepath.Join(t.TempDir(), "bad.onnx")
	_, e := FetchPinnedHTTPS(context.Background(), server.Client().Transport, server.URL+"/bad", []string{u.Hostname()}, 100, strings.Repeat("0", 64), out)
	if e == nil {
		t.Fatal("bad digest accepted")
	}
	if _, e := os.Stat(out); !os.IsNotExist(e) {
		t.Fatal("bad output published")
	}
}
func TestHTTPSNotAllowlisted(t *testing.T) {
	_, e := FetchPinnedHTTPS(context.Background(), http.DefaultTransport, "https://evil.example/model.onnx", []string{"trusted.example"}, 1, strings.Repeat("0", 64), filepath.Join(t.TempDir(), "out"))
	if e == nil {
		t.Fatal("unapproved host accepted")
	}
}
func TestHTTPSRedirectRejected(t *testing.T) {
	server := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "https://evil.example/model", http.StatusFound)
	}))
	defer server.Close()
	u, _ := url.Parse(server.URL)
	_, e := FetchPinnedHTTPS(context.Background(), server.Client().Transport, server.URL+"/x", []string{u.Hostname()}, 100, strings.Repeat("0", 64), filepath.Join(t.TempDir(), "out"))
	if e == nil {
		t.Fatal("external redirect accepted")
	}
}
