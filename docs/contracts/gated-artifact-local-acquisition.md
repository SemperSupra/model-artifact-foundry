# Gated Artifact Local Acquisition Contract

## Purpose

Retain Foundry identity, provenance, compatibility, and rollback value for upstream artifacts whose files require user authentication, terms acceptance, contact sharing, or another access gate, without using the public Foundry to bypass that gate or redistribute the gated bytes.

## Governing boundary

A gated artifact is not eligible for the normal public harvest -> OCI/GHCR publication path by default.

The public Foundry may record public-safe facts about the source and its access requirements. The consumer is responsible for satisfying upstream access requirements and obtaining the files directly from the upstream provider using credentials that remain outside Foundry tooling.

Foundry tooling may then adopt an already-downloaded local directory and create a deterministic content-manifest identity from:

- logical artifact ID;
- upstream provider and repository;
- exact upstream revision supplied by the consumer;
- relative file paths;
- file sizes;
- SHA-256 hashes.

Local absolute paths, usernames, hostnames, provider tokens, account identity, acceptance-form contents, and credential state are not serialized.

## Lifecycle

```text
GATED_SOURCE_DECLARED
        |
        | consumer independently satisfies upstream gate
        v
LOCAL_BYTES_ACQUIRED
        |
        | offline Foundry adoption
        v
LOCAL_CONTENT_VERIFIED
        |
        +--> private compatibility evaluation
        |
        +--> consumer selection/cache
```

This lifecycle does not produce an approved public OCI artifact.

## Identity

For normal redistributable Foundry artifacts, the OCI registry digest remains the authoritative Foundry artifact identity.

For gated local-only artifacts, the identity is a `content-manifest` SHA-256 digest over canonical JSON containing the exact upstream identity and the sorted per-file content identities. The digest does not contain a local filesystem path or timestamp.

The content-manifest identity proves which bytes were adopted. It does not prove the user's right to access them, quality, safety, compatibility, or product fitness.

## Access claims

The public gated-source declaration may state only public facts such as:

- provider/repository;
- access mode;
- whether an account, terms acceptance, or token is required;
- publicly documented dependent access requirements;
- publicly observed license metadata;
- the fact that Foundry public redistribution is disabled.

It must not claim that any particular user has accepted terms or has access.

## Local adoption

`tools/adopt_local_artifact.py` is intentionally offline. It:

1. loads a gated-source declaration;
2. requires an exact upstream revision supplied by the caller;
3. recursively enumerates regular files under a caller-supplied directory;
4. rejects symlinks and non-regular files;
5. hashes content and builds a sorted canonical manifest;
6. computes a deterministic content-manifest SHA-256 identity;
7. writes a path-free local acquisition record.

It never downloads files and never accepts provider credentials.

## Compatibility

A private compatibility record may key evidence to the resulting SHA-256 content identity. Product qualification remains product-owned. A locally verified artifact is not automatically compatible or product-qualified.

## Redistribution

Default policy for this path is fail-closed:

- public harvest: disabled;
- public OCI publication: disabled;
- public byte redistribution: disabled;
- private repackaging/redistribution: not implied or authorized.

A future decision to redistribute a gated artifact requires a separate explicit licensing/access review and a separately authorized path. It must not be inferred solely from an open-source license label.

## Non-goals

This increment does not implement:

- provider login or token management;
- automatic acceptance of terms;
- browser automation;
- credential storage;
- host inventory;
- public or private artifact republishing;
- generic license interpretation;
- automatic artifact conversion;
- product qualification.
