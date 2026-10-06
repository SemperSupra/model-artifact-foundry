# Local Capability-Provider Control-Plane RDTE

This PoC qualifies existing open-source control planes for a local, multimodal
capability provider. It is intentionally host-agnostic and contains no private
machine inventory.

## Candidates

| Candidate | Exact identity | Lane |
|---|---|---|
| llama-swap | v262 / `079c35ae82fb2816d319f7bd16936675597b262d` | released binary + deterministic mock model processes |
| LocalAI | v4.11.0 / `58830f7ac508845a6f4efa32cfca06af422d4d82` | upstream source + upstream mock backend/e2e suites |

## Claims this GHA PoC may establish

The llama-swap lane checks, as black-box behavior:

- selector-backed virtual model IDs;
- automatic child-backend cold start;
- warm-target selector preference;
- matrix-driven eviction when a mutually-exclusive model is requested;
- TTL-driven idle unload;
- OpenAI-compatible request proxying.

The LocalAI lane reuses the exact-release upstream mock backend and targeted
e2e suites to check:

- multimodal API/capability behavior without real model weights;
- failover-chain behavior;
- CPU-only CI testability of the control plane.

The final workflow step emits a machine-readable JSON receipt and a GitHub step
summary. Both candidate lanes run even if the other fails, preserving causal
isolation.

## Claims this PoC does *not* establish

GitHub-hosted Linux runners cannot establish Apple Silicon/Metal performance,
unified-memory pressure behavior, real model quality, model cold-start latency
on a target host, or hardware-specific backend compatibility. Those remain HIL
gates after a control plane is selected.

## Decision rule

Prefer the least-custom candidate that earns the required control-plane
primitives. Add a thin compatibility/capability membrane only for gaps proven
by evidence; do not build a new supervisor by default.
