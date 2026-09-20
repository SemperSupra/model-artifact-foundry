# Hosted realization provenance

Hosted provider APIs do not normally expose immutable model bytes. The Foundry therefore
records **observed hosted realizations** separately from immutable artifact identities.

## Invariant

A hosted realization observation is evidence about a provider-served model/service at a
particular time. It is **not** a cryptographic identity for model weights, quantization,
serving kernels, prompt templates, or policy layers that the provider does not expose.

## Minimal fields

Record only observable facts:

- provider;
- requested model ID or alias;
- resolved/returned model ID when exposed;
- provider model version/revision when exposed;
- backend/system fingerprint when exposed;
- API/interface family/version when relevant;
- service tier when exposed;
- observation timestamp;
- direct versus intermediary route;
- intermediary/upstream provider/fallback observation when exposed;
- provenance strength.

Unknown values remain null. Do not infer hidden checkpoints from marketing names.

## Provenance strength

- `VERSIONED_HOSTED`: provider exposes a concrete model version/revision.
- `FINGERPRINTED_HOSTED`: stable/named model plus a backend/system fingerprint.
- `NAMED_HOSTED`: stable/named hosted model without stronger identity.
- `MUTABLE_ALIAS`: mutable alias such as `latest`, preview, or equivalent.
- `ROUTED_UNKNOWN`: router/intermediary treatment where the exact upstream realization is unresolved.

These labels describe evidence strength only. They do not score model quality.

## Drift

A changed version/fingerprint creates a new observation. Historical evidence is never
rewritten. A consumer such as Model Spelunker may use drift as a trigger for a bounded
requalification/challenge rep, but Foundry does not infer that performance changed.

## Boundary

Foundry owns hosted model identity/provenance. It does not own task qualification,
actor ranking, provider routing, credentials, spend controls, or acceptance decisions.
