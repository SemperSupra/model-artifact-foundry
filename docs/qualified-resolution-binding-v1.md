# Qualified resolution binding v1

Status: first-consumer MVP contract for Foundry issue #37.

## Purpose

A qualification receipt proves that a specific artifact/representation/runtime/target/workload subject passed the required project quality and resource/performance gates.

A qualified resolution binding answers the next deterministic question:

> For this exact project request and concrete target environment, which already-qualified subject did we retain as the known answer?

This is the minimum state needed to prove the determinization ratchet. It is not a model catalog service or recommendation engine.

## Stable resolution key

The known-path lookup context is deliberately small:

```text
canonical request digest
+ target profile ID
+ exact semantic environment digest
```

The stable identity is:

```text
resolution_key = sha256(canonical {
  request_digest,
  target_profile_id,
  environment_digest
})
```

The request digest already binds capability/interface, offline/runtime constraints, representation/quantization constraints, declared resource/performance envelope, and project quality-policy identity.

The target environment digest binds the concrete private environment semantics separately from the public request.

The key deliberately excludes qualification event time, evidence ordering/storage reference, provider-native/local model path, materialization receipt path, and host-local resolution-store path.

## Binding authority

`tools/qualified_resolution.py` creates a binding only from a valid **qualified** qualification receipt.

The tool mechanically requires:

- receipt request digest == canonical request digest;
- receipt target profile == request target profile;
- receipt environment digest == lookup environment digest;
- receipt selected runtime/representation/quantization satisfies the request;
- exact selection facts come from the qualified receipt subject;
- the receipt's canonical subject/record digests validate.

A rejected qualification cannot be retained as a qualified resolution.

## Binding contents and integrity

The v1 binding retains:

- canonical resolution context + `resolution_key`;
- qualified `subject_key` + `record_digest`;
- exact artifact provider/repository/revision/observation digest;
- representation ID/variant/quantization;
- runtime ID;
- target profile ID;
- canonical `binding_digest` over all of the preceding binding body.

`binding_digest` is deliberately distinct from `resolution_key`:

- `resolution_key` says **which request/environment lookup slot this is**;
- `binding_digest` says **exactly what qualified subject/selection is stored in that slot**.

This distinction matters because a later edit to artifact/runtime/qualification references must be detected even when request/environment have not changed.

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

A new qualification event for the same request/environment can legitimately have the same `resolution_key` and `subject_key` but a different qualification `record_digest`. V1 does **not** silently replace the retained decision in that case; it reports a conflict so lifecycle/requalification policy cannot emerge accidentally from file-write order.

There is deliberately no daemon, database, lock service, global index, web API, expiry mechanism, or automatic replacement policy in v1.

## Deterministic lookup

Given request + target environment:

```text
compute request digest
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

## Changed-envelope experiment

Changing any material request fact changes `request_digest`, and therefore `resolution_key`.

Changing target profile or semantic environment digest also changes `resolution_key`.

The old retained binding therefore cannot be silently reused after a material envelope/target change.

For the first experiment:

1. qualify one real KV-Ground subject;
2. retain its resolution binding;
3. rerun the exact request/environment and require a deterministic hit;
4. change exactly one material request/target/environment fact;
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
  --receipt <qualified-receipt.json> \
  --store <private/local-resolution-store>
```

Look up a known resolution:

```text
python tools/qualified_resolution.py lookup \
  --request <request.json> \
  --environment-digest sha256:<environment> \
  --store <private/local-resolution-store> \
  --output <model-plan-result.json>
```

Missing binding is a successful deterministic lookup operation whose plan status is `unknown`, not an execution error.

Malformed/tampered state is different and fails execution rather than pretending nothing was retained.

## Privacy and public execution

The code/schema/tests are public-safe and provider-free. Real first-consumer resolution bindings may remain private/local because they can carry opaque target IDs and qualification references tied to private evidence.

Public Foundry code does not own the private screenshot corpus, raw hardware inventory, credentials, or native model bytes.

## R4

- **reproducible:** versioned canonical context/binding plus binding integrity digest;
- **repeatable:** equivalent request/environment computes the same key and finds the same retained binding;
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

The first real repeat/changed-envelope evidence decides whether broader retained-planning infrastructure is earned.
