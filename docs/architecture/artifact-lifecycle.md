# Artifact Lifecycle and Identity

## Purpose

The Foundry turns volatile third-party artifact references into reviewable, provenance-rich, immutable artifact identities without coupling consumer releases to upstream hosting or mutable names.

## State model

```text
DECLARED
   |
   v
DISCOVERED_REVISION
   |
   v
CANDIDATE_PLANNED
   |
   v
CANDIDATE_HARVESTED
   |
   v
PUBLIC_VALIDATED
   |
   +----> REJECTED / QUARANTINED
   |
   v
PROMOTION_REVIEW
   |
   v
APPROVED
   |
   v
CONSUMER_SELECTED
   |
   v
HYDRATED / VERIFIED
   |
   +----> SUPERSEDED (prior digest retained for rollback)
```

Discovery is not harvesting. Harvesting is not approval. Public validation is not a generic safety or quality certification. Approval is not consumer selection.

## Three identities

1. **Upstream identity** — provider/repository plus an exact upstream revision and file identities/hashes.
2. **Foundry identity** — immutable OCI registry digest for the curated bundle plus its manifest.
3. **Consumer selection** — logical artifact ID plus the exact approved Foundry OCI digest selected by a consumer/deployment.

Mutable tags may improve discoverability but are never authoritative deployment identity.

## Independent versioning

Artifact evolution and consumer software evolution are independent. A consumer release may continue using the same approved artifact digest across multiple software versions. A newly approved artifact digest does not automatically alter any consumer selection.

Compatibility is explicit data, not inferred from matching version numbers.

## Promotion invariant

An upstream change may automatically produce a discovery observation and, for allowlisted cases, a candidate. It must never silently mutate the approved catalog entry used by consumers.

## Storage boundary

- Git stores declarations, schemas, catalogs, validator code, and small evidence.
- Temporary CI workspace may stage candidate bytes.
- Large model/checkpoint bytes are distributed as OCI artifacts, not committed to Git.
- Consumer deployments hydrate immutable approved artifacts into durable content-addressed local storage.

## Initial family

The first planned family is Faster Whisper CTranslate2 model data. The public bootstrap defines only contracts and example metadata; model acquisition and publication occur in later reviewed increments.
