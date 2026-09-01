# Model request/result v1 — first-consumer boundary

Status: minimal contract for Foundry issue #35 and the first `desktop-ui-cv` / KV-Ground proving slice.

## Purpose

The request states **what the project needs**, without naming how or where to acquire a model. The result states **what retained deterministic knowledge says about that request**.

This contract gives qualification receipt v1 a real `request_digest` and gives the changed-envelope experiment a mechanically meaningful identity boundary.

It is not a general planner implementation.

## Request v1

A request contains only material first-consumer requirement facts:

```text
capability + versioned interface
        +
target profile ID
        +
offline/runtime constraints
        +
representation/quantization constraints
        +
declared resource/performance envelope
        +
frozen project quality-policy identity
```

It deliberately does not contain:

- provider URL or provider name;
- model repository/model ID;
- provider token/credential;
- local/native model path;
- acquisition/download instructions;
- selected candidate;
- event timestamp.

If any of those are added to the request object, the strict canonicalizer rejects them rather than ignoring them.

### Target profile

`target.profile_id` is an opaque stable profile reference. Detailed/private hardware inventory does not need to be in this public contract. Qualification evidence separately binds the exact target environment snapshot digest.

### Runtime

`runtime.offline_required` is a hard project requirement. `runtime.allowed_ids` is the allowed runtime family set for the experiment.

The first KV-Ground consumer is expected to require offline normal serving after a verified local handle has been supplied. Provider-native materialization remains a separate pre-serving concern.

### Representation

`representation.allowed_ids` and `allowed_quantizations` define which representations are acceptable to the project/runtime experiment. These are constraints, not a selected answer.

### Resource/performance envelope

`envelope` may contain any of the following only when the consumer has actually frozen a meaningful limit:

- `max_peak_vram_gib` — maximum observed peak GPU-memory allocation/reservation under the defined qualification procedure;
- `max_model_load_seconds` — maximum wall-clock time from the defined pre-load state until the model/processor pair is ready for the qualification workload;
- `max_p95_query_latency_ms` — maximum p95 end-to-end query latency over the defined measured query set after the defined warm-up procedure.

These names are intentionally measurement-specific. Generic `max_query_latency_ms` and `max_steady_state_vram_gib` were rejected before the contract was frozen because they permit materially different measurement interpretations.

Omitting a limit means this request version does not constrain that dimension. Do not invent a number just to populate the schema.

**Important:** the numeric values in `fixtures/request/ui-grounding-request.example.json` are deterministic contract-test values only. They are not approved first-consumer KV-Ground resource/performance thresholds. The real first-consumer envelope and measurement procedure must be frozen separately before candidate performance is observed.

### Quality policy

`quality_policy.id` + `quality_policy.digest` binds the project-owned threshold policy required by this request. The policy implementation/semantics remain project-owned.

## Canonical identity

The stable request identity is:

```text
sha256(canonical normalized request JSON)
```

`tools/model_request_contract.py` normalizes:

- object key ordering through canonical JSON;
- allowed runtime IDs;
- allowed representation IDs;
- allowed quantization values.

Duplicate allowed values are rejected. The request digest is independent of storage location and wall-clock time.

Any material change to target/runtime/offline/representation/quantization/quality policy or a declared envelope limit changes the digest.

## Result v1

A result is bound to the exact canonical request digest and has one status.

### `qualified`

A retained qualification already exists for this request/selection subject.

Requires:

- exact selection;
- retained qualification `subject_key`;
- retained qualification `record_digest`.

### `candidate`

A specific exact candidate is proposed, but it has **not** yet been qualified for this subject.

Requires exact selection; forbids a qualification reference.

### `unknown`

Retained deterministic knowledge is insufficient to produce a qualified result or deterministic rejection.

Requires explicit unresolved reason(s). Forbids selection/qualification fields.

Only this state may justify escalation to bounded Generator–Validator exploration under the established control model.

### `rejected`

The request/candidate space is deterministically infeasible or disallowed for explicit reasons.

Requires explicit reason(s). Forbids selection/qualification fields. Rejection is evidence; it does not automatically trigger exploration.

## Exact selection shape

A `qualified` or `candidate` selection binds:

- provider;
- repository;
- immutable source revision;
- normalized observation digest;
- representation ID/variant/quantization;
- runtime ID;
- target profile ID.

The contract helper mechanically rejects a selection whose target, runtime, representation, or quantization is outside the request.

The selection does not use a machine-local model path as durable identity. A materialization receipt can be retained as event evidence separately.

## Relationship to qualification receipt

Qualification receipt v1 uses the canonical request digest as one component of the stable qualification subject key.

This gives the determinization test a clean rule:

```text
same request digest + same other subject facts
    -> equivalent qualification subject

material request/envelope change
    -> different request digest
    -> old qualification must not be silently reused
```

The target environment digest still belongs in the qualification subject because two concrete environments may differ even when they share a logical target profile ID.

## CLI

Canonicalize a request:

```text
python tools/model_request_contract.py request \
  --input <request.json> \
  --output <canonical-request.json>
```

Compute its digest:

```text
python tools/model_request_contract.py digest --input <request.json>
```

Validate/canonicalize a result against the exact request:

```text
python tools/model_request_contract.py result \
  --request <request.json> \
  --input <result.json> \
  --output <canonical-result.json>
```

## R4

- reproducible: versioned strict request/result schemas and deterministic fixture;
- repeatable: equivalent request input canonicalizes to the same bytes/digest;
- reversible: no runtime/catalog/provider mutation;
- idempotent: repeated canonicalization/result validation has no side effects beyond the requested output file.

## Deferred

This contract does not implement:

- persistent qualified lookup/catalog storage;
- model ranking;
- candidate generation;
- Generator–Validator exploration;
- target discovery;
- provider discovery;
- broad model ontology;
- project evaluation.

Those behaviors must be earned by the first real proving experiment rather than inferred from the existence of a schema.
