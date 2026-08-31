# Faster Whisper `tiny` proof of concept

This is the deliberately narrow end-to-end proof for Model Artifact Foundry issue #3.

## Fixed inputs

- logical artifact ID: `asr/faster-whisper/tiny`
- upstream repository: `Systran/faster-whisper-tiny`
- exact upstream revision: `d90ca5fe260221311c53c58e660288d3deb8d356`
- observed source metadata for the proof: public, non-gated, MIT
- validator: `faster-whisper==1.2.1`, `ctranslate2==4.6.0`
- behavior fixture: `openai/whisper/tests/jfk.flac` at commit `6e3be77e1a105e59086e3e21ff5f609fd6fa89a5`
- OCI repository: `ghcr.io/sempersupra/model-artifact-foundry`
- candidate tag: `candidate-asr-faster-whisper-tiny-d90ca5fe2602`

The candidate tag is only a locator. The OCI `sha256:` digest emitted after publication is the artifact identity.

## What trusted-main publication proves

The one-shot workflow:

1. checks that the public upstream metadata still identifies the exact pinned revision and MIT/non-gated state;
2. downloads only `config.json`, `model.bin`, `tokenizer.json`, and `vocabulary.txt` from that exact revision;
3. hashes every file and enforces the declared size ceiling;
4. loads the model from the explicit local directory with `local_files_only=True` and offline environment flags;
5. transcribes the pinned JFK fixture and checks expected English phrases;
6. builds a deterministic `model.tar.gz` with normalized archive metadata;
7. publishes the archive, bundle manifest, and notice as a generic OCI artifact;
8. resolves the registry digest, pulls the artifact back by digest, and re-verifies the bundle;
9. writes a schema-valid candidate manifest to a separate evidence branch.

Candidate publication does **not** update `catalog/approved.json`.

## Promotion

After the evidence branch is reviewed and merged, promotion is one small catalog PR. The catalog entry records:

- OCI repository;
- immutable approved digest;
- exact upstream revision;
- immutable candidate evidence commit/path;
- MIT license identity;
- compatibility evidence.

No consumer should resolve the candidate tag or upstream `main`.

## Generic hydration

`tools/hydrate.py` consumes the approved catalog and an artifact logical ID.

Example:

```bash
oras login ghcr.io
python3 tools/hydrate.py \
  --catalog catalog/approved.json \
  --id asr/faster-whisper/tiny \
  --cache-root /cache/models/asr
```

The hydrator pulls `repository@sha256:digest`, stages it under `.staging`, verifies the bundle/archive/per-file hashes, safely extracts the allowlisted model files, atomically promotes the content-addressed directory, and writes a small selection JSON under `selected/`.

Repeated hydration of an intact selected digest verifies the existing files and performs no download. Older digest directories are retained for rollback.

The command prints the explicit local model directory. BHADA should pass that directory to Faster Whisper rather than asking Faster Whisper to resolve a remote model name.

## BHADA boundary

The intended BHADA mapping is:

```text
/cache/models/asr/
  blobs/sha256-<digest>/
    bundle-manifest.json
    NOTICE.txt
    .verified.json
    model/
      config.json
      model.bin
      tokenizer.json
      vocabulary.txt
  selected/
    asr__faster-whisper__tiny.json
```

BHADA `runtime-full` can consume the printed `model/` path with ASR model auto-download disabled. `runtime-core` remains model- and ASR-package-free.

## Package visibility

GitHub Container Registry creates a new package as private by default. The publication/pull-back proof works with the workflow's `GITHUB_TOKEN`. A deployment can also authenticate ORAS.

If anonymous public consumption is desired, an organization/package administrator must change the package visibility to **Public** in GitHub package settings. GitHub documents that this visibility change is irreversible, so it remains a deliberate owner action rather than an automated workflow side effect.

## Scope stop

Once one digest is approved and BHADA can hydrate/use it, this proof is done. Scheduled discovery, additional models, second-consumer work, generalized harvesters, and large-model infrastructure are later work only if the Foundry proves enough value to justify them.
