# Agent Operating Contract

This repository is the public/shared mechanics and evidence plane for the Model Artifact Foundry. It is not a universal model warehouse and it is not the authority for private project selection policy, credentials, target inventory, or private qualification conclusions.

## Source-of-truth order

1. current GitHub repository/branch/issue/PR state;
2. this file and `CURRENT_TASK.md`;
3. current architecture/contracts/schemas and governing issues;
4. public upstream evidence tied to exact revisions/identities;
5. historical PoC material, notes, or chat context.

Historical Faster-Whisper/OCI work is a mechanism/specification donor. Do not assume its artifact-mirroring architecture is the current product direction.

## Working method

Use bounded `Observe / Discover -> Plan -> Act -> Verify` increments. Preserve reproducibility, repeatability, reversibility, and idempotence (R4). Record exact repository revisions and the strongest artifact/provider identity supported by the evidence.

> **Deterministic machinery owns what we know. Generator–Validator works the frontier of what we don't yet know. Successful work at that frontier should move the boundary outward.**

Known in-envelope requests should resolve deterministically from retained evidence. Generator–Validator exploration is permitted only for explicit residual uncertainty such as a new capability, target, envelope, representation, provider state, or insufficient/conflicting evidence.

## Current architecture invariants

- The catalog/control plane records identity, provenance, locations, qualification evidence, lifecycle and approved/alternate state; it is not the warehouse.
- Prefer provider-native ownership and caches/stores. Do not duplicate an artifact merely to bring it under Foundry management.
- OCI/ORAS is an optional representation/distribution mechanism where justified, not the universal artifact identity or storage contract.
- Identity strength is provider/evidence-specific: prefer content digest when available; otherwise immutable repository commit/provider version as applicable. Mutable aliases and hosted model names must not be represented as cryptographic artifact identity.
- Selection output is a complete tuple where applicable: model + exact artifact/representation + runtime/backend + placement target + acquisition/materialization plan.
- A model that downloads or loads is not automatically qualified. Qualification binds exact artifact/representation/runtime/toolchain/target/workload to measured evidence.
- `UNKNOWN` is a valid and important result. Do not weaken constraints or validators to force a selection.
- Project-specific quality validators remain in consuming projects; Foundry records/references their evidence rather than absorbing their domain semantics.
- Provider credentials belong at the acquisition boundary and must not be exposed to consuming applications or committed to Git.
- Model/checkpoint bytes do not belong in Git.
- Generic acquisition must not execute arbitrary upstream scripts, remote code, or unreviewed serialized executable content merely to discover or materialize a model.

## Public/private boundary

Public code may contain reusable schemas, provider adapters, sanitization rules, benchmark adapters and deliberately public/sanitized receipts. Private project requirements, target topology, gated access state, selection/rejection history, approval mappings, credentials, strategic heuristics and sensitive qualification evidence stay in the private control plane by default.

Publicly downloadable material is not automatically redistributable, approved, or trusted. Technical ability to copy/publish never substitutes for rights/policy adjudication.

## Authority gates

Do not without explicit applicable authorization:

- publish, mirror, promote, withdraw, or delete model artifacts;
- broaden source/license/redistribution policy materially;
- expose credentials, private target inventory, or private evaluation knowledge;
- create a new hosting service, scheduler, global catalog crawler, community benchmark service, or statistical prediction platform;
- change the public/private authority boundary.

## Evidence discipline

State only what the evidence proves. Distinguish static/fixture verification, provider observation, native acquisition verification, runtime smoke, performance measurement, project-quality qualification, and production validation. Missing or ambiguous identity, rights, provenance, or qualification state fails closed rather than being silently inferred.
