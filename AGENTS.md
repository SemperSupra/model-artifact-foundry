# Agent Operating Contract

This repository is the public execution/distribution plane for the Model Artifact Foundry.

## Source-of-truth order

1. current GitHub repository/branch/issue/PR state;
2. this file and `CURRENT_TASK.md`;
3. repository architecture/contracts/schemas;
4. public upstream evidence tied to exact revisions;
5. historical notes or chat context.

## Working method

Use bounded `Observe / Discover -> Plan -> Act -> Verify` increments. Preserve reproducibility, repeatability, reversibility, and idempotence (R4). Record exact repository revisions and OCI/artifact digests whenever evidence refers to a concrete artifact.

## Public-plane invariants

- This repository must be independently usable without credentials that can read private repositories.
- Publicly downloadable material is not automatically redistributable, approved, or trusted.
- Discovery, candidate harvesting, validation, promotion, and consumer selection are distinct states.
- A newly discovered upstream revision must never silently replace an approved digest.
- OCI registry digest is authoritative artifact identity; tags are locators only.
- Model/checkpoint bytes do not belong in Git.
- Generic acquisition must not execute arbitrary upstream scripts, remote code, or unreviewed serialized executable content.
- PR workflows must be unprivileged. Package-writing jobs may run only trusted repository state with least-privilege permissions.
- Do not use `pull_request_target` to execute untrusted checkout content in a privileged context.
- Pin third-party GitHub Actions by full commit SHA when workflows are introduced.

## Authority gates

Do not without explicit applicable authorization:

- promote a candidate to approved when review is required;
- broaden source/license allowlists materially;
- publish or delete immutable approved artifacts;
- introduce privileged/self-hosted harvesting infrastructure;
- change the public/private authority boundary.

## Evidence discipline

Hashing and packaging prove identity, not model quality or safety. Validators must state only the claims they actually establish. Missing or ambiguous license/provenance state fails closed.
