# Experimental multifile OCI hydration — local, source-only, non-promoting

This is an independently scoped Go standard-library experiment in the **existing Model Artifact Foundry**, not a replacement for the approved `tools/hydrate.py` or an authorized model publisher.

## Why this experiment exists

The current approved Foundry hydrator expects a single `model.tar.gz` plus bundle metadata. The original pinned Edge0 35B source comprises **11 files**, including four ~4.4–5.4 GB safetensors shards and two smaller weight components. Individual upstream files are below the conservative 9 GB OCI-layer planning bound, but the entire source (~19.71 GB) cannot be put into a single compliant GHCR layer. The separate synthetic chunker PR #88 and strict manifest PR #90 tested a single logical byte file; this work tests the missing *multiple independent source files → OCI layers → content-addressed selected directory* boundary without model bytes.

## Exact scope

The workcell creates 11 **synthetic**, model-named, random byte files; a bounded, exact-revision and logical-ID manifest records sorted file basename, size, and SHA256. The Go `pack` command refuses symlinks, unknown/unsafe filenames, mutable revision aliases, overlong manifests, existing outputs and unbounded source dimensions. `hydrate` refuses unsafe/unknown/duplicate JSON, extra, missing, changed or symlinked members. A verified digest-named blob is installed atomically; the selected logical ID is only updated *after* full verification. Existing verified blobs are rechecked and reused; malformed inputs leave the prior selection unchanged. Different exact source revisions coexist.

On two standard public GHA Ubuntu CPU architectures (x64 and ARM64), actual ORAS 1.3.3 serializes the 11 synthetic raw files plus one manifest as separate layers into a local OCI layout. The workflow reads the layout manifest descriptor, pulls by immutable digest, then exercises fresh hydration and same-job offline cache hit. A machine receipt records only grounded synthetic success and refuses all model approval or registry publication claims. Go race, vet and adversarial tests run independently.

## Adoption boundaries

- Not an approved Foundry artifact schema and not drop-in compatible with the existing catalog or `tools/hydrate.py`.
- Source file-level SHA, local OCI layout digest, and source revision identity are three distinct things. The synthetic Go cache does not establish signed publisher provenance or approved upstream licensing.
- Standard public runner storage is ephemeral. This does not prove GHCR upload/readback, permission, retries, timeout, >5 GB layer transfer, streaming speed, local NVMe, full 35B checkpoint inference, or statefully durable storage across runners.
- Full source byte verification, derivative/conversion rights, license and mirror authorization remain **private Model Artifact Foundry #6**; model selection is **private #7**. BrowserParity runtime acceptance remains its **private #109 and #25**. Never use this experiment to bypass human browser authorization, prompt-effect policy, or Evidence Service custody.
- Source-side TOCTOU, concurrent multiprocess atomic selection, filesystem durability/fsync, signed provenance, cross-platform cache portability, and multi-GB streaming limits are **not qualified**. Keep draft and no production adoption.

This is a feasibility and negative-test gate to determine whether raw original files can be retrieved, verified, selected and rolled back without a giant tar. No real model bytes, tokens, private source, registry writes or paid private GHA minutes.
