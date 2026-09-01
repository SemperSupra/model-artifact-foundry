# Metadata-only provider fixtures

This directory supports issue #12: capture enough provider evidence to classify identity strength **without downloading model/checkpoint bytes**.

## Boundary

Fixtures are evidence samples, not a mirrored model catalog. They must not contain credentials, cookies, private endpoints, unrelated local inventory, or model/checkpoint/archive bytes.

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
  --output fixtures/raw/civitai/model-version-131508.json \
  civitai \
  --version-id 131508

python tools/capture_provider_metadata.py \
  --output fixtures/raw/openrouter/<model-id>.json \
  openrouter \
  --model-id <exact-openrouter-model-id>
```

Do not substitute an invented/synthetic response when a provider cannot be reached. Record the missing evidence and capture it later from an authorized network path.

## Current evidence state

### Ollama

`fixtures/raw/ollama/kv-ground-8b.tags.json` is a deliberately narrow sanitized projection from an authorized local inventory snapshot. It preserves only one installed model's provider-native digest and representation metadata. Hostname, endpoint, unrelated inventory, local filesystem details, and credentials are excluded.

A genuine sanitized `/api/show` response is still required before the Ollama proof case is complete. Do not fabricate it from `/api/tags` fields.

### Hugging Face KV-Ground

The capture target is `vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315`. The important identity distinction is:

- the weight correction was committed at `fe7563292bb52ab6c235fc3c87157e6a14017479`;
- the repository `main` alias later advanced to README-only commit `a3c224bdd97ed6de15baef3524eb590c480e0d78`, whose parent is the weight-correction commit.

This is a concrete reason to preserve **source revision** separately from **payload/file identities**. Alias/repository movement must not automatically be interpreted as payload drift. The raw HF API fixture with file metadata is still required so that determination can be made mechanically rather than from UI observations.

### Civitai

The chosen existing dependency is numeric model-version `131508`, already used by the authorized TrueNAS Stable Diffusion acquisition script. Capture the public version response; do not download the checkpoint.

### Hosted provider

Use OpenRouter's public model-list response for one exact, deliberately selected model identity. A hosted model ID/canonical slug is provider identity, not cryptographic identity for hidden model weights.

## Offline verification

```bash
python -m unittest discover -s tests -p 'test_provider_fixtures.py' -v
python tools/validate_provider_fixtures.py
```

These checks require no network access.
