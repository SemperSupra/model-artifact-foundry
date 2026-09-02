# Issue #39 — external KV-Ground compatibility smoke

## Purpose

Use opportunistic third-party/shared GPU capacity to answer one bounded public question before the authoritative local target run:

> Does the exact KV-Ground artifact load and produce a structurally parseable GUI-grounding response through the legacy-equivalent loader, and if not, does the model's public evaluation loader succeed in the same environment?

This is uncertainty reduction, not target qualification. Failure to obtain shared GPU access does not block the MVP critical path.

## Frozen public subject

- Hugging Face repository: `vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315`
- exact corrected-weight revision: `fe7563292bb52ab6c235fc3c87157e6a14017479`
- fixture: generated synthetic 1000x1000 GUI image with a `TARGET` control and a decoy control
- instruction: `Click the TARGET button.`

The corrected-weight revision is deliberately immutable even though later repository commits changed non-weight evidence. Do not replace it with mutable `main` merely because the provider has advanced.

## Why two loader paths

`desktop-ui-cv` Increment 0 characterized the legacy sidecar as using `AutoModelForCausalLM` with `trust_remote_code=True`. No real model-backed evidence has yet proved that loader class works for the exact current KV-Ground subject.

The public `vocaela/kv-ground` evaluation code uses `AutoModelForImageTextToText` and `AutoProcessor`. Its published requirements pin a compatibility reference environment including PyTorch 2.8.0, Transformers 4.57.3, and Accelerate 1.12.0.

The smoke therefore keeps the two facts separate instead of silently modernizing the private runtime.

## Harness

`experiments/kv_ground_external_smoke.py` has three relevant modes:

```bash
# No ML dependencies, provider access, model download, or GPU required.
python experiments/kv_ground_external_smoke.py --contract-only --output contract.json

# Run first on an authorized external/shared CUDA GPU.
python experiments/kv_ground_external_smoke.py \
  --loader legacy_equivalent \
  --output legacy.json

# Run only if needed to distinguish a legacy-loader problem from a broader failure.
python experiments/kv_ground_external_smoke.py \
  --loader provider_eval \
  --output provider.json
```

The GPU environment should be as close as practical to the model's published evaluation environment. Do not turn environment adaptation into a new platform project. In particular, optional provider benchmark dependencies such as FlashAttention are not required merely to ask this compatibility question unless runtime evidence proves they are necessary.

## Execution order and interpretation

1. Run `legacy_equivalent`.
2. If it loads, infers, and emits a structurally parseable tool call, retain the receipt. The legacy loader class has **not been falsified** by this external environment; this does not prove the target runtime.
3. If `legacy_equivalent` fails, run `provider_eval` under the same material environment.
4. Classify the result:

| Legacy-equivalent | Provider-eval | Interpretation |
| --- | --- | --- |
| PASS | not required | Preserve the current #35 loader class pending authoritative target evidence. |
| FAIL | PASS | Bounded runtime-loader defect discovered; fix separately rather than hiding modernization inside the local-handle seam. |
| FAIL | FAIL | External environment/model compatibility evidence; proceed to the authoritative local target without manufacturing a pass. |

A provider-eval run after a legacy PASS is optional and is not required for the MVP.

## Receipt boundary

The result receipt records only public/synthetic execution facts:

- exact model repository/revision;
- selected loader path;
- Python/platform and relevant package versions;
- CUDA availability/runtime/device name when exposed;
- processor/model load and inference elapsed time;
- raw model output for the synthetic fixture;
- structural parser result and whether the point lands in the synthetic target box;
- bounded exception type/message on failure.

Review a receipt before publishing it if an external environment returns unexpected host-specific text in an exception. The harness intentionally does not retain tracebacks.

## Explicit non-qualification

This experiment cannot establish:

- private `desktop-ui-cv` holdout quality;
- Windows/local target compatibility;
- target peak VRAM;
- target model-load or p95 grounding latency;
- a Foundry qualification subject or retained qualified resolution.

Those remain on the authoritative first-consumer path:

`exact identity -> provider-native materialization -> frozen request/target/envelope -> local-handle seam -> private holdout + target resource measurement -> qualification receipt -> equivalent deterministic repeat -> one-material-change falsification -> GO/NARROW/KILL`.

## Resource policy

Use the lowest-friction available shared GPU. Hugging Face ZeroGPU, Colab, Kaggle, or another authorized environment are acceptable execution venues, but none is an architectural dependency. Stop external adaptation when platform friction costs more than the uncertainty this one experiment removes.

The repository CI for this increment validates only the harness contract and repeatability with the Python standard library. It does not download KV-Ground or request a GPU.
