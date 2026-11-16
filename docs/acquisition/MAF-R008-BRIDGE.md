# R008 — Test-only Foundry canonical identity bridge and private Drive custody

The upstream public GitHub Actions job is a **neutral fixture transport experiment**, not a promotion authority, Thai TTS model intake, or license/redistribution oracle.

## Public provenance controls

1. The neutral fixture witness is committed under `examples/test-fixtures/r008-hf-public-safetensors.json`, explicitly `TEST_ONLY_NOT_APPROVED_NOT_MIRRORABLE` with source revision `8301186e0724d418a8d4f5eb17011c9226f5b766`, `model.safetensors` SHA256 `965f02b6a7e5520fc12f710e4e3b6132f697f1c8f648819553c5ade86752d2de`, a 1 MiB transfer cap, and no license acceptance.
2. The workflow anonymously checks current HF metadata against the pinned commit and independently published expected file hash. The public-ungated neutral fixture uses `license_evidence=public-neutral-fixture-transport-only`, requiring the `test-fixture/` logical ID and ≤2 MiB per file. No policy string is authentication or authorization.
3. The **actual Go acquisition CLI** executes `hf download` into an empty temporary directory. It independently hashes the bytes and returns **`STAGED_VERIFIED_NOT_PROMOTED`**. It rejects symlinked ancestry, external hardlinks, unsafe pickle, unpinned source and invalid path/budget.
4. `bridge_canonical.py` separately reads actual staged bytes, checks the Go receipt and file bytes against committed witness, and **imports canonical identity material and `content_manifest_digest` from existing `tools/adopt_local_artifact.py`**, not a new identity algorithm. Its output is `CANDIDATE_CONTENT_DIGEST_COMPUTED_ONLY_NOT_APPROVED`, not an adopted `content-manifest` or approved OCI digest.
5. Safetensors metadata is inspected without loading model tensors or executing upstream model code. Staged files, Go receipt and fixture candidate identity are deleted at job completion. No GHCR/Drive/public artifact bytes or project-private model IDs are published.
6. Three extra fail-closed Go parser controls reject duplicate JSON keys at root/nested levels and appended JSON documents; the fourth new control limits the neutral test class to bounded public HF fixtures. Python contract tests reject tampered binary and Go receipts, source revision mismatch, external links, false approval and missing bytes.

## Independence and integration holds

The test fixture witness is *not* a production `schemas/source-declaration.schema.json` claim and its `license_admission` is unverified. Candidate digest computation exercises existing Foundry semantics but does **not** establish rights, trusted model quality, source consent or canonical adoption of a real consumer model. Draft Foundry #70/#71 remain the authoritative no-copy native HF cache adoption and independent expected-digest verification work. Later integrate against those reviewed contracts rather than publish a competing cache or registry.

Private R008 Google Drive custody readback is for an original **synthetic** 524,512-byte safetensors tensor, not an externally trained model; hash equality and tensor parse after full authenticated restore were observed, and `shared=false` owner-only metadata was read. No third-party model weights, user voice, private corpora, large shard capacity or automatic restore service were qualified.

## Gate state

- `PUBLIC_NEUTRAL_TRANSFER`: TEST-ONLY PASS on free public GHA #43840509916 (three jobs success), exact tested source SHA `2d3b45e03192beb0c579ce1045da06a3e1a63582`. First GHA #43839915446 failed due to incorrect JSON receipt key capitalization and was preserved; source-bound test added and rerun passed.
- `STANDOFF_CANONICAL_DIGEST`: computed test-only, not approved.
- `PRIVATE_SYNTHETIC_DRIVE_BYTE_CUSTODY`: verified for this one small synthetic file.
- `THAI_TTS_MODEL_ACQUISITION`: held pending source rights, exact weights, private executor admission and native evaluation.
- `PUBLISHING`: P0 multilingual ShelfMark release gates unchanged.
