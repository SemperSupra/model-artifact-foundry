# Current Task — Gated Artifact Local Acquisition

**Issue:** #51  
**State:** COMPLETE  
**Merged PR:** #52  
**Merge commit:** `c3a78b4c7b6293603c09e008882ebae5c8e31e6f`  
**Prior compatibility-v2 merge:** `c3a5e12f74daf529545ed94f98f625c6f600652a`

## Result

The Foundry now supports gated/user-accepted upstream artifacts without weakening the public redistribution boundary.

Delivered:

- separate public-safe gated-source declaration;
- fail-closed policy disabling public harvest, redistribution and package publication;
- offline adoption of already-authorized local bytes;
- deterministic `content-manifest` SHA-256 identity over exact upstream revision and sorted per-file hashes;
- path-free local acquisition records with no provider credentials or user acceptance state;
- compatibility identity-kind discriminator (`oci` vs `content-manifest`) with legacy records defaulting to `oci`;
- matcher protection preventing legacy OCI private evidence from upgrading a content-manifest artifact;
- public example based only on documented gated access requirements for `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0`.

## Verification

- PR gated-artifact contract CI passed.
- Compatibility-v2 regression CI passed.
- Faster Whisper PoC regression passed on the PR.
- Post-merge gated-artifact run `34057088900` passed.
- Post-merge compatibility-v2 run `34057088936` passed.

## Boundary retained

The public Foundry does not authenticate to gated providers, accept terms for a user, hold provider tokens, download gated bytes, or publish them.

No token management, login flow, automatic terms acceptance, browser automation, gated byte publication, private repackaging, host inventory, environment solver, model conversion, HIL compatibility claim, or product qualification was introduced.

Future gated-model use begins with a consumer independently satisfying upstream access requirements and downloading an exact revision; Foundry tooling begins only after those bytes are local.
