# MakeHuman archived-community source adapter (research)

This is a read-only discovery adapter stacked on the existing MAF R006 acquisition preflight PR #80. **It does not download, install, assert permission, create an approved identity or replace the MAF artifact catalog.**

Offline use from `tools/maf-acquire`:

```bash
go run ./cmd/makehuman-catalog -catalog /path/to/assets.json -q human -type model -license CC0
```

Upstream archived catalog: https://files.makehumancommunity.org/sites/default/files/assets.json

The legacy browse/search service was disabled in October 2026. Asset-pack archive directory: https://static.makehumancommunity.org/assets/assetpacks/index.html . This adapter treats any listed URL, especially historical HTTP URLs, as an **untrusted discovery hint**. It performs no automatic network access, protocol upgrade, host authorization, extraction, mirroring, or rights promotion. Repeatable acquisition needs exact snapshot SHA-256 plus per-file upstream hash witnesses, independently checked license, source allowlist and bounded transfer policy. Use existing MAF `acquire.FetchPinnedHTTPS` after those gates, and then the existing adopt/hydrate lifecycle; do not duplicate the downloader.

No public/private inventory, owner preferences, Drive locations, credentials or private source material belong in this adapter. MAF private #6 retains operational provider/custody admission; Stable Character private R014 #138 owns the human-model quality test results.

Acceptance for this first bounded rep: source-only `go test ./...`, `go test -race ./...`, `go vet ./...`; deterministic offline filtering; malformed/oversize negative controls; no network; no actual upstream archive claims. Follow-on independent work can add a bounded pinned-source transfer receipt to the generic downloader without building a dedicated MakeHuman warehousing service.
