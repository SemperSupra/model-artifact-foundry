# Qualification receipt v1

Status: first-consumer MVP contract for issue #31.

## Purpose

A Foundry materialization receipt answers:

> Is this exact provider artifact available here as a verified provider-native handle?

A qualification receipt answers a different question:

> Did this exact artifact/representation/runtime tuple satisfy this capability request on this target under this frozen project-owned validation basis?

The qualification receipt binds evidence. It does not move project-specific evaluation policy into Foundry.

## Two identities

### `subject_key`

`subject_key` is SHA-256 over canonical JSON for `subject` only.

It is the deterministic lookup identity for an equivalent qualification subject. It includes facts whose change invalidates equivalence:

- capability + interface;
- request/envelope digest;
- stable provider artifact identity: provider, repository/locator, immutable source revision, and identity strength;
- representation/quantization;
- runtime/toolchain/config;
- target profile + environment snapshot;
- project/workload + frozen capture/holdout/evaluator/policy basis.

It deliberately excludes:

- event timestamp;
- evidence storage/reference locations;
- normalized provider-observation digest;
- machine-local native model path;
- materialization receipt digest when that receipt includes machine-local handle state;
- the pass/fail result itself.

This allows a repeated qualification event on an equivalent subject to resolve to the same lookup key while retaining a distinct event record.

For the first Hugging Face slice, the stable artifact tuple remains conservative: a different immutable `source_revision` is a different qualification subject. This v1 contract does not attempt to prove payload-equivalence across two different provider commits, even when a change appears documentation-only.

### `record_digest`

`record_digest` is SHA-256 over canonical JSON for the complete receipt **except the `record_digest` field itself**.

It therefore binds:

- the stable subject + subject key;
- event time;
- qualification/rejection result;
- canonical sorted evidence references/digests.

A repeated event may have the same `subject_key` and a different `record_digest`.

## Observation evidence is not subject identity

A normalized provider observation is an evidence event. Its canonical digest may legitimately change when the same immutable provider revision is recaptured because the observation contains event-local facts such as observation time or evidence references.

Therefore the full normalized observation digest is retained under `evidence`, not embedded in `subject.artifact`. The stable subject already binds the immutable provider identity tuple needed by the first Hugging Face consumer.

This separation prevents a metadata recapture from manufacturing a new qualification subject when provider/repository/source revision, representation, runtime, target, request, and validation basis are unchanged.

## Result semantics

The v1 receipt records only completed qualification attempts:

- `qualified`: both the project quality gate and the required resource/performance gate passed;
- `rejected`: at least one required gate failed, with explicit rejection reason(s).

`UNKNOWN` is not a qualification receipt outcome. It belongs to the planner/control plane when the system lacks sufficient retained evidence to select/qualify a known tuple.

The builder refuses to emit `qualified` unless both independent gates are `pass`. It also refuses a `rejected` record unless at least one gate is `fail` and at least one reason is retained.

## First-consumer mapping: `desktop-ui-cv` KV-Ground

The first real receipt should be assembled only after the consumer local-handle seam, real holdout capture, project evaluation, and resource/performance measurement exist.

