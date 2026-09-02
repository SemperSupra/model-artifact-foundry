# Qualified resolution binding v1

Status: first-consumer MVP contract for Foundry issue #37.

## Purpose

A qualification receipt proves that a specific artifact/representation/runtime/target/workload subject passed the required project quality and resource/performance gates.

A qualified resolution binding answers the next deterministic question:

> For this exact project request, concrete target environment, and concrete runtime identity, which already-qualified subject did we retain as the known answer?

This is the minimum state needed to prove the determinization ratchet. It is not a model catalog service or recommendation engine.

## Stable resolution key

The known-path lookup context is deliberately small but must include every concrete execution fact required for qualification-subject equivalence:

```text
canonical request digest
+ target profile ID
+ exact semantic environment digest
+ concrete runtime ID
+ runtime toolchain digest
+ runtime configuration digest
```

The stable identity is:

```text
resolution_key = sha256(canonical {
  request_digest,
  target_profile_id,
  environment_digest,
  runtime: {
    id,
    toolchain_digest,
    config_digest
  }
})
```

The request digest binds capability/interface, offline/runtime-family constraints, representation/quantization constraints, declared resource/performance envelope, and project quality-policy identity.

The target environment digest binds the concrete private platform/hardware semantics separately from the public request.

The concrete runtime identity binds the actual runtime family plus the exact toolchain/configuration that was part of the qualification subject. This is intentionally separate from the request: the request says which runtime families are acceptable; the resolution context says which concrete runtime instance was actually qualified.

The key deliberately excludes qualification event time, evidence ordering/storage reference, provider-native/local model path, materialization receipt path, and host-local resolution-store path.

## Why runtime identity is part of the key

Qualification receipt v1 includes `runtime.id`, `runtime.toolchain_digest`, and `runtime.config_digest` in the stable qualification subject. A retained lookup must not erase those facts.

In particular, the private target `environment_digest` used by the first consumer deliberately describes platform/hardware semantics and keeps Python/Torch/Transformers and loader configuration in the separate runtime/toolchain/config identity. Therefore a toolchain or loader-config change is a different concrete execution subject even when request, target profile, and hardware environment are unchanged.

A changed runtime digest must produce a different resolution key. If no binding exists for that exact runtime context, lookup returns explicit `unknown`; it must not reuse a qualification earned under another toolchain/configuration.

This is subject-equivalence correctness, not automatic expiry/requalification policy.

## Binding authority

`tools/qualified_resolution.py` creates a binding only from a valid **qualified** qualification receipt.

The tool mechanically requires:

- receipt request digest == canonical request digest;
- receipt target profile == request target profile;
- receipt environment digest == lookup environment digest;
- receipt concrete runtime ID/toolchain/config == lookup runtime context;
- concrete runtime ID is allowed by the request;
- receipt selected runtime/representation/quantization satisfies the request;
- exact selection facts come from the qualified receipt subject;
- the receipt's canonical subject/record digests validate.

A rejected qualification cannot be retained as a qualified resolution.

## Binding contents and integrity

The v1 binding retains:

- canonical resolution context + `resolution_key`;
- concrete runtime ID/toolchain/config inside that resolution context;
- qualified `subject_key` + `record_digest`;
- exact artifact provider/repository/revision/observation digest;
- representation ID/variant/quantization;
- selected runtime ID;
- target profile ID;
- canonical `binding_digest` over all of the preceding binding body.

`binding_digest` is deliberately distinct from `resolution_key`:

- `resolution_key` says **which request/target/runtime lookup slot this is**;
- `binding_digest` says **exactly what qualified subject/selection is stored in that slot**.

This distinction matters because a later edit to artifact/runtime/qualification references must be detected even when the lookup context itself has not changed.

Lookup recomputes `binding_digest` and fails closed on any content mutation. The digest is also the evidence digest emitted on a successful retained-resolution result.

It does not duplicate private holdout, performance, target inventory, credentials, or native model paths. Those remain evidence behind the qualification receipt.

## File-backed MVP storage

Use an ordinary directory:

```text
<resolution-store>/
  <64-hex>.json
```

