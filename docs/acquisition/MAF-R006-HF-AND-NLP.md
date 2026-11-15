# R006 — Hugging Face / external publisher acquisition, Drive custody, multilingual NLP

2026-11-15. Source-only research implementation; no model weights, no consumer promotion, no private secrets, no model-quality claims.

## Current canonical boundaries

- Reuse existing Foundry source declaration, local adoption (`tools/adopt_local_artifact.py`), content-manifest identity, OCI catalog and hydration; **do not** create another authoritative artifact registry.
- The generic `tools/maf-acquire/` Go *transfer request preflight* is a **non-authoritative execution plan** that references the existing `foundry_logical_id` and independent `source_declaration_sha256`. It produces SHA-256 file witnesses only; it is not an OCI or Foundry canonical identity. The existing Foundry verification/adoption contract must run separately against actual accepted bytes.
- Auth/gating and operational provider instances remain under private Foundry issue #6. Public CI cannot receive private source, local host profile, tokens, Google Drive IDs or restricted selections. `CURRENT_TASK.md` gated artifact control and #70/#71 native HF cache adoption are separate from this generic public-only source preflight.

## Hugging Face acquisition

- Official Hugging Face Python Hub API `HfApi.model_info` exposes `sha`, `private`, `gated`, file `siblings`. Resolve a mutable `main` or tag **once** into exact commit ID, then pin every requested file; `HfApi.resolve_revision` may help. Metadata-only access does **not** demonstrate actual ability to download bytes.
- For selected, reviewed public source files, use `hf download <repo> <files...> --revision <40hex> --local-dir <isolateddir>` (or hf_hub_download / snapshot_download). Do **not** `hf download <model>` indiscriminately for large repos. Hugging Face transfers use Xet caches and metadata; avoid reimplementing the transfer engine. The CLI invocation in `tools/maf-acquire` uses `exec.CommandContext`, no shell interpolation or arbitrary executable upstream script.
- The public Go request **requires** public-ungated, policy-asserted independent review, exactly 40 lower-case hex HF commit, 64-hex expected file SHA, bounded 16-file and 8GiB aggregate budgets, safe relative paths, no pickle-like checkpoints, and candidate-only. It requires fresh empty staging, checks actual file size+SHA after CLI, and reports `STAGED_VERIFIED_NOT_PROMOTED`. A fake `license_evidence=independent-reviewed` field is *not* proof: the upstream license, training-data lineage and reviewer authenticity must be confirmed independently, before the actual request is approved. A missing file, wrong digest or inaccessible network is HOLD/WAIT, never successful adoption. The Go output is deliberately distinct from Foundry OCI/content-manifest identity.
- Note: `hf download --local-dir` may add `.cache/huggingface` metadata. Do not blindly adopt the entire download folder; use only the file records checked and the existing Foundry normalized-file adopter. For reuse avoid copying native HF caches: staged qualification may instead use the existing `#70` symlink-safe native adopter once merged and qualified.
- Authentication: Hugging Face official GitHub Action `huggingface/hub-sync` is for synchronization **to** HF Hub, not third-party weight downloads. Use `hf download` in public-safe PR CI or separate approved worker. HF Trusted Publishers/CI-CD identities offer OIDC short-lived tokens with read-only gated access for previously accepted user terms or repo-scoped private access. Credentials never enter public PR runners. Gated terms and consent remain attended.

## Non-HF model acquisition

- Existing Foundry declaration supports `github-release` and `https`. For approved publisher releases, record *both* tag/underlying git commit identity and every immutable asset SHA-256; changing assets under a tag must create new candidate bytes. GitHub Releases redirects to asset CDN; allowlist both source and permitted redirect hosts, and cap total bytes. Do not use GitHub release tag alone as byte identity. For direct HTTPS (including an academic institutional or vendor site), explicitly allowlist scheme/host, record source URL and response metadata separately from SHA256, block untrusted redirects and reject decompression bombs / unsafe deserializers. `FetchPinnedHTTPS` is a synthetic-tested transfer primitive for a preapproved HTTPS origin; CLI and actual publisher-specific credentials are **not** wired yet.
- Additional adapters for Ollama-native blobs, GHCR/OCI (ORAS), Civitai, GitHub Releases and institutional archives should *first* detect verified provider-native cache, then use permitted origin, verify digest, adopt via canonical Foundry identity, and only mirror if rights explicitly permit. Local/private Drive custody does not grant redistribution rights. No implicit cache copies on hit.

