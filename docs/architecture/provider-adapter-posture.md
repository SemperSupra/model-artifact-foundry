# Provider adapter posture — extraction-ready without plugin infrastructure

Status: current architectural posture for the identity-first MVP.

## Decision

Use **narrow in-tree provider adapters/integrations** where a provider-specific semantic boundary is already proven. Do not add a general plugin system, automatic discovery, or separately distributed provider wheels to the MVP critical path.

For the current Hugging Face identity slice, the first proven boundary is:

```text
captured provider evidence
        ↓
in-tree provider evidence adapter
        ↓
normalized Foundry observation
        ↓
deterministic Foundry control logic / retained evidence
```

This boundary is intentionally smaller than a generic `ProviderPlugin` abstraction.

## Why this posture is useful now

Even if adapters are never extracted into separate packages, the seam provides current value:

- provider-specific evidence interpretation stays out of core control logic;
- provider SDK/types can remain local to the provider integration when live provider code is introduced;
- deterministic fixtures can test provider boundaries without unnecessary network/provider access;
- credential-bearing acquisition remains a separate bounded capability rather than leaking into consumers;
- policy, selection, qualification, runtime loading, and project validators remain outside provider integrations;
- future extraction becomes primarily packaging/release work instead of architecture surgery.

## Semantic boundaries are separate

Do not collapse every provider-related operation into one provider object merely because it talks to the same provider.

For Hugging Face, two different boundaries are now evidenced:

1. **Evidence normalization**
   - captured HF metadata -> normalized exact observation;
   - stdlib-only and offline;
   - implemented by the evidence adapter from #27 / PR #28.

2. **Provider-native materialization**
   - normalized exact observation -> verified HF native-cache snapshot handle;
   - may use the Hugging Face SDK and provider credentials at the acquisition boundary;
   - implemented downstream by #29 / PR #30 as a concrete HF-only module, not a generic materializer protocol.

The successful materialization implementation is evidence **against** inventing one all-purpose `ProviderPlugin`: the same provider has distinct operations with different dependencies, authority, side effects, and verification requirements.

## What the evidence adapter is allowed to own

The Hugging Face evidence adapter may:

- validate captured HF-specific evidence shape needed by the current observation contract;
- interpret HF repository revision/blob/LFS evidence;
- normalize that evidence into the versioned Foundry observation shape.

It does **not** own:

- Foundry selection policy;
- license/rights adjudication;
- project quality thresholds;
- qualification decisions;
- target selection/placement;
- runtime loading;
- live provider authentication;
- provider acquisition/materialization;
- plugin discovery or lifecycle.

## What the materializer is allowed to own

The concrete HF native materializer may:

- require an exact normalized HF observation;
- query/ensure the provider-native cache at the immutable revision;
- use native provider credential resolution when network acquisition is explicitly authorized;
- verify the returned provider-native handle against observation file/path/size evidence;
- return a machine-local handle plus a deterministic materialization receipt.

It does **not** own:

- model/capability selection;
- project runtime loading;
- target placement policy;
- project quality evaluation;
- qualification acceptance;
- artifact identity invention from local paths;
- a Foundry-owned blob warehouse.

## Follow-through result from the first live materializer

Downstream PR #30 exercised the current posture with a real provider-native path and did **not** require:

- Pluggy;
- Python entry-point discovery;
- a generic `ProviderMaterializer` protocol;
- a provider registry/lifecycle manager;
- a separate provider wheel;
- a Foundry blob store;
- consumer-visible credentials.

Its public run `33554409931` passed both deterministic materialization tests and a real exact-revision Hugging Face native-cache materialize-then-cache-hit smoke at product head `7380395be39934407565edb8717eb56afb77f728`.

Disposition: **CONFIRMS / NARROW remains correct.** Keep explicit, concrete provider-specific implementations until another real provider or materially different consumer forces a common abstraction.

## Explicit construction before discovery

For the MVP, provider use remains explicit in code. Installed code is not treated as automatically authorized or selected code.

Do not add entry-point scanning merely because Python supports it. If future evidence justifies separately distributed wheels, Python package entry points and/or a mature hook library can be evaluated then without changing the semantic contract first.

## Packaging is not sandboxing

A separately distributed Python wheel is a dependency/deployment capability boundary, not a security sandbox. Loading third-party Python code into the Foundry process gives it that process's effective authority.

If a future provider integration needs hostile/untrusted isolation, use a real process/container/RPC/credential boundary rather than describing Python plugin packaging as isolation.

## Extraction / common-interface gate

Do not extract a provider integration into a separately distributed wheel, or promote a provider-specific operation into a generic public interface, until:

1. at least a **second real implementation has exercised the same semantic boundary**; and
2. one or more material extraction/common-interface triggers exist.

The HF evidence adapter plus the HF materializer do **not** count as two implementations of one boundary; they are two different boundaries for one provider.

Material triggers include:

- independent release cadence;
- substantial provider-exclusive dependency tree;
- dependency conflict with core or another integration;
- deployments that deliberately omit the provider integration;
- different maintenance ownership;
- provider-specific churn that should not force core releases;
- demonstrated independent reuse;
- repeated structural duplication across two real providers for the same operation.

If a second implementation does not fit naturally, revise the in-tree seam. Do not preserve a premature public plugin API for compatibility's sake.

## Namespace/API posture

The current `tools/provider_adapters/` package is an internal implementation location, not a promised public plugin API. The fact that the concrete HF materializer currently lives beside the evidence adapter does not by itself establish a common interface.

Do not rename/repackage solely for taxonomy. Revisit package boundaries when a second provider or extraction trigger supplies evidence that the current layout creates real coupling or dependency cost.

## Deferred until the gate is earned

- Pluggy or another plugin manager;
- Python entry-point discovery;
- separately versioned provider wheels/repos;
- general plugin lifecycle/version negotiation;
- provider auto-discovery;
- generic materializer/provider registries;
- package templates/marketplace concepts;
- permission manifests presented as sandbox controls;
- speculative runtime/target/representation plugin families.

## Relationship to the MVP critical path

This posture does **not** add a new critical-path stage. It constrains implementation already required for the first HF consumer:

```text
exact HF evidence
  → in-tree HF evidence adapter
  → normalized exact identity
  → concrete HF native materialization
  → verified local handle
  → desktop-ui-cv local-handle runtime seam
  → project-owned qualification
```

The first consumer remains the architecture falsification mechanism. This posture is successful while it keeps the current path small, explicit, independently verifiable, and easy to revise without operating a plugin ecosystem.