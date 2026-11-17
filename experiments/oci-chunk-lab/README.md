# Source-only, offline OCI model-chunk qualification

This is an **experimental** Go standard-library chunker and validator in the existing public Model Artifact Foundry, not a new publisher, a replacement for the approved `tools/hydrate.py`, or a production model-cache service.

Synthetic bytes are split into deterministic bounded parts, each with SHA-256, index and byte count; a separate manifest records the whole-file SHA-256, logical identifier, source filename and exact parts. Recovery rejects changed/missing/extra/out-of-order files, symlinks, unsafe paths, invalid digests, changed sizes and replacing previously selected output. The test fixture is deliberately small and unrelated to real model weights.

GHA runs on independent free public x64 and ARM64 Ubuntu hosts. Existing ORAS 1.3.3 is used to push and pull the test bundle through a **local OCI layout**, not GHCR. Exact bytes must survive its genuine layer serialization and reconstruction. No secrets or private Actions minutes, GHCR write, catalog promotion, model download or actual 35B inference.

GHCR's present limit is 10 GB **per layer**, with a 10-minute upload timeout. The prototype rejects part sizes over 9 GB, but production use would choose much smaller layers (e.g. 128 MiB–2 GiB) based on measured transfer throughput and retry costs. This experimental manifest is **not** the Foundry approved OCI bundle schema and must not be silently accepted as one. An OCI manifest digest and MAF candidate review would remain authoritative for remote publication.

**DLE authority:** MAF public `AGENTS.md`, `docs/architecture/future-model-publishing.md`, MAF-private #6 (source rights and mirrors), MAF-private #7 (model selection), BrowserParity-private #25 (workload evidence). No upstream model mirroring without applicable owner approval. This proposal is deliberately separate from the existing pending Foundry PRs.
