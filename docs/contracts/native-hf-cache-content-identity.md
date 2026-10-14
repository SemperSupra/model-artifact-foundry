# Content-manifest identity from a native Hugging Face snapshot (no-copy)

This bounded host-side, **offline** adapter complements the already-established
Foundry `adopt_local_artifact.py` content-manifest contract and the provider-native
materialization work in draft PR #30. It neither replaces the Hugging Face
provider adapter nor operates as a second model downloader/cache.

Given an **already-present**, exact 40-hex HF repository snapshot in the native
Hub cache, `tools/adopt_hf_native_snapshot.py` resolves ordinary model files
and relative HF symlinks to repository-local or hub-shared blob objects.
It rejects arbitrary external paths, absolute symlinks, symlink directories,
missing files, nonregular objects, invalid revisions, and oversized inventories.
It hashes the verified file bytes while preserving their **logical snapshot
relative paths**, then calls Foundry's canonical `adopt_file_records` identity
function. It never copies model data into a warehouse or publishes model bytes.

```bash
python3 tools/adopt_hf_native_snapshot.py \
  --declaration /path/to/local-only-hf-declaration.json \
  --hub-cache /path/to/existing/huggingface/hub \
  --source-revision <exact-40-hex-commit> \
  --output /path/to/new-evidence-receipt.json
```

The declaration must obey the existing fail-closed local-acquisition policy.
The returned `content-manifest` SHA256 matches normal local adoption of the
same logical files, upstream metadata and exact revision. It does **not**
prove model license/distribution permission, quality or compatibility.
It is a **local identity**, not a published OCI digest, and the consumer
continues to use its provider-native cache rather than an additional mirror.

Non-HF caches consisting of ordinary files (e.g. provider-owned application
model directories) should call `tools/adopt_local_artifact.py` directly.
Retain **separate** identities for independently versioned model families.
Host/target-specific inference validation remains owned by the consumer.

This implementation is opt-in. It does not revise `adopt_local_artifact`'s
intentional default rejection of symlinks, nor change approval/promotion.
Use per-project private policy for actual model selection, licenses and
provisioning; do not publish aggregated operational inventories.
