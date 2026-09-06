# Current Task — Gated Artifact Local Acquisition

**Issue:** #51  
**Branch:** `gated-artifacts/local-acquisition`  
**State:** ACTIVE-NO-HIL  
**Prior compatibility-v2 merge:** `c3a5e12f74daf529545ed94f98f625c6f600652a`

## Purpose

Support gated/user-accepted upstream artifacts without weakening the Foundry public redistribution boundary.

## In scope

- separate public-safe gated-source declaration;
- fail-closed policy that disables public harvest, redistribution and package publication;
- offline adoption of already-authorized local bytes;
- deterministic `content-manifest` SHA-256 identity over exact upstream revision and sorted per-file hashes;
- no serialization of local absolute paths or provider credentials;
- compatibility identity-kind discriminator (`oci` vs `content-manifest`) with legacy records defaulting to `oci`;
- public example based on the documented gated access requirements of `pyannote/speaker-diarization-3.1` and its `pyannote/segmentation-3.0` dependency.

## Boundary

The public Foundry does not authenticate to gated providers, accept terms for a user, hold provider tokens, download gated bytes, or publish them.

The consumer independently satisfies upstream requirements and downloads the exact artifact. Foundry tooling begins only after the bytes are local.

## Acceptance

CI must prove:
1. a gated declaration validates only under the gated contract and does not satisfy the normal public-harvest source declaration;
2. local adoption is deterministic and independent of the source directory path;
3. content or exact-revision changes change identity;
4. symlinks are rejected;
5. output records contain no local absolute source path and disable public publication;
6. legacy OCI compatibility overlays cannot be confused with `content-manifest` identities;
7. public gated metadata passes the existing privacy lint.

## Non-goals

No token management, login flow, automatic terms acceptance, browser automation, gated byte publication, private repackaging, host inventory, environment solver, model conversion, or product qualification.
