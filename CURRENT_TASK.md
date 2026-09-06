# Current Task — Compatibility v2 Public Contract

**Issue:** #49  
**Branch:** `compatibility-v2/public-contract`  
**State:** ACTIVE-NO-HIL  
**Prior operational proof:** Faster Whisper Tiny at `46dc566f59a8ab28a5a00c1eeaa2e6ef132c014b`

## Purpose

Extend the proven artifact identity/hydration mechanism with structured, privacy-safe artifact/runtime compatibility evidence. This is a separately authorized value case after the Faster Whisper/BHADA proof; it is not continuation of generalized harvesting.

## In scope

- additive v2 representation-aware candidate/catalog schemas while preserving v1;
- public-safe compatibility and environment capability schemas;
- deterministic conservative compatibility matcher;
- public metadata privacy leak lint;
- compatibility-v2 description of the existing Faster Whisper artifact without changing its digest;
- prepared SigLIP2 source declaration for a second-consumer experiment.

## Public privacy boundary

Do not require or record local hostnames, usernames, IP/network identity, local paths, device UUIDs/serials, private repository/corpus identity, or raw environment dumps. Public records contain portable generic artifact/runtime facts only.

## Claim boundary

- `declared`: public/upstream statement.
- `publicly-validated`: exact representation exercised with public-safe evidence.
- `unqualified`: insufficient evidence; not incompatibility.
- `incompatible`: deterministic required constraint conflict.

Optional private evidence may be consumed locally by the matcher but is never published/persisted by this public tool. Product fitness remains product-owned.

## C8 regression gate

The approved Faster Whisper identity remains unchanged:
- logical artifact: `asr/faster-whisper/tiny`
- digest: `sha256:f2d664ae986b0b0598037a9f0b929fd0b0b748871474a06c84658c1f2a1a4b42`

Compatibility metadata must not rewrite artifact bytes or invalidate the existing hydration/R4 proof.

## C9 hold

`google/siglip2-base-patch16-224` is preparation only. This task does not authorize harvesting, package publication, approval, or hardware compatibility claims.

## Non-goals

No host registry, scheduler, placement engine, GPU manager, generic environment solver, automatic representation conversion, benchmark storage, product qualification, private evidence publication, or HIL validation.

## Acceptance

CI validates schemas and fixtures, exercises matcher/lint behavior, and asserts the existing Faster Whisper digest remains unchanged. Stop before any local hardware compatibility claim.