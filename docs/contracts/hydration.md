# Digest-Pinned Hydration Contract

## Goal

Give consumers a generic way to materialize an approved OCI artifact into durable local storage without embedding model/checkpoint bytes or harvesting tooling in the consumer runtime image.

## Required operation

```text
plan
  -> resolve exact approved OCI digest
  -> inspect local content-addressed cache
  -> pull into staging only when absent
  -> verify OCI digest
  -> verify bundle manifest/schema
  -> verify expected logical artifact ID and artifact family
  -> verify every declared file hash/size
  -> atomically promote to durable content-addressed location
  -> update/select logical pointer only after verification
```

## Invariants

- Input identity is an exact OCI `sha256:` digest, not `latest` or another mutable tag.
- Existing verified content for the requested digest makes hydration a no-op.
- Verification failure leaves the previously selected artifact untouched.
- Multiple approved/superseded digests may coexist to support rollback.
- Runtime consumers see an ordinary local filesystem directory.
- ORAS/registry acquisition tooling should normally remain host-side or in a one-shot init/fetcher image, not the application runtime.
- Runtime network/model auto-download can be disabled when a prehydrated artifact is required.

## Suggested durable layout

```text
<cache-root>/
  blobs/<foundry-digest>/...
  manifests/<logical-id>/<foundry-digest>.json
  selected/<logical-id> -> ../../blobs/<foundry-digest>/
```

The exact filesystem mechanism may differ across platforms; content-addressed coexistence, verification-before-selection, and rollback are the invariants.

## R4

- **Reproducible:** logical ID + exact OCI digest + manifest define the bytes.
- **Repeatable:** hydration can rerun against the same durable cache.
- **Reversible:** previous verified digest remains selectable.
- **Idempotent:** an already verified selected digest causes no material mutation or download.

## Consumer responsibility

The Foundry does not become the runtime orchestrator. Consumers decide which approved digest to select, where durable storage lives, how to pass the local directory to their backend, and what product-specific behavior occurs when the artifact is absent or incompatible.
