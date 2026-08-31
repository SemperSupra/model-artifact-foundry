# Faster Whisper `tiny` proof of concept

This is the deliberately narrow end-to-end proof for Model Artifact Foundry issue #3.

## Result — complete

The proof succeeded. The approved artifact is:

- logical artifact ID: `asr/faster-whisper/tiny`
- upstream repository: `Systran/faster-whisper-tiny`
- exact upstream revision: `d90ca5fe260221311c53c58e660288d3deb8d356`
- OCI repository: `ghcr.io/sempersupra/model-artifact-foundry`
- approved OCI digest: `sha256:f2d664ae986b0b0598037a9f0b929fd0b0b748871474a06c84658c1f2a1a4b42`
- model archive SHA-256: `9e578a3dc8d8ac2178a4e986a8f02e488c94bf814dd7ba51701591a76093c829`
- canonical candidate evidence commit: `4a82c5d72dd3fef6bef3dccdace23a5c1859636c`
- operationally tested Foundry head: `46dc566f59a8ab28a5a00c1eeaa2e6ef132c014b`
- validator: `faster-whisper==1.2.1`, `ctranslate2==4.6.0`
- behavior fixture: `openai/whisper/tests/jfk.flac` at commit `6e3be77e1a105e59086e3e21ff5f609fd6fa89a5`
- observed source metadata for the proof: public, non-gated, MIT

The candidate tag `candidate-asr-faster-whisper-tiny-d90ca5fe2602` is only a locator. The OCI digest above is the approved artifact identity.

## Evidence sequence

Trusted-main publication run `33438050007` successfully:

1. verified the pinned upstream revision and MIT/non-gated state;
2. downloaded only `config.json`, `model.bin`, `tokenizer.json`, and `vocabulary.txt`;
3. hashed every file and enforced the size ceiling;
4. loaded the model from the explicit local directory with `local_files_only=True` and offline environment flags;
5. transcribed the pinned JFK fixture and passed expected English phrase checks;
6. built the deterministic model archive;
7. published the generic OCI candidate at the digest above.

The first pull-back verifier revealed that ORAS preserves the original `dist/` source directory when pulling these layers. That was a verifier-path observation, not a model or registry failure.

Recovery run `33438464760` then pulled the **existing digest without republishing it**, verified the archive and per-file hashes, and produced the schema-valid candidate evidence that is now canonical at commit `4a82c5d72dd3fef6bef3dccdace23a5c1859636c`.

Promotion subsequently bound `asr/faster-whisper/tiny` to that immutable digest in `catalog/approved.json`.

Final consumer run `33438707454` successfully:

1. validated the approved catalog;
2. hydrated an empty cache by `repository@sha256:digest`;
3. verified bundle, archive and per-file identities;
4. ran hydration again with ORAS deliberately replaced by `/bin/false`, proving the intact local cache is sufficient;
5. loaded Faster Whisper from the hydrated local directory with model networking disabled;
6. transcribed the pinned JFK fixture successfully.

## Generic hydration

`tools/hydrate.py` consumes the approved catalog and an artifact logical ID.

```bash
oras login ghcr.io
python3 tools/hydrate.py \
  --catalog catalog/approved.json \
  --id asr/faster-whisper/tiny \
  --cache-root /cache/models/asr
```

The hydrator pulls the approved immutable digest, stages it under `.staging`, verifies the OCI-selected bundle/archive/per-file hashes, safely extracts the allowlisted model files, atomically promotes the content-addressed directory, and writes a small selection JSON under `selected/`.

Repeated hydration of an intact digest verifies the existing local files and performs no download. Older digest directories can coexist for rollback.

## BHADA boundary

With `/cache/models/asr` as the cache root, BHADA receives:

```text
/cache/models/asr/
  blobs/sha256-f2d664ae986b0b0598037a9f0b929fd0b0b748871474a06c84658c1f2a1a4b42/
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

The selected JSON identifies the exact digest and explicit local `model/` directory. BHADA `runtime-full` can pass that directory to Faster Whisper with ASR model auto-download disabled. `runtime-core` remains model- and ASR-package-free.

## Package visibility

The GHCR package was created through the repository workflow and is usable with authenticated ORAS access. Anonymous public package access is optional rather than required for this proof. Changing GHCR package visibility to public is a separate owner decision and is not part of the BHADA MVP critical path.

## Scope stop

This proof is complete. Scheduled discovery, additional models, second-consumer work, generalized harvesters, and large-model infrastructure are deferred. Further Foundry work should occur in its own session and must justify expansion against the private value/kill criteria rather than continuing as part of BHADA's MVP work.