| Receipt field | First-consumer evidence |
|---|---|
| `capability.id` | `ui-grounding` |
| `capability.interface` | versioned `desktop-ui-cv` grounding interface used by the qualification run |
| `request.digest` | canonical digest of the versioned capability/target/envelope request |
| `artifact.provider/repository/source_revision/identity_strength` | stable immutable identity copied from the exact normalized Hugging Face observation |
| `representation` | exact selected representation/variant/quantization, e.g. HF Transformers snapshot + NF4 when used |
| `runtime.id` | runtime family used by the consumer, e.g. Transformers/PyTorch |
| `runtime.toolchain_digest` | canonical exact runtime/toolchain inventory digest |
| `runtime.config_digest` | canonical runtime configuration digest, including material loader policy relevant to validity |
| `target.profile_id` | stable opaque target profile identifier |
| `target.environment_digest` | canonical private environment snapshot digest; raw private hardware details need not be public |
| `validation.project` | `SemperSupra/desktop-ui-cv` |
| `validation.workload_id` | frozen first-consumer workload ID |
| `validation.capture_manifest_digest` | canonical digest of the real semantic capture provenance manifest from `desktop-ui-cv` PR #30 / WineBot #121 |
| `validation.holdout_digest` | `sha256:` + the evaluator's canonical `holdout_sha256` |
| `validation.evaluator_digest` | digest of the exact evaluator implementation/bundle used |
| `validation.policy_digest` | `sha256:` + the evaluator's canonical `policy_sha256` |
| `result.quality.result_digest` | canonical project evaluation-result digest |
| `result.resource_performance.result_digest` | canonical bounded performance/resource result digest |
| evidence `kind=provider_observation` | full canonical normalized provider-observation digest/ref for provenance; event-local, not subject identity |

The `desktop-ui-cv` evaluator already records `candidate_ref`, `holdout_sha256`, `policy_sha256`, metrics, failed thresholds, and `qualification_pass`. The project remains authority for those semantics. Foundry consumes the resulting digest/binding rather than reimplementing the evaluator.

## Materialization evidence is event evidence, not subject identity

The HF native materialization receipt includes a machine-local native handle so the immediate consumer can load the snapshot. That path is intentionally not durable artifact identity.

Therefore the qualification subject binds the stable provider artifact tuple, while both the full normalized provider observation and the particular materialization receipt are retained under `evidence`, for example:

```json
[
  {
    "kind": "provider_observation",
    "digest": "sha256:...",
    "ref": "public://...",
    "visibility": "public"
  },
  {
    "kind": "materialization_receipt",
    "digest": "sha256:...",
    "ref": "local://...",
    "visibility": "local"
  }
]
```

A second machine may have a different materialization receipt and local path while still qualifying the same semantic subject if artifact, representation, runtime, target environment, request, and validation basis are equivalent. Likewise, recapturing the same immutable provider revision may produce a different provider-observation record without changing qualification equivalence.

## Evidence visibility

Evidence entries carry `public`, `private`, or `local` visibility. A reference is a locator/reference only; it does not imply Foundry owns or republishes the evidence.

For the first consumer:

- normalized public HF observation may be public;
- model materialization receipt may remain local;
- captured screenshots, holdout annotations, predictions, target inventory, and detailed performance evidence remain private unless separately authorized.

No credential value belongs in a receipt.

## Determinization use

After a successful first qualification:

1. retain the receipt keyed by `subject_key`;
2. build the equivalent request/subject again;
3. deterministic lookup should find the retained qualified subject without model research/generation;
4. recapturing the same immutable provider revision must not create a new subject merely because observation-event metadata changed;
5. change exactly one material fact (target environment, envelope/request digest, representation, runtime, artifact source revision, or validation policy);
6. the subject key must change;
7. deterministic machinery either finds an already-qualified alternate or returns `UNKNOWN` to the bounded exploration layer.

This contract supplies the evidence identity needed for that ratchet; it is not itself the catalog/database implementation.

## Fixture warning

`fixtures/qualification/kv-ground-qualification-draft.example.json` is a deterministic contract fixture with placeholder digests. It is **not** real KV-Ground qualification evidence and must never be promoted into a catalog as a qualified production/consumer tuple.

## CLI

Build a receipt from a draft:

```text
python tools/qualification_receipt.py \
  --input <qualification-draft.json> \
  --output <qualification-receipt.json>
```

Validate an existing receipt and recompute both digests:

```text
python tools/qualification_receipt.py \
  --input <qualification-receipt.json> \
  --validate-existing
```

The builder is stdlib-only, sorts evidence deterministically, and writes canonical JSON atomically.
