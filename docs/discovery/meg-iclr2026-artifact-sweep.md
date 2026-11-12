# MeG ICLR 2026 — official artifact recovery and Foundry admission

**Corrected on November 12, 2026.** Discovery authority: [Foundry private #35](https://github.com/SemperSupra/model-artifact-foundry-private/issues/35). Scientific replication authority: [Model Mechanisms private #5](https://github.com/SemperSupra/model-mechanisms-private/issues/5).  
**Machine-readable source inventory:** [artifacts.json](../../discovery/meg-iclr2026/artifacts.json).

## Critical correction to the original GitHub-only sweep

The official [ICLR 2026 MeG proceedings](https://proceedings.iclr.cc/paper_files/paper/2026/hash/7926a9c34166da5a6a681cc0fe6d8a28-Abstract-Conference.html) link an author-associated [supplementary ZIP](https://proceedings.iclr.cc/paper_files/paper/2026/file/7926a9c34166da5a6a681cc0fe6d8a28-Supplemental-Conference.zip). It contains two nested ZIPs: an approximately 100 KB code archive and an approximately 81 MB **data** archive. The absence of these data files from the authors' GitHub tree did **not** mean they were unpublished.

The new public [Model Mechanisms archive audit](https://github.com/SemperSupra/model-mechanisms/actions/runs/43210713738) used only free public GitHub Actions, and safely inspected and SHA-256-hashed ZIP members **without extracting, executing or redistributing any third-party code/data**.

| Publisher artifact | Verified evidence |
| --- | --- |
| Official outer ZIP | SHA256 `d8abdd06a77318d0af5f6f3414092eafe3b29a3fe10eb890704d6c237c760d71`, 81,010,254 compressed bytes |
| Nested `code_for_our_MeG.zip` | SHA256 `5b31e870127b90d2fa1a5281b58a29a16816cd59c022b22689dc597726632b9b`; 63 code/config/readme members |
| Nested `data_for_our_MeG.zip` | SHA256 `10f0cad94529f9d1522a34dad9379e6f7e15ea51f9500180fe4f892edffde088`; 18 data/prompt/readme members, 453,026,585 uncompressed bytes |

### Original author-associated datasets now located and file-hashed

The nested publisher data archive includes these named files with exact member sizes and SHA256 (full inventory in the JSON and Actions evidence):

| Original path under `data_for_our_MeG/` | Size | File SHA-256 prefix |
| --- | ---: | --- |
| `edit_data/phi2_zsre_edit.json` | 20,357,962 B | `100fa2b28e9e` |
| `edit_data/phi2_cf_edit.json` | 41,287,967 B | `34c9a0f9f65f` |
| `new_split_data/zsre_mend_eval_new_rephrase.json` | 22,541,146 B | `46be35aa7657` |
| `new_split_data/zsre_for_bert_train.json` | 3,733,310 B | `438dc2f1c98a` |
| `new_split_data/multi_counterfact_new_id.json` | 49,980,934 B | `f36ac1453742` |
| `train_familiar/zsre_phi2_fake_id_class.json` | 12,071,586 B | `2649173060b8` |
| `train_familiar/cf_fake_id_class.json` | 24,171,877 B | `b1b60bbe3a31` |
| `raw_data/zsre_mend_train_10000.json` | 5,277,557 B | `640ec98a583f` |
| `raw_data/rephrase.prompt` | 2,005 B | `707fd63436ee` |

Also included: raw `multi_counterfact.json`, `zsre_mend_eval.json`, `zsre_mend_train.json`; `new_split_data/zsre_mend_eval_new.json`, `zsre_train_new.json`; and GPT-J-specific edit/familiarity datasets. These publisher-attested data are better source candidates for **faithful stage-zero reconstruction** than third-party EasyEdit mirrors. Their exact member SHA-256 and source hierarchy are recorded in the JSON and CI audit receipts.

**A path mismatch remains:** the upstream paraphrase-generation script references `get_rephrase.prompt`, whereas the publisher archive contains `rephrase.prompt`. Treat that as a documented compatibility deviation until the actual prompt contents are compared; never silently rename and declare byte-identity.

### Trained components still not located

Neither official supplementary ZIP lists the original trained Phi-2/ZsRE text encoder, familiarity network, per-edit optimized stage-three neuron weight directory and success subset, or stage-four diffusion checkpoint. These **trained artifacts still require independent reconstruction or author release**. The authors publicly discussed releasing them in [GitHub Issue #1](https://github.com/RodeWayne/MeG-for-Knowledge-Editing/issues/1), but a verified downloadable checkpoint bundle is not yet established.

**Terminology:** data from official publisher archive are now `AUTHOR_SUPPLEMENT_SOURCE_VERIFIED`; *not* `FOUNDRY_ACQUIRED` or `REDISTRIBUTION_APPROVED`. New checkpoints produced by retraining are `RECONSTRUCTED_DERIVATIVE`, not `AUTHOR_CHECKPOINT_BYTES_RECOVERED`. Numeric reproduction against reported ICLR metrics is a third independent claim requiring executed evaluations and matched protocol.

## Foundry admission and legal gates

1. **Source intake:** use the publisher's exact outer ZIP URL/digest, inner ZIP digest and individual member SHA-256 values in a reviewed **source-local** acquisition plan. The official source is downloadable, but no publisher archive bytes were retained by this repository or published to GHCR.
2. **Rights review:** official conference hosting establishes authenticity but not blanket commercial redistribution or OCI mirror rights. Original author GitHub code has no verified top-level LICENSE. Decide benchmark dataset and authored prompt rights before any public Foundry publication; if uncertain, restrict to authorized pull-through/private-only local acquisition with no public mirror.
3. **Integrity:** independently re-fetch in a disposable isolated resource, assert outer and inner digests, verify each member path/hash; never execute embedded Python, unpickle checkpoint files, or silently add unlicensed data to a public PR.
4. **Pretrained backbones:** [Phi-2](https://huggingface.co/microsoft/phi-2) MIT and [BERT-base-uncased](https://huggingface.co/google-bert/bert-base-uncased) Apache-2.0 are separately revision-pinned candidates pending Transformers/safetensors family validator and own license notice checks. The exact historical author-used model revisions still need checking. [GLM-4-9B-Chat](https://huggingface.co/zai-org/glm-4-9b-chat) is custom licensed and its original script calls remote model code; **do not redistribute/execute it by default**.
5. **Scientific pipeline:** use the publisher's stage-zero originals, retain their digests; retrain stage1–4 with immutable environment/model/seed receipts under Model Mechanisms authority. No full MeG training or paper-result reproduction has been performed by these discovery tests.

## Reproducibility and external review

The ICLR paper was accepted, but no independently verified end-to-end replication was found in targeted searches. A fork with exactly the same Git commit is not a replication. A Chinese-language [technical review](https://m0rtzz.github.io/paper-notes/ICLR2026/llm_nlp/massive_editing_for_large_language_models_based_on_dynamic_weight_generation/) views the architecture favorably but notes training cost and scaling limitations; it did not reproduce scores. The official [OpenReview forum](https://openreview.net/forum?id=GJfWu4BjoI) was identified, but reviewer-specific text/ratings were not accessible via automated browsing and are not asserted here.

Relevant independent competing work: [EAMET](https://proceedings.iclr.cc/paper_files/paper/2026/hash/3d226fb8fbd6ee6ec70d0427f1319707-Abstract-Conference.html) highlights context-rich and same-subject multiple-edit failure modes. [Towards a Principled Evaluation of Knowledge Editors](https://arxiv.org/abs/2507.05937) highlights scoring-protocol sensitivity. These are **not** direct replications of MeG and must not be presented as such.

**DLE:** Exact archive/member hashes, source identity, original-vs-derived distinctions, explicit rights and model-checkpoint blockers. No unreviewed approval, ingestion or scientific promotion.
