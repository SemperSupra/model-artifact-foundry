# MeG (ICLR 2026): global multilingual artifact discovery and Foundry admission

**As-of:** 2026-11-12. **Disposition:** discovery-only; no artifact bytes downloaded or mirrored, no OCI digest, no approved catalog entry.  
**Foundry decision:** [private #35](https://github.com/SemperSupra/model-artifact-foundry-private/issues/35).  
**Research authority:** [Model Mechanisms](https://github.com/SemperSupra/model-mechanisms-private/issues/1) and [original Phi-2 MeG reproduction](https://github.com/SemperSupra/latent-reasoning-private/issues/5).  
**Machine-readable inventory:** [artifacts.json](../../discovery/meg-iclr2026/artifacts.json).

## Finding: raw benchmark and base-model sources are located; original MeG output artifacts are not

The exact [MeG author source revision](https://github.com/RodeWayne/MeG-for-Knowledge-Editing/tree/9fa8ae10cf33c82dd2200057f70dfcb73388cd74) defines all four computational stages but contains no original trained weights/derived data distribution, root LICENSE or GitHub Releases. On [author GitHub issue #1](https://github.com/RodeWayne/MeG-for-Knowledge-Editing/issues/1), Hugging Face requested that the authors publish the trained encoder, familiarity network, diffusion generator, and pseudo-knowledge dataset. The author publicly agreed April 12 2026 but the checked official source has not yet supplied them.

This is a **negative public-indexing observation**, not proof that files do not exist on unindexed/private accounts or a claim that all languages or websites can be exhausted. Searches used exact filenames, the paper title/translations, authors, release discussions, and targeted indexing of Hugging Face, ModelScope, GitHub and forks, ICLR/OpenReview, Zenodo, Kaggle, papers and Chinese/Japanese/Korean/German/English-language material. Translated paper abstracts and third-party summaries are not original checkpoints. Any future mirror requires author authenticity, file hash comparison, and license evidence.

## Recoverable original prerequisites

| Artifact / expected use | Source (verified listing) | Exact identity | License decision |
| --- | --- | --- | --- |
| Phi-2 backbone for all trained edits | [Microsoft Phi-2](https://huggingface.co/microsoft/phi-2) | HF commit `810d367871c1d460086d9f82db8696f2e0a0fcd0`; historical author-used revision unknown | MIT on model card, **Foundry candidate review** once safetensors/transformers validator exists |
| BERT base for MeG's encoder/familiarity | [google-bert/bert-base-uncased](https://huggingface.co/google-bert/bert-base-uncased) | HF commit `86b5e0934494bd15c9632b12f734a8a67f723594`; historical author-used revision unknown | Apache-2.0 on model card, **Foundry candidate review** |
| GLM-4-9B-Chat author ZsRE paraphrase model | [zai-org/glm-4-9b-chat](https://huggingface.co/zai-org/glm-4-9b-chat) | Author script names `THUDM/glm-4-9b-chat`, model revision not pinned | **Custom GLM-4 license** and script's `trust_remote_code=True`: HOLD for public redistribution and executable code |
| ZsRE original eval | [ROME/Bau Lab](https://rome.baulab.info/data/dsets/zsre_mend_eval.json) | URL, not immutable SHA yet | Dataset rights unverified: HOLD before mirror |
| ZsRE original train | [ROME/Bau Lab](https://rome.baulab.info/data/dsets/zsre_mend_train.json) | URL, not immutable SHA yet | Dataset rights unverified: HOLD before mirror |
| MultiCounterFact original | [ROME/Bau Lab](https://rome.baulab.info/data/dsets/multi_counterfact.json) | URL, not immutable SHA yet | Dataset rights unverified: HOLD before mirror |
| ZsRE subset `zsre_mend_train_10000.json` | [EasyEdit-associated Hugging Face dataset](https://huggingface.co/datasets/wangzn2001/data/tree/main/data/zsre) | HF commit `0f3666b7646e47a44c636667b3aa6e18a04ea33b` | Dataset license and matching author file hash unverified: HOLD |

**Do not substitute** `counterfact.json` for `multi_counterfact.json`. Do not assume the Hugging Face ZsRE subset is byte-for-byte equal to the one the MeG authors used.

The author source itself has no found top-level license. Its public availability **does not grant a general right** to mirror, modify or redistribute the authors' code or unpublished trained outputs. We can inspect metadata and link to exact Git commits while permission is unresolved.

## Author-derived outputs that still need acquisition or explicit reconstruction

| Stage | Required exact author output or information | Key blocker |
| --- | --- | --- |
| Data split | `new_split_data/zsre_mend_eval_new_rephrase.json`, `zsre_for_bert_train.json` | LLM-generated paraphrases; original prompt `raw_data/get_rephrase.prompt` not included |
| Edit-data selection | `edit_data/phi2_zsre_edit.json`, `phi2_cf_edit.json` | Depends on exact Phi-2 model revision and inference outputs |
| Familiarity labels | `train_familiar/zsre_phi2_fake_id_class.json`, `cf_fake_id_class.json` | Upstream `add_fake_id_for_familiar.py` uses unseeded Python `random.randint` |
| Text-encoder weights | `checkpoints_trained_bert/bert_phi2_zsre/model_epoch_100.pth` | Exact trained checkpoint absent |
| Familiarity weights | Phi-2/ZsRE trained familiarity network | Exact serialized checkpoint/path to establish from training source |
| Per-edit teachers | `data_paras/phi2_zsre_10000/paras` and `train_success_data_prompt_1_6_neuron_1_layer_29.json` | Original optimized neuron tensors and successful subset/order absent |
| Diffusion generator | `results/029_20250518224950/checkpoints/model_epoch_all_30000.pth` | Original diffusion weights absent; example config includes mismatched data_size references |

For CounterFact, the author-provided `data/add_id_for_cf.py` deterministically adds IDs to the original `multi_counterfact.json`. That transformation can be rebuilt with exact source hash, raw input SHA and output hash once dataset license and raw files are checked. It is **a derived reconstruction**, not a claim to have recovered the author's actual serialized output file.

Similarly, `data/get_new_zsre.py` has a deterministic selection/dedup procedure **given identical input file bytes and order**. It cannot establish fidelity if the original `zsre_mend_train_10000.json` differs.

## Explicit acquisition plan by Foundry class

1. **Ready for source-declaration review:** Phi-2 (MIT) and BERT (Apache-2.0) exact HF revisions. Extend/qualify a bounded, non-executing `transformers/safetensors` family validator first; review original model notices and license file, include tokenizer/config, then candidate artifact/pullback, approval and digest-pinned hydration. Historical author checkpoint revision remains unknown: `CURRENT_APPROXIMATION`, not `AUTHOR_EXACT`.
2. **Hold until rights documented:** raw ROME benchmarks and EasyEdit ZsRE 10K. Fetch exact bytes only under an authorized research source-inspection path, compute SHA-256 and size and compare alternate sources; do not automatically publish them in public GHCR when rights unclear.
3. **Restricted separate path:** GLM-4-9B-Chat; license is custom and the author's script uses remote code. Foundry public redistribution is ineligible by default. A user-authorized, isolated local-only pathway, or independently validated alternate paraphrase generator, must be a separate research decision and is not a faithful author artifact substitute.
4. **Request from authors:** original complete text encoder, familiarity, stage-3 pseudo-knowledge/teacher tensors and success subsets, stage-4 diffusion checkpoint, the missing prompt, original dataset split/selection hashes, original Phi-2/BERT/GLM revision IDs, random seeds and redistribution permissions. For PyTorch `.pth` weights, use isolated, non-executing format inspection/conversion and explicit untrusted-pickle refusal; never blindly `torch.load` untrusted weights in Foundry.
5. **Independently reconstructed fallback:** if original weights are unavailable, run the frozen author training procedure only in a separate reviewed scientific workcell with reproducible RNG/environment and new derived artifact identities; report `RECONSTRUCTED_NOT_AUTHOR_IDENTICAL` and retain the full deviation ledger.

## Foundry policy

The current public `schemas/source-declaration.schema.json` is for redistributable, allowlisted sources, and `candidate-manifest` needs real hashes, validator evidence and an OCI digest. **This discovery report is intentionally neither schema**; it lives under `discovery/` with `bytes_acquired=false`, `oci_published=false` and `promoted=false` assertions. No active source declaration, automatic harvesting workflow, package publication, privileged credential, or approved catalog mutation is authorized by this document.

Author permission and original sources outrank third-party reuploads. Source/format integrity is not scientific fidelity. Maintain DLE: Durable exact source/file/dataset identities; Legible availability/rights/reconstruction distinctions; Executable deterministic reviewed acquisition and validation gates.
