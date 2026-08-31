# Current Task — Faster Whisper Tiny Foundry Proof of Concept

**Issue:** #3  
**State:** COMPLETE  
**Operationally tested head:** `46dc566f59a8ab28a5a00c1eeaa2e6ef132c014b`  
**Purpose:** prove one complete Foundry supply path for BHADA, then stop platform expansion.

## Result

The proof succeeded end to end for logical artifact `asr/faster-whisper/tiny`.

Approved identity:

- upstream: `Systran/faster-whisper-tiny`
- exact upstream revision: `d90ca5fe260221311c53c58e660288d3deb8d356`
- OCI repository: `ghcr.io/sempersupra/model-artifact-foundry`
- approved digest: `sha256:f2d664ae986b0b0598037a9f0b929fd0b0b748871474a06c84658c1f2a1a4b42`
- candidate evidence commit: `4a82c5d72dd3fef6bef3dccdace23a5c1859636c`
- model archive SHA-256: `9e578a3dc8d8ac2178a4e986a8f02e488c94bf814dd7ba51701591a76093c829`
- validated runtime: `faster-whisper==1.2.1`, `ctranslate2==4.6.0`

## Evidence

- publication run `33438050007`: exact-revision acquisition, local-only JFK transcription, GHCR login and candidate publication passed; initial pull verifier exposed only the ORAS-preserved `dist/` path observation;
- recovery run `33438464760`: pulled the existing immutable digest without republishing, verified bundle/archive/per-file hashes, and produced schema-valid canonical candidate evidence;
- approved-consumer run `33438707454`: catalog validation, fresh digest-pinned hydration, second hydration with ORAS replaced by `/bin/false`, and local-only Faster Whisper JFK transcription all passed.

The operational test at `46dc566f59a8ab28a5a00c1eeaa2e6ef132c014b` produced the model directory:

`/tmp/foundry-cache/blobs/sha256-f2d664ae986b0b0598037a9f0b929fd0b0b748871474a06c84658c1f2a1a4b42/model`

For BHADA, the equivalent durable root is `/cache/models/asr`.

## R4 proof

- **Reproducible:** source revision, per-file hashes, OCI digest, evidence commit and validator versions are fixed.
- **Repeatable:** the approved digest hydrated successfully from a fresh cache.
- **Reversible:** the content-addressed layout retains digest-specific blobs; selection is separate from bytes.
- **Idempotent:** a second hydration succeeded while the ORAS executable was deliberately `/bin/false`, proving no registry access was required for an intact cached digest.

## Scope stop

The Foundry proof is complete. Do not continue scheduled discovery, additional models, second-consumer work, generalized harvesting, or large-model infrastructure as part of the BHADA MVP effort.

BHADA #88 now has a usable artifact/catalog/hydrator contract. Return current engineering effort to BHADA's stabilization/release critical path; any further Foundry work belongs in a separate session and must re-establish value/scope before expansion.

Any commits after the operationally tested head above are documentation/control-plane closeout only unless separately revalidated.
