# Benchmark artifact Rep 1

Status: experimental proving increment

## Question
Can the Foundry represent benchmark/dataset dependencies needed by Visual Spelunker without pretending all bytes are redistributable OCI artifacts or creating a competing dataset metadata standard?

## Adopt-before-build
Use MLCommons Croissant metadata when an upstream dataset publishes it or when a standards-compliant metadata record can be deterministically derived. The Foundry does not replace Croissant; it adds portfolio-specific immutable selection, promotion, verification, materialization, and dependency semantics.

## Scope
This rep adds only an experimental benchmark source declaration, public fixtures, a dependency-free boundary validator, tests, and public CI. It does not modify existing approved model/checkpoint schemas or catalog entries.

Supported artifact kinds:
- dataset
- benchmark
- benchmark-overlay
- synthetic-generator

Supported component materialization modes:
- mirror
- upstream-hydrate
- manifest-only

A declaration may be `composite` when different components use different modes.

## Core invariant
A component marked `mirror` must have verified redistribution permission. An unresolved or non-redistributable component may still be represented as `upstream-hydrate` or `manifest-only` so that identity/provenance can be pinned without copying bytes into the Foundry.

## Specimens
### Project-owned synthetic contract generator
The first fixture proves a generator can be registered by manifest/reference and can expose sample identity fields for later rendered-byte hashes. This rep intentionally makes no redistribution claim about the project fixture itself.

### Open Images V7
The first external fixture is composite:
- annotations are represented as mirror-eligible because the upstream project licenses annotations under CC BY 4.0;
- image pixels remain upstream-hydrated because Open Images explicitly advises users to verify each image's license status even though images are listed as CC BY 2.0.

This fixture proves that dataset-level licensing cannot be collapsed into one bundle-wide boolean.

## Croissant boundary
The optional `croissant` reference is reserved for an actual Croissant metadata record. A generic dataset webpage must not be mislabeled as Croissant metadata. Croissant parsing/validation is deferred until a first real upstream Croissant record is selected.

## Relationship to Visual Spelunker
The Foundry supplies benchmark identity and component acquisition rules. A Visual Spelunker stimulus ledger supplies the exact acquired byte hash, decoded-pixel hash, processor/transform identity, and realization hash for each run. Foundry approval means reproducible/provenance-checked acquisition, not scientific sufficiency or freedom from benchmark contamination.

## Rep success
- schema is Draft 2020-12 valid;
- project synthetic and Open Images fixtures validate;
- mirror-without-verified-redistribution fails closed;
- malformed composite materialization fails closed;
- benchmark overlays without dependencies fail closed;
- existing Foundry contracts remain untouched;
- CI executes on a public hosted runner with read-only repository permission.

## Next if successful
1. add a real Croissant-bearing dataset specimen;
2. add immutable candidate-manifest identity for non-OCI benchmark components;
3. add upstream hydration with expected file/sample hashes;
4. connect one approved benchmark identity to a Visual Spelunker stimulus-ledger rep;
5. only then add further benchmark families such as Visual Genome, XM3600, SugarCrepe, VL-CheckList, or LVIS.
