# Compatibility v2 Public Contract

## Purpose

Record portable, public-safe compatibility facts for an exact Foundry artifact representation without turning the Foundry into a host registry, scheduler, product qualification service, or environment solver.

## Boundary

The public Foundry may know:
- immutable artifact digest and upstream provenance;
- representation identity (format, precision/quantization, derivation);
- generic platform/architecture/backend/runtime constraints;
- upstream-declared compatibility;
- compatibility validated with public-safe evidence.

The public Foundry must not require or encourage:
- hostnames, usernames, IP addresses, local DNS names;
- mount points/local filesystem paths;
- GPU UUIDs, serials, PCI topology;
- private repository/corpus identifiers;
- arbitrary environment dumps;
- local machine inventory.

Private environment-specific evidence belongs in `SemperSupra/model-artifact-foundry-private`. Product fitness belongs in the consuming product repository.

## Identity

A conceptual/upstream model and an executable artifact representation are separate identities.

Normal redistributable representations use an immutable OCI digest. Gated/local-only representations that cannot enter the public distribution path may instead use a deterministic `content-manifest` SHA-256 identity produced by the gated local-acquisition contract.

`artifact_identity_kind` distinguishes these namespaces:
- `oci` — normal registry-distributed Foundry artifact;
- `content-manifest` — local-only content identity over exact upstream revision plus sorted per-file hashes.

For backward compatibility, compatibility records that predate this discriminator and omit `artifact_identity_kind` are interpreted as `oci`.

Example:

```text
model: vision/siglip2/base
  -> pytorch-safetensors-fp16 : OCI digest A
  -> onnx-fp16                : OCI digest B
  -> mlx-q8                   : OCI digest C

model: gated/example
  -> locally acquired exact revision : content-manifest digest D
```

Conversion provenance links a derived representation to its parent digest where applicable.

## Claim states

Public records use:
- `declared`: upstream/public metadata supports the generic compatibility claim.
- `publicly-validated`: exact artifact representation was exercised under public-safe validation evidence.

Local/private matching may additionally report:
- `privately-validated`: a matching private overlay record exists and passed;
- `unqualified`: constraints do not establish incompatibility, but sufficient evidence is absent;
- `incompatible`: deterministic required constraints conflict or private validation positively failed.

`unqualified` must never be treated as `incompatible`.

`product-qualified` is intentionally outside this contract and belongs to a product authority.

## Environment profiles

An environment profile describes capabilities, not machine identity. It is an input to matching and may remain ephemeral/private.

The public schema permits generic fields such as OS family, architecture, accelerator backend/vendor, runtime family, versions and coarse model class/memory where a private caller chooses to include them. It contains no hostname or network identity field.

## Matching

The deterministic matcher:
1. checks artifact identity kind before applying private evidence;
2. checks hard platform/backend/runtime-family constraints;
3. evaluates only simple version constraints it can interpret conservatively;
4. returns `unqualified` when information is missing or a constraint cannot be safely decided;
5. prefers matching passed private evidence over public/declarative evidence when an optional private overlay is supplied locally;
6. never selects a host or launches a workload.

A legacy private overlay with no identity-kind field means `oci`; it cannot upgrade a `content-manifest` artifact.

## Private evidence projection

Private validation does not automatically create a public compatibility claim. A public projection is a separate reviewed record containing only generic facts worth exposing. Detailed local evidence remains private.

## Privacy lint

Candidate/evidence metadata intended for public commit/publication should pass `tools/public_metadata_lint.py`. The lint is defense in depth, not the primary privacy boundary. It checks only supplied files and does not scan or inventory hosts.

## Backward compatibility

Schema v1 and the existing Faster Whisper Tiny approved digest remain authoritative and unchanged. Compatibility v2 is additive. Existing consumers need not migrate until they need compatibility-aware selection.