## Storage policy

- **Public eligible**: GHCR OCI package by immutable digest after independent rights/source/quality gates; Git catalog only metadata. Not all public HF weights qualify for redistribution.
- **Gated/nonredistributable**: authorized existing HF/Ollama/provider-native store, plus private exact content-manifest receipt and source-local handle. A private Drive pointer can be kept but do not upload source bytes unless source license/terms expressly permit private archival/transfers.
- **Private owner-held**: optionally store compact/small model bytes in verified Google Drive owner-only folder under an approved explicit custody manifest. Verify Drive `id`, `size`, `shared=false`, actual retrieved byte SHA256 *before* calling it `VERIFIED`. Large multi-GiB sharded models should remain in verified caches/OCI if rights allow; Drive may hold only manifests/receipts. Google Drive's available capacity, max individual file and upload resumability have NOT been checked; never promise large multi-GB upload.
- **Quarantine**: unknown provenance/rights, insecure archive or unsafe serialized checkpoint; keep untrusted files outside auto-loadable consumers and release catalogs.

## NLP routing and pronunciation

| locale / task | primary | comparative | risk / qualification |
|---|---|---|---|
| Thai words/sentences | PyThaiNLP `newmm` and sentence/Thai character clusters | AttaCut, DeepCut, Stanza Thai | dictionary segmentation != phonetic syllabification; preserve original UTF-8 and many-to-many spans |
| Thai romanization | PyThaiNLP `royin` **RTGS** | `thai2rom_onnx`, lookups | RTGS != IPA, often loses tone and vowel length; no label spoofing |
| Thai G2P/phonemic syllables | FastThaiG2P, native lexica | PyThaiNLP pronunciation and WangchanBERTa-derived context | independent gold all 5 tones, aspiration, vowel length, code switch |
| English syntax/NER | spaCy `en` trained packages | Stanza | CMUdict + G2P / eSpeak phonemizer for speech layer, not spaCy token IDs |
| German syntax/NER | spaCy `de`, Stanza | SoMaJo and morphological compounds | lexical compounds, noun capitalization, stress, Sie/du forms require phonetic and sociolinguistic tests |
| broader European/multilingual UD | Stanza, UDPipe families | spaCy where full trained package available | model/data licenses per version; `spacy.blank` is not trained model |
| JA/KO/ZH/AR | SudachiPy / MeCab-ko / jieba or pkuseg / CAMeL Tools | Stanza + language-specific systems | independent script and segmentation evaluation |
| model-specific subword tokens | pin Hugging Face tokenizer or SentencePiece model | ICU Unicode break and UAX29 grapheme | subwords != natural words or syllables; lossless text/source offset contract |

**Candidate qualification is per task and locale**, not one universal “best NLP library.” Real corpus/error and reuse license checks are separate from these source-only recommendations.

## Evidence / status

- Ran `go test ./...`, `go test -race ./...`, `go vet ./...`: **19 synthetic/offline tests** (including simulated official HF CLI, checksum tamper, directory controls, release locator, TLS synthetic HTTPS allowlisted host/redirect tests); verify actual count on exact commit.
- Networked HF/GH Release model bytes and real TTS NOT_RUN in this batch. No new approved catalog, code merge, package publication, model rights or user policy change.
- Private Foundry #6 and ShelfMark #82 / toolbox PR #2 stay DLE owners. Do not print private Drive IDs, model selections or host configurations into this public document.

## References

- https://huggingface.co/docs/huggingface_hub/guides/download
- https://huggingface.co/docs/hub/trusted-publishers
- https://huggingface.co/docs/hub/repositories-github-actions
- https://spacy.io/usage/models
- https://pythainlp.org/about/
- https://stanfordnlp.github.io/stanza/available_models.html
- https://github.com/pythainlp/attacut
