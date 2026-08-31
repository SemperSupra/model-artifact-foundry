# Model Artifact Foundry

Public execution and distribution plane for curated, versioned third-party ML models, checkpoints, and other large replaceable artifacts.

The Foundry does not exist to mirror arbitrary public bytes. Its public contract is to make eligible third-party artifacts reproducible and inspectable through exact upstream identity, license/provenance evidence, family-specific validation, immutable OCI identity, reviewed promotion, and digest-pinned consumer hydration.

## Core model

```text
upstream source
   -> metadata discovery
   -> exact-revision candidate
   -> bounded public validation
   -> OCI candidate identity
   -> reviewed approved catalog
   -> consumer selects exact digest
   -> durable verified hydration
```

Discovery, candidate production, validation, approval, consumer selection, and hydration are separate states. A newly discovered upstream revision must never silently replace an approved consumer digest.

## Start here

- `AGENTS.md` — contributor/agent authority and safety contract.
- `CURRENT_TASK.md` — current bounded increment.
- `docs/architecture/artifact-lifecycle.md` — state machine, identity model, independent versioning, and storage boundary.
- `docs/security/public-execution-boundary.md` — public CI, credential, upstream-content, and claim boundaries.
- `docs/contracts/hydration.md` — generic digest-pinned durable hydration contract.
- `docs/plans/increment-0.md` — initial contract-bootstrap plan and follow-on increments.
- `schemas/source-declaration.schema.json` — allowlisted source declaration contract.
- `schemas/candidate-manifest.schema.json` — exact-revision candidate evidence contract.
- `schemas/approved-catalog.schema.json` — immutable approved digest mapping contract.
- `examples/sources/faster-whisper-tiny.json` — non-executable first-family declaration example.

## Repository boundary

This repository is intentionally public and independently operable. Public workflows must not require credentials capable of reading private repositories. Publicly downloadable does not imply redistributable or trusted; missing or ambiguous license/provenance state fails closed.

Large model/checkpoint bytes do not belong in Git or normal consumer runtime images. Later increments will distribute eligible curated bytes as generic OCI artifacts and hydrate them into durable content-addressed consumer storage by immutable digest.

## Current status

Increment 0 defines contracts only. There is currently no harvesting workflow, no model/checkpoint download, no approved catalog entry, and no GHCR artifact publication authorized by this baseline.

> Bootstrap note: this repository was created empty. The initial `main` commit exists only to initialize the repository; substantive contracts and implementation are introduced through reviewed branches and pull requests.
