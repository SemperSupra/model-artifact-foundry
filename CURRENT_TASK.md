# Current Task — Faster Whisper Tiny Foundry Proof of Concept

**Issue:** #3  
**Branch:** `poc/faster-whisper-tiny`  
**State:** ACTIVE  
**Purpose:** prove one complete Foundry supply path for BHADA, then stop platform expansion.

## Objective

Produce one known-good Faster Whisper `tiny` artifact from exact upstream revision `d90ca5fe260221311c53c58e660288d3deb8d356`, publish it as a generic OCI artifact in GHCR from trusted public GitHub Actions, record immutable candidate evidence, promote one reviewed catalog mapping, and provide a generic digest-pinned hydrator suitable for BHADA's durable `/cache/models/asr` boundary.

## In scope

- exact-revision acquisition from `Systran/faster-whisper-tiny`;
- fail-closed upstream metadata/license/gating checks;
- expected-file inventory and SHA-256 manifest;
- local-only Faster Whisper load/transcription smoke using a pinned public JFK fixture;
- deterministic model archive + manifest/notice as generic OCI layers;
- trusted-main GHCR candidate publication and pull-back verification;
- immutable candidate evidence committed to a review branch;
- one approved catalog entry after evidence review;
- generic ORAS-based hydrator with stage -> verify -> atomic promote behavior;
- BHADA handoff documentation with logical ID, digest, cache layout and invocation.

## Out of scope

- scheduled discovery or automatic update harvesting;
- additional model sizes/families;
- second consumers;
- self-hosted runners;
- generic quality benchmarking;
- BHADA product-code changes;
- TrueNAS deployment.

## Gates

PR validation must not publish. Candidate publication may occur only from trusted `main`. Candidate publication is not catalog promotion. Consumers pin an OCI digest, never `latest` or upstream `main`.

## Exit

Stop when a real candidate has been published and pull-back verified, the catalog maps `asr/faster-whisper/tiny` to its immutable digest, the generic hydrator is usable, and BHADA #88 has an exact consumer handoff. At that point return effort to the BHADA MVP critical path.
