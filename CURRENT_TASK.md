# Current Task — Public Contract Bootstrap / Increment 0

**Issue:** #1  
**Branch:** `bootstrap/public-contracts`  
**State:** ACTIVE

## Objective

Establish the first reviewed public contract baseline without harvesting, downloading, or publishing model/checkpoint artifacts.

## In scope

- repository role and non-goals;
- OPAV/R4 contributor/agent contract;
- artifact lifecycle and identity semantics;
- draft machine-readable schemas for source declarations, candidate manifests, and approved catalog entries;
- generic digest-pinned hydration contract;
- public GitHub Actions security/authority boundary for later increments;
- non-executable Faster Whisper `tiny` source-declaration example;
- Increment 0 documentation and evidence.

## Out of scope

- discovery workflow execution;
- model/checkpoint downloads;
- GHCR/OCI publication;
- package-write permissions;
- model validation execution;
- catalog promotion;
- consumer integration changes;
- private repository access.

## Acceptance

1. Public repository role is independently understandable.
2. Candidate production and approval/promotion are unambiguously separate.
3. Schemas fail closed on missing license/provenance/identity fields.
4. Approved catalog requires immutable OCI digest identity.
5. Hydration contract is stage -> verify -> atomic promote and is R4 by design.
6. Security contract prohibits privileged execution of untrusted PR code and private-read credentials.
7. Example declaration contains metadata only and no model bytes.
8. No workflow in this increment can harvest or publish artifacts.

Stop at `READY-FOR-EXPLICIT-MERGE-AUTHORIZATION`. No GHCR mutation or model harvesting is authorized by this task.
