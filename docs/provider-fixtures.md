# Metadata-only provider fixtures

This directory supports issue #12: capture enough provider evidence to classify identity strength **without downloading model/checkpoint bytes**.

## Boundary

Fixtures are evidence samples, not a mirrored model catalog. They must not contain credentials, cookies, private endpoints, unrelated local inventory, or model/checkpoint/archive bytes.

Public provider responses are deliberately projected to the fields needed for identity, lifecycle, access, and later normalization tests. The full transient provider response is not retained merely because it is available. This follows the Foundry data-minimization rule: retain a field only when we can name the identity/lifecycle question it answers.

The capture tool deliberately accepts no authentication material. If a proof case requires authenticated/gated access, that observation belongs in the private operational plane until a separate public-safety projection is reviewed.

## Capture commands

These commands are read-only metadata requests and overwrite the named JSON/sidecar atomically.

```bash
python tools/capture_provider_metadata.py \
  --output fixtures/raw/huggingface/kv-ground-main.json \
  huggingface \
  --repo vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315 \
  --revision main

python tools/capture_provider_metadata.py \
  --output fixtures/raw/huggingface/kv-ground-fe756329.json \
  huggingface \
  --repo vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315 \
  --revision fe7563292bb52ab6c235fc3c87157e6a14017479

python tools/capture_provider_metadata.py \
  --output fixtures/raw/civitai/model-version-128713.json \
  civitai \
  --version-id 128713

python tools/capture_provider_metadata.py \
  --output fixtures/raw/openrouter/<model-id>.json \
  openrouter \
  --model-id <exact-openrouter-model-id>
```

Do not substitute an invented/synthetic response when a provider cannot be reached. Record the missing evidence and capture it later from an authorized network path.

## Current evidence state

### Ollama — partial

`fixtures/raw/ollama/kv-ground-8b.tags.json` is a deliberately narrow sanitized projection from an authorized local inventory snapshot. It preserves one installed model's provider-native digest and representation metadata:

- `kv-ground-8b:latest`
- digest `fa1d74b1cd05750f3d17025f35f70272b883cf09757d771488be5cba103f7b37`
- GGUF, Q4_K_M, 8.2B, context 32768

Hostname, endpoint, unrelated inventory, local filesystem details, and credentials are excluded.

A genuine sanitized `/api/show` response is still required before the Ollama proof case is complete. Do not fabricate it from `/api/tags` fields.

### Hugging Face KV-Ground — captured

The target is `vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315`.

Reviewed public capture evidence from workflow run `33475949112` establishes:

- corrected-weight revision: `fe7563292bb52ab6c235fc3c87157e6a14017479`;
- current `main` revision at capture: `a3c224bdd97ed6de15baef3524eb590c480e0d78`;
- public, ungated repository;
- declared model-card license: `cc-by-nc-sa-4.0`;
- four safetensor shard LFS SHA-256 identities;
- the model/config/tokenizer payload entries are identical between the two observations;
- `README.md` is the only sibling whose blob identity/size differs between these captured revisions.

Therefore this proof case demonstrates a critical identity rule:

> **source revision drift is not automatically payload drift.**

Foundry must preserve repository/source revision separately from behaviorally relevant file/payload identity and derive drift classes from the actual changed evidence.

The four captured weight shard SHA-256 values are frozen by offline tests.

### Civitai — live identity plus disappearance evidence

The existing TrueNAS acquisition script referenced multiple numeric Civitai model versions. The first selected proof dependency, version `131508`, now returns HTTP `404` from the documented model-version API. That state is preserved in `model-version-131508.status.json` rather than erased or replaced.

A second dependency from the same real acquisition script, version `128713`, remains resolvable and is the positive file-identity fixture. Reviewed capture evidence establishes:

- model version `128713`;
- model ID `4384`;
- provider model name `DreamShaper`, version name `8`;
- AIR `urn:air:sd1:checkpoint:civitai:4384@128713`;
- primary file `dreamshaper_8.safetensors`;
- SafeTensor / fp16 / pruned representation;
- SHA-256 `879DB523C30D3B9017143D56705015E15A2CB5628762C11D086FED9538ABD7FD`;
- published status and successful provider pickle/virus scan results at the recorded observation.

The old TrueNAS script had version `128713` stored under a filename suggesting a different model. Foundry therefore treats the provider version/file identity as authoritative evidence and treats project/local filenames as locators or local labels, not canonical model identity.

### Hosted provider — pending real selection

The intended proof source is OpenRouter, but the current delegation-ledger experiment only records a future choice between an `openrouter-pinned` backend and Cloudflare Workers AI; it does not yet pin an exact OpenRouter model.

Do not choose an arbitrary hosted model merely to make the fixture matrix look complete. Once a real experiment or consumer selects an exact OpenRouter model ID, capture the single provider model record. Hosted model ID/canonical slug is provider identity, not cryptographic identity for hidden model weights.

## Public capture workflow

`.github/workflows/issue-12-provider-fixture-capture.yml` uses unprivileged public GitHub-hosted execution with `contents: read`, no provider secrets, and third-party Actions pinned by exact commit SHA. It:

1. validates committed fixtures offline;
2. captures HF `main` and the exact corrected-weight revision;
3. records the current HTTP state of legacy Civitai version `131508`;
4. captures live Civitai version `128713`;
5. validates the resulting working set;
6. uploads the JSON directory only as a short-lived review artifact.

The workflow does not commit or promote captured evidence. Promotion remains a deliberate review action.

## Offline verification

```bash
python -m unittest discover -s tests -p 'test_provider_fixtures.py' -v
python tools/validate_provider_fixtures.py
```

The tests pin the meaningful evidence above and require no network access.
