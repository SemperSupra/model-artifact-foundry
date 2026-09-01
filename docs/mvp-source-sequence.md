# Thin MVP source sequence

## Decision

Keep the implementation sequence deliberately narrow.

### Phase 1 — establish identity

1. Hugging Face: mutable model/repository locator -> exact repository revision and file metadata.
2. Civitai: model-version ID -> provider file hashes and artifact metadata.
3. Ollama: installed model tag -> actual local digest/format/quantization without `pull`.
4. One direct hosted provider: observable provider-model/version identity, explicitly weaker than bit-level artifact identity.

### Phase 2 — lifecycle/context enrichment

Only after Phase 1 normalizes/diffs correctly:

1. LLM Releases for release/deprecation/withdrawal and primary-source context.
2. Epoch AI for historical/model-family/accessibility enrichment.
3. LMArena for external behavioral/performance history after model-identity reconciliation is explicit.

### Restricted/reference-only

- OpenRouter: minimal watched-model lookup/crosswalk unless a clearer bulk-ingestion permission is established.
- Artificial Analysis: private/internal enrichment only under Free API terms; do not republish raw/detailed data without compatible rights.

## Anti-duplication gate

Do not ingest an external dataset or add a field until we can name the specific value it contributes that authoritative primary sources and already-integrated observatories do not.

The foundry is not rewarded for the size of its dataset. It is rewarded for joining dependency-grade identity to longitudinal evidence and experiment provenance.
