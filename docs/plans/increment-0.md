# Increment 0 — Public Contract Bootstrap

## Goal

Establish the public contracts required to build a safe artifact Foundry before any workflow can download or publish model/checkpoint bytes.

## Deliverables

- repository operating contract;
- artifact lifecycle/identity model;
- source declaration schema;
- candidate manifest schema;
- approved catalog schema;
- digest-pinned hydration contract;
- public execution security boundary;
- one non-executable Faster Whisper `tiny` source declaration example.

## Explicit non-deliverables

This increment does not contain:

- scheduled or manual discovery workflows;
- artifact downloader/harvester code;
- model validation execution;
- OCI packaging or GHCR publication;
- package-write permissions;
- an approved catalog entry;
- model/checkpoint bytes.

## Verification

Before merge:

1. review the complete diff for private/sensitive content;
2. validate all JSON files parse successfully;
3. validate example declarations against the source-declaration schema;
4. confirm no `.github/workflows` package/discovery/harvest implementation is introduced;
5. confirm no binary/model/checkpoint files are introduced;
6. confirm source/license uncertainty is fail-closed;
7. confirm candidate state cannot be represented as approved by the candidate schema;
8. confirm approved catalog requires exact `sha256:` OCI digest identity;
9. confirm the public repository contract requires no private-read credential;
10. stop at explicit owner merge authorization.

## Next increments after merge

### Increment 1 — metadata-only discovery

Implement discovery for one allowlisted source. It must resolve upstream metadata/revision/license/gating/size without downloading unchanged model bytes. No candidate publication yet.

### Increment 2 — candidate harvest/validation

Acquire one exact revision, inventory/hash it, validate only the documented family claims, package it as a candidate OCI artifact, publish/pull-back by digest, and preserve promotion separation.

### Increment 3 — reviewed promotion/catalog

Promote a proven candidate through a reviewed catalog change. Upstream changes must not alter the approved digest automatically.

### Increment 4 — generic hydrator

Implement digest-pinned stage/verify/atomic-promote behavior into durable content-addressed storage.

### Increment 5 — first consumer proof

Use the generic contract from an actual consumer while keeping consumer-specific orchestration outside the Foundry.
