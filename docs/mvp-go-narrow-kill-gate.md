# First-consumer GO / NARROW / KILL gate

Status: frozen pre-result decision gate for Foundry issue #33.

This document is frozen before real KV-Ground qualification output is observed. Its purpose is to prevent the proving criteria from being relaxed or redefined after results arrive.

## Separation of machinery and authority

The gate has two layers:

```text
qualification / repeat / changed-envelope / value / R4 evidence
                         |
                         v
        deterministic readiness checker
              READY / NOT_READY
              + GO mechanical eligibility
                         |
                         v
              designated authority
                GO / NARROW / KILL
```

The readiness checker is deliberately incapable of emitting the final architecture decision.

A failed experiment is still evidence. For example, a rejected first qualification or a repeat that invokes research can still produce a mechanically complete evidence package and support a NARROW/KILL judgment. Missing or contaminated evidence is different: that produces `NOT_READY`.

## Frozen evidence package

The versioned evidence manifest is `schemas/mvp-decision-evidence-v1.schema.json`.

### 1. First qualification

Record the qualification receipt digest, subject key, and actual outcome.

For GO mechanical eligibility the outcome must be `qualified`. A `rejected` outcome may still leave the final decision gate READY for NARROW/KILL once the other required experiments and evidence exist.

### 2. Equivalent repeat

Repeat the same qualification subject and record whether:

- the same subject key was reproduced;
- retained evidence was found deterministically;
- Generator–Validator/candidate generation was invoked;
- provider/model research was invoked.

For GO:

- subject key must match;
- deterministic retained-record lookup must succeed;
- generator and provider research must not run.

If those fail, preserve the failure; do not reroute the attempt merely to produce a green trace.

### 3. Changed-envelope test

Change exactly one material request/target/envelope dimension and retain both original and changed request digests.

The old qualification record must not be reused as though the request were unchanged.

Allowed deterministic dispositions are:

- `known_qualified_alternative`;
- `unknown`;
- `rejected`.

Generator invocation is GO-compatible only after deterministic `unknown`. A generator invocation after a known alternative or deterministic rejection violates the escalation boundary.

### 4. Consumer value delta

Record each outcome explicitly rather than hiding it in one score:

- exact identity preserved;
- verified local handle is the normal qualified path;
- provider credentials removed from normal serving;
- implicit provider download no longer normal serving behavior;
- provider-native storage/cache ownership preserved;
- repeated research/acquisition work avoided.

False values are valid evidence, but they block GO mechanical eligibility.

### 5. Control / R4

The following are evidence-validity requirements. If false, the gate is NOT_READY rather than merely a GO failure:

- validator/policy frozen before candidate results;
- holdout frozen before candidate results;
- exact evidence retained;
- privacy boundary preserved.

The following are experiment outcomes and GO requirements, but may fail while still leaving a NARROW/KILL decision READY:

- repeated operation demonstrated idempotence;
- rollback path is understood.

### 6. Lifecycle assessment

Provide a digest/reference to a written lifecycle assessment covering at least:

- new schemas/interfaces/tooling to maintain;
- provider-specific dependency/churn cost;
- remaining manual steps;
- CI/runtime cost;
- operational burden;
- whether the shared layer is materially smaller/clearer than duplicated project-local responsibility.

The checker validates that the assessment exists; authority judges whether the cost is acceptable.

## Deterministic checker outputs

`tools/check_mvp_decision_readiness.py` produces:

- `decision_readiness`: `READY` or `NOT_READY`;
- `readiness_blockers`: missing/invalid evidence conditions;
- `go_mechanical_eligible`: boolean;
- `go_blockers`: explicit mechanical facts that prevent GO;
- a fixed note that the checker does not choose GO/NARROW/KILL.

`READY` does **not** mean GO. It means enough trustworthy evidence exists for authority to make a final decision.

## Authority decision meanings

### GO

GO requires:

1. `decision_readiness = READY`;
2. `go_mechanical_eligible = true`;
3. authority judges the shared layer materially reduces repeated project-local model identity/acquisition/qualification toil at acceptable lifecycle cost.

GO authorizes only **BHADA as the next stronger falsification consumer**. It does not authorize broad model migration, generalized provider/plugin infrastructure, catalog UI, dynamic scheduling, or fleet-wide rollout.

### NARROW

NARROW is appropriate when evidence supports a useful subset but not the broader architecture.

The decision record must name, separately:

- retained capabilities;
- removed/deferred capabilities;
- why the retained subset still earns its lifecycle cost;
- what evidence would be required to broaden again.

Likely retainable subsets include exact identity/provenance, provider-native materialization, explicit local-handle loading, and qualification evidence binding without a generalized planner/Generator–Validator layer.

### KILL

KILL/REVERT is appropriate when evidence demonstrates that the shared layer does not remove meaningful ambiguity/toil, cannot preserve authority/evidence integrity, cannot demonstrate useful determinization, or costs more to operate than the duplicated responsibility it replaces.

The decision record must state:

- rollback point;
- what integration is removed/reverted;
- which artifacts remain as useful specification/research evidence;
- whether any narrower reusable mechanism survives independently.

## Final authority record template

After the evidence checker reports READY, record the human/designated-authority decision separately from the evidence manifest:

```text
Decision: GO | NARROW | KILL
Gate ID: first-consumer-kv-ground-v1
Evidence manifest digest/ref: ...
Readiness result digest/ref: ...
Authority: ...
Recorded at: ...
Rationale: ...

If NARROW:
  retain: ...
  remove/defer: ...

If KILL:
  rollback point: ...
  retained lessons/artifacts: ...

If GO:
  next authorized falsification: BHADA only
```

Do not embed the authority decision in `mvp-decision-evidence-v1`; this separation prevents a deterministic evidence checker from silently becoming the decision-maker.

## CLI

```text
python tools/check_mvp_decision_readiness.py \
  --input <first-consumer-decision-evidence.json> \
  --output <readiness-result.json>
```

Exit status is `0` for READY and `2` for NOT_READY. GO mechanical ineligibility alone does not cause NOT_READY because failed experiments are still valid evidence for NARROW/KILL.

## Fixture warning

`fixtures/decision/first-consumer-ready.example.json` is a deterministic contract fixture with placeholder digests. It is not actual qualification, repeat, changed-envelope, lifecycle, or authority evidence.
