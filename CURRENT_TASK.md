# Current Task — Identity-first Model Foundry MVP

**Current implementation target:** issue #12  
**Parent identity MVP:** #9  
**Post-identity vertical slice:** #18  
**First-consumer contract:** #19  
**State:** active / bounded

## Current objective

Finish only the metadata-only provider fixture increment required to establish exact/strongest-available model identity without downloading model weights.

Issue #12 is the current implementation target. The immediate proof classes are:

1. Hugging Face exact repository revision + file/Git/LFS metadata for `vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315`;
2. one Civitai numeric model-version fixture with file identity/hash metadata;
3. sanitized Ollama `/api/tags` + `/api/show` metadata fixture, with no pull/download;
4. one hosted-provider observable model/version identity fixture that does not falsely claim a content digest.

Use fixtures/capture scripts and offline tests only as required by #12. Do not implement the full normalized schema, drift engine, scheduler, database, UI, broad catalog crawling, or model artifact storage in this increment.

## Architecture context

The earlier Faster-Whisper/OCI PoC succeeded and remains useful evidence for exact revision binding, digest/hash verification, R4 hydration, content-addressed rollback and offline consumption. It is **not** the current product boundary.

The current direction is a private-first model parts/placement system with shared public mechanics:

`capability + target/envelope -> deterministic known solution | UNKNOWN -> bounded Generator–Validator exploration -> provider-native acquisition -> project validator -> qualification receipt -> retained knowledge`

Governing principle:

> **Deterministic machinery owns what we know. Generator–Validator works the frontier of what we don't yet know. Successful work at that frontier should move the boundary outward.**

## Provider-native ownership rule

Never duplicate an artifact merely to bring it under Foundry control.

Prefer:

1. verified existing provider-native/local representation;
2. exact provider-native acquisition/cache/store;
3. alternate/mirrored/OCI representation only when availability, transformation, isolation, deployment, or rights/policy justify it.

OCI registry digest is authoritative for an OCI artifact representation, but OCI is not the universal identity for every model artifact.

## Critical-path after #12

Do not serialize the whole observatory roadmap ahead of the first consumer. After the minimum identity semantics are sufficient for the first slice:

1. complete the minimum identity resolver needed by #9;
2. support the `desktop-ui-cv` first-consumer contract from #19;
3. provide exact Hugging Face revision resolution and provider-native HF materialization for KV-Ground;
4. let `desktop-ui-cv` consume a verified local/native handle and run its own quality/performance validator;
5. retain a qualification receipt;
6. prove an equivalent request resolves deterministically without repeated Generator–Validator research;
7. change one material target/envelope variable and require a known alternate or explicit `UNKNOWN`;
8. make a GO / NARROW / KILL decision before broadening providers, consumers, UI, statistics, scheduling, or catalog ingestion.

## Scope stop

Do not restart the old BHADA-local artifact warehouse direction. BHADA is a later, stronger falsification consumer after `desktop-ui-cv` proves the first interface slice.

Do not implement future model publishing (#20) as part of the consumer-side MVP.

Any work outside the current issue must be separately bounded and must re-establish value, authority, and verification before mutation.
