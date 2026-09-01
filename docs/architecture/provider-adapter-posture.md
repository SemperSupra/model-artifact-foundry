# Provider adapter posture — extraction-ready without plugin infrastructure

Status: current architectural posture for the identity-first MVP.

## Decision

Use **narrow in-tree provider adapters** where a provider-specific boundary is already proven. Do not add a general plugin system, automatic discovery, or separately distributed provider wheels to the MVP critical path.

For the current Hugging Face slice, the proven boundary is:

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
- provider SDK/types can remain local to the adapter when live provider code is introduced;
- deterministic fixtures can test the provider boundary without network/provider access;
- credential-bearing acquisition can remain a separate bounded interface rather than leaking into consumers;
- policy, selection, qualification, and project validators remain outside provider adapters;
- future extraction becomes primarily packaging/release work instead of architecture surgery.

## What the current adapter is allowed to own

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
- acquisition/materialization in this increment;
- plugin discovery or lifecycle.

## Explicit construction before discovery

For the MVP, provider use remains explicit in code. Installed code is not treated as automatically authorized or selected code.

Do not add entry-point scanning merely because Python supports it. If future evidence justifies separately distributed wheels, Python package entry points and/or a mature hook library can be evaluated then without changing the semantic adapter contract first.

## Packaging is not sandboxing

A separately distributed Python wheel is a dependency/deployment capability boundary, not a security sandbox. Loading third-party Python code into the Foundry process gives it that process's effective authority.

If a future provider integration needs hostile/untrusted isolation, use a real process/container/RPC/credential boundary rather than describing Python plugin packaging as isolation.

## Extraction gate

Do not extract a provider adapter into a separately distributed wheel until:

1. at least a **second real implementation** has exercised the same semantic boundary; and
2. one or more material extraction triggers exist.

Material triggers include:

- independent release cadence;
- substantial provider-exclusive dependency tree;
- dependency conflict with core or another adapter;
- deployments that deliberately omit the provider integration;
- different maintenance ownership;
- provider-specific churn that should not force core releases;
- demonstrated independent reuse.

If the second implementation does not fit naturally, revise the in-tree seam. Do not preserve a premature public plugin API for compatibility's sake.

## Deferred until the extraction gate

- Pluggy or another plugin manager;
- Python entry-point discovery;
- separately versioned provider wheels/repos;
- general plugin lifecycle/version negotiation;
- provider auto-discovery;
- package templates/marketplace concepts;
- permission manifests presented as sandbox controls;
- speculative runtime/target/representation plugin families.

## Relationship to the MVP critical path

This posture does **not** add a new critical-path stage. It is a structural constraint on implementation already required for the first HF consumer:

```text
exact HF evidence
  → in-tree HF adapter
  → normalized exact identity
  → provider-native materialization (future bounded increment)
  → verified local handle
  → desktop-ui-cv qualification
```

The first consumer remains the architecture falsification mechanism. The adapter posture is successful if it makes the current path cleaner and later extraction cheap without increasing the number of systems that must be operated to reach the MVP.
