# Qualified resolution binding v1

Status: first-consumer MVP contract for Foundry issue #37.

## Purpose

A qualification receipt proves that a specific stable artifact/representation/runtime/target/workload subject passed the required project quality and resource/performance gates.

A qualified resolution binding answers:

> For this exact project request, concrete target environment, and concrete runtime identity, which already-qualified subject did we retain as the known answer?

This is the minimum file-backed state needed for the determinization ratchet. It is not a catalog service or recommendation engine.

## Stable resolution key

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

The request digest binds capability/interface, requirement-side runtime/representation constraints, declared resource envelope, and quality-policy identity. The environment digest binds the concrete target. The concrete runtime identity binds the exact runtime family/toolchain/configuration that was qualified.

Changing request, target, environment, runtime ID, runtime toolchain, or runtime config changes the resolution key. Wall clock, evidence ordering/ref, provider-observation event, local model path, materialization path, and resolution-store path do not.

## Binding authority

`tools/qualified_resolution.py` creates a binding only from a valid `qualified` qualification receipt. It requires:

- receipt request digest == canonical request digest;
- receipt target profile == request target profile;
- receipt environment digest == lookup environment digest;
- receipt runtime ID/toolchain/config == lookup runtime context;
- runtime ID is allowed by the request;
- selected representation/quantization satisfies the request;
- stable selection facts are derived from the receipt subject;
- receipt subject and record digests validate.

Rejected receipts cannot create a known-qualified resolution.

## Stable selection vs observation evidence

The retained selection contains only stable chosen-artifact facts needed by model-plan result v1:

- provider;
- repository;
- immutable source revision;
- representation ID/variant/quantization;
- selected runtime ID;
- target profile ID.

It deliberately does **not** contain a normalized provider-observation digest. A provider observation is an evidence event and may be recaptured for the same immutable provider revision. Its digest/ref belongs in qualification/result evidence rather than retained selection identity.

For v1, a different immutable provider `source_revision` remains a different artifact selection. We do not yet infer payload equivalence across different provider commits.

## Binding contents and integrity

The binding retains:

- canonical resolution context + `resolution_key`;
- qualified `subject_key` + `record_digest`;
- stable exact selection;
- `binding_digest` over the canonical binding body.

`resolution_key` identifies the request/target/runtime lookup slot. `binding_digest` identifies exactly what qualified subject/selection is stored in that slot. Lookup recomputes both and fails closed on tampering.

A later qualification event for the same subject can have the same resolution key and subject key but a different record digest. V1 deliberately refuses silent replacement and reports a conflict; lifecycle/requalification policy is not inferred from file-write order.

## File-backed MVP storage

```text
<resolution-store>/<64-hex>.json
```

The semantic key remains `sha256:<64-hex>` in the binding; the filename uses only the hex suffix for Windows compatibility.

- new key -> atomic canonical write;
- identical binding -> idempotent no-op;
- same key + different valid binding -> explicit conflict;
- malformed/tampered state -> fail closed.

No daemon, database, lock service, global index, expiry mechanism, or automatic replacement policy is introduced.

## Deterministic lookup

```text
request + environment + runtime
          |
          v
   resolution_key
     /         \
 absent       present
   |             |
 unknown      validate binding
                 |
           invalid -> fail closed
                 |
              valid
                 |
         qualified plan result
```

The hit path performs no provider query, model search, candidate generation, LLM call, acquisition, or inference.

## First MVP proof

1. qualify one real KV-Ground subject;
2. retain its resolution binding;
3. rerun the exact request/environment/runtime and require a deterministic hit;
4. change exactly one material request/target/environment/runtime fact;
5. require a different resolution key;
6. if no binding exists for that new key, return explicit `unknown`;
7. only a genuine unknown may open bounded candidate exploration.

Provider-observation recapture by itself is not a changed-context experiment and must not produce a different stable selection or subject.

## CLI

Retain:

```text
python tools/qualified_resolution.py retain \
  --request <request.json> \
  --environment-digest sha256:<environment> \
  --runtime-id <runtime-id> \
  --runtime-toolchain-digest sha256:<toolchain> \
  --runtime-config-digest sha256:<config> \
  --receipt <qualified-receipt.json> \
  --store <resolution-store>
```

Lookup:

```text
python tools/qualified_resolution.py lookup \
  --request <request.json> \
  --environment-digest sha256:<environment> \
  --runtime-id <runtime-id> \
  --runtime-toolchain-digest sha256:<toolchain> \
  --runtime-config-digest sha256:<config> \
  --store <resolution-store> \
  --output <model-plan-result.json>
```

Missing binding is a successful deterministic lookup with plan status `unknown`; malformed retained state is an execution error.

## Privacy / R4

Code/schema/tests are public-safe. Real bindings may remain private/local. No screenshot data, credentials, native model paths, or raw target inventory belong in the binding.

- reproducible: canonical versioned context/binding;
- repeatable: equivalent request/environment/runtime -> same key;
- reversible: deleting retained files does not mutate providers/models/runtimes;
- idempotent: retaining the exact same binding is a no-op.

## Deferred

No generalized catalog, ranking, expiry/revocation policy, distributed synchronization, fleet scheduling, provider discovery, or Generator–Validator implementation is implied by this MVP layer.
