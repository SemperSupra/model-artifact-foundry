# Hugging Face native materialization — first-consumer MVP

Status: bounded implementation for issue #29, stacked on the exact HF observation/provider-adapter work.

## Decision

The normal Hugging Face acquisition path uses `huggingface_hub.snapshot_download()` with the **full immutable provider revision** and the provider-native shared cache. Foundry does not copy the snapshot into a separate warehouse merely to manage it.

The first call is always cache-only. Network acquisition is opt-in. A returned local filesystem path is a machine-local handle, **not artifact identity**; durable identity remains the normalized provider observation's exact repository commit plus its file evidence.

This increment is deliberately Hugging Face-specific. No generic provider materializer protocol is introduced until a second real implementation demonstrates that the same boundary exists.

## Current Hub API basis

As checked for this increment against current Hugging Face Hub documentation and `huggingface_hub` 1.29.0:

- `snapshot_download(repo_id=..., revision=<full commit>)` downloads an exact repository snapshot;
- the normal path uses the Hub cache rather than `local_dir`;
- `local_files_only=True` prevents download and resolves only a complete cached snapshot;
- missing/incomplete offline snapshots raise the Hub's local-entry/incomplete-snapshot error family;
- repeated exact-revision downloads benefit from the native cache.

The public smoke workflow pins `huggingface_hub==1.29.0` so evidence records the client behavior actually exercised rather than silently following a moving dependency.

## Flow

```text
normalized exact HF observation
        |
        v
validate provider + full source revision
        |
        v
snapshot_download(local_files_only=True)
        |
   +----+----+
   |         |
 complete   cache miss
   |         |
   |      allow_network?
   |       /        \
   |     no          yes
   |     |            |
   | explicit     snapshot_download(
   | cache miss    exact revision,
   |               local_files_only=False)
   |                   |
   +-------------------+
              |
              v
verify expected safe paths and sizes
              |
              v
HF native local handle + receipt
```

## Verification strength

The materializer verifies:

- provider is Hugging Face;
- source revision is a full 40-hex commit and observation identity strength is `repository_commit`;
- observation paths are relative/safe and non-duplicated;
- returned handle exists and is a directory;
- every file listed by the observation exists in that snapshot;
- file sizes match where the observation has a size.

It deliberately does **not** re-hash multi-GB LFS weights on every ensure operation and does not invent a whole-model content digest. The normalized provider observation retains provider-side Git/LFS evidence; the materialization receipt binds back to that observation with a canonical SHA-256 digest of the observation JSON.

Hugging Face native snapshots may contain symlinks into the Hub blob cache. Verification therefore checks safe relative snapshot names and their resulting file/size rather than incorrectly requiring symlink targets to remain physically below the snapshot directory.

## Credential boundary

No token string is accepted on the CLI and no token field is emitted in receipts. When real gated/private access is eventually authorized, the Hugging Face client may use its native credential resolution at this Foundry acquisition boundary. The `desktop-ui-cv` runtime must not receive those credentials.

## Public live smoke

The workflow uses public model `optimum-intel-internal-testing/tiny-random-vit` at immutable revision:

`d4ddddabea80a187f3adce69c76ab017d2cf9a86`

The repository is roughly 1 MB and `config.json` at that revision is 605 bytes. The smoke starts with a fresh temporary Hub cache, materializes once with explicit network permission, then repeats cache-only and requires `cache_hit`. No model is stored in Git or uploaded as an Actions artifact.

This smoke validates Hub/native-cache mechanics only. It does not qualify the tiny model or imply anything about KV-Ground quality/runtime behavior.

## R4

- **Reproducible:** pinned exact revision, pinned Hub client for live evidence, deterministic offline tests.
- **Repeatable:** second ensure of an exact complete snapshot is a cache hit/no-op.
- **Reversible:** no consumer/runtime dependency is changed here.
- **Idempotent:** provider-native cache ownership prevents duplicate Foundry copies.

## Non-goals

No KV-Ground download in CI, generic acquisition framework, plugin system, Civitai/Ollama/OpenRouter materialization, runtime loading, target planning, project validator, or release/publication work is introduced.


## R009 ownership and source-hardening reconciliation — 2026-11-16

**Canonical Hugging Face-native download owner:** this PR's `tools/provider_adapters/hf_native.py` and `tools/materialize_hf_observation.py` are the reusable cache-first provider-native path. The newer generic Go source preflight (draft [#80](https://github.com/SemperSupra/model-artifact-foundry/pull/80)) must not become a second HF cache/credentials/download authority. Its useful digest/byte verification and generic HTTPS provenance controls should be reconciled through reviewed contracts, with non-HF stacked consumers preserved. No unreviewed code merge is implied.

**Exact-revision file selection:** materialization now supplies `allow_patterns` from the bounded 1–64 observed, normalized relative file paths to `snapshot_download`. It never silently harvests all unrelated files when a small model component set was requested. New negative controls reject aliased paths, invalid owner/repository locators, external symlink targets and external hardlink substitutes; provider-native links into bounded HF blob-cache roots are supported. This is structural/path safety, not full content authentication: the independent per-file hash and immutable content-manifest work remains in draft [#70](https://github.com/SemperSupra/model-artifact-foundry/pull/70) / stacked [#71](https://github.com/SemperSupra/model-artifact-foundry/pull/71).

**Credentials:** the native `huggingface_hub` client uses the calling environment's already authorized credential resolution; this source accepts or prints no token. The linked GitHub integration does not expose a way to inspect currently configured Actions secret values or a user's local Hugging Face login state. Public Actions smoke uses an ungated public fixture without assuming a token exists. Private gated access state remains under private Foundry #6 and user-granted upstream terms; this PR does not configure or grant it.

**Verified cloud execution:** [run #43857626029](https://github.com/SemperSupra/model-artifact-foundry/actions/runs/43857626029) passed deterministic and live cache-first smoke after path/link hardening; [run #43858037615](https://github.com/SemperSupra/model-artifact-foundry/actions/runs/43858037615) passed **20/20 pytest tests** and live exact-revision selected-file native materialization/cache-hit, source commit `89c7a10a0b5e7d65e12f54af90aa2ea5c3ebd642`. Provider observation and Faster Whisper regressions attached to the same commit also passed. No Thai-specific model bytes or vocal quality tested and no authorized artifact was promoted.

**Remaining:** independent code/rights review, order this stacked PR after provider observation and adapter posture branches, reconcile #70/#71 native no-copy hash verification, separately prove any locally configured auth profile and exact gated consent on an admitted private actor, then test specific consumer audio models without exposing private selection on public runner.