The semantic key remains `sha256:<64-hex>` inside the binding. The filename uses only the hex suffix because `:` is not valid in Windows filenames.

Retention behavior:

- new key -> atomically write canonical binding;
- same key + byte-equivalent canonical binding -> idempotent no-op;
- same key + different **valid** binding -> explicit conflict/fail closed;
- malformed/tampered existing binding -> fail closed.

A new qualification event for the same request/environment/runtime can legitimately have the same `resolution_key` and `subject_key` but a different qualification `record_digest`. V1 does **not** silently replace the retained decision in that case; it reports a conflict so lifecycle/requalification policy cannot emerge accidentally from file-write order.

There is deliberately no daemon, database, lock service, global index, web API, expiry mechanism, or automatic replacement policy in v1.

## Deterministic lookup

Given request + target environment + current concrete runtime identity:

```text
compute request digest
normalize runtime identity
compute resolution key
        |
        +-- file absent --> unknown(no_retained_qualified_resolution)
        |
        +-- file present --> verify resolution key + binding digest
                               |
                               +-- invalid/tampered --> error/fail closed
                               |
                               +-- valid --> qualified model-plan result
```

A successful lookup produces the versioned model-plan `qualified` result from the request/result contract. It references the retained qualification subject/record and exact selection.

No provider metadata request, model search, candidate generator, LLM, or model acquisition is needed on the hit path.

## Changed-context experiment

Changing any material request fact changes `request_digest`, and therefore `resolution_key`.

Changing target profile, semantic environment digest, runtime ID, runtime toolchain digest, or runtime configuration digest also changes `resolution_key`.

The old retained binding therefore cannot be silently reused after a material requirement/target/runtime change.

For the first experiment:

1. qualify one real KV-Ground subject;
2. retain its resolution binding;
3. rerun the exact request/environment/runtime and require a deterministic hit;
4. change exactly one material request/target/environment/runtime fact;
5. require a different resolution key;
6. if the changed key has no existing valid binding, return explicit `unknown`;
7. only that genuine `unknown` may open bounded Generator–Validator/candidate exploration;
8. if exploration later succeeds, retain a binding for the new key so the next equivalent request is deterministic.

## CLI

Retain from a qualified receipt:

```text
python tools/qualified_resolution.py retain \
  --request <canonical-or-equivalent-request.json> \
  --environment-digest sha256:<environment> \
  --runtime-id <runtime-family-id> \
  --runtime-toolchain-digest sha256:<toolchain> \
  --runtime-config-digest sha256:<config> \
  --receipt <qualified-receipt.json> \
  --store <private/local-resolution-store>
```

Look up a known resolution:

```text
python tools/qualified_resolution.py lookup \
  --request <request.json> \
  --environment-digest sha256:<environment> \
  --runtime-id <runtime-family-id> \
  --runtime-toolchain-digest sha256:<toolchain> \
  --runtime-config-digest sha256:<config> \
  --store <private/local-resolution-store> \
  --output <model-plan-result.json>
```

Missing binding is a successful deterministic lookup operation whose plan status is `unknown`, not an execution error.

Malformed/tampered state is different and fails execution rather than pretending nothing was retained.

## Privacy and public execution

The code/schema/tests are public-safe and provider-free. Real first-consumer resolution bindings may remain private/local because they can carry opaque target IDs and qualification references tied to private evidence.

Runtime toolchain/config digests are semantic identities, not credentials or host paths. Public Foundry code does not own the private screenshot corpus, raw hardware inventory, credentials, or native model bytes.

## R4

- **reproducible:** versioned canonical context/binding plus binding integrity digest;
- **repeatable:** equivalent request/environment/runtime computes the same key and finds the same retained binding;
- **reversible:** removing the file-backed state does not mutate providers/models/runtimes;
- **idempotent:** retaining the exact same binding is a no-op with identical bytes.

## Deferred

Do not infer the following from this MVP layer:

- generalized catalog/database service;
- multi-candidate ranking;
- expiry/revocation/requalification policy;
- distributed locking;
- cross-host synchronization;
- fleet scheduling;
- provider discovery;
- Generator–Validator implementation.

The first real repeat/changed-context evidence decides whether broader retained-planning infrastructure is earned.
