# Current Task — Public Contract Bootstrap / Increment 0

**Issue:** #1  
**Branch:** `bootstrap/public-contracts`  
**State:** READY-FOR-EXPLICIT-MERGE-AUTHORIZATION

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

1. Public repository role is independently understandable. — satisfied
2. Candidate production and approval/promotion are unambiguously separate. — satisfied
3. Schemas fail closed on missing license/provenance/identity fields. — satisfied
4. Approved catalog requires immutable OCI digest identity. — satisfied
5. Hydration contract is stage -> verify -> atomic promote and is R4 by design. — satisfied
6. Security contract prohibits privileged execution of untrusted PR code and private-read credentials. — satisfied
7. Example declaration contains metadata only and no model bytes. — satisfied
8. No workflow in this increment can harvest or publish artifacts. — satisfied

## Verification evidence

- branch reconciled with current `main`; final pre-ready compare was ahead with 0 commits behind;
- diff contains only Markdown documentation, JSON schemas, and one JSON metadata example;
- no `.github/workflows` files and no binary/model/checkpoint files are introduced;
- all three schemas parse and pass JSON Schema Draft 2020-12 schema validation;
- the Faster Whisper `tiny` example validates against the source-declaration schema;
- negative validation confirms a gated source declaration is rejected by policy schema;
- negative validation confirms the candidate-manifest schema cannot represent state `approved`;
- no GHCR mutation, upstream artifact download, model validation execution, or private-repository read occurred.

Stop at explicit owner merge authorization. No GHCR mutation or model harvesting is authorized by this task.
