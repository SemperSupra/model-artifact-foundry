# Future model producer/publisher architecture

Status: deferred architecture note. Not on the current consumer-side MVP critical path.

## Decision

Some portfolio projects create or fine-tune models. Those models may eventually need controlled publication to public, gated/private, OCI-compatible, or provider-native venues.

This is a **producer/publisher plane**, distinct from the current consumer-side model selection/acquisition MVP.

Current consumer flow:

`project requirement -> select/qualify model -> acquire/materialize -> consume`

Future producer flow:

`project-created model -> project qualification -> release candidate -> policy/rights/release gates -> publish to approved venue -> read-back verify exact published identity -> register provenance/location`

## Authority boundary

Producing projects remain authoritative for:

- training/fine-tuning code and dataset lineage;
- project/model-specific quality acceptance;
- release intent and version semantics;
- model-card/domain documentation;
- owner/legal judgments that cannot be derived mechanically.

Shared publisher machinery may later own:

- exact release-candidate identity and payload-set hashing;
- transformation lineage for conversion/quantization/packaging;
- deterministic validation gates;
- credential-isolated venue adapters;
- idempotent publish/read-back verification;
- immutable publication receipts and external location registration;
- publication lifecycle state.

Foundry should not become a universal model host merely because it can publish. Prefer venue-native ownership and register authoritative destination identities/locations.

## Private/gated distribution

Internally created models may enter the private parts catalog before publication. Publication is a lifecycle property, not a prerequisite for catalog identity or internal qualification.

A future gated/private venue must preserve:

- explicit access policy;
- immutable identity/provenance;
- credential isolation;
- auditability;
- revocation/withdrawal semantics;
- separation between catalog visibility and byte access;
- independent rights/licensing gates;
- protection against publishing private training data, secrets, or internal evaluation/strategy metadata.

Do not preselect the gated-hosting technology until a real model is approaching release.

## Generator–Validator boundary

> **Deterministic machinery owns what we know. Generator–Validator works the frontier of what we don't yet know. Successful work at that frontier should move the boundary outward.**

Release acceptance is predominantly deterministic. Generator assistance may be useful around residual uncertainty, but project validators, policy checks, owner gates, and reproducible evidence control publication.

## Way of Work

Future publishing follows `Observe/Discover -> Plan -> Act -> Verify` and R4.

Publishing is an external mutation. The preferred sequence is:

1. observe the exact candidate and venue requirements;
2. produce a non-mutating publication plan;
3. validate quality, identity, rights/policy, notices, safety/serialization, and sanitization;
4. stop at explicit owner/credential/release authorization;
5. publish to the selected venue;
6. read back from the venue and verify exact identity/content/metadata;
7. retain the publication receipt and rollback/withdrawal information.

## Deferral rule

Do not implement generalized publishing automation, hosting, or gated portals now. Revisit only when one real internally-created model is approaching a release/promotion decision. Use that real model as the bounded vertical slice and red-team the selected venue before external mutation.

Tracking: public issue #20; private operational/control counterpart `SemperSupra/model-artifact-foundry-private#9`.
