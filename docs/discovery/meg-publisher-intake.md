# MeG publisher original data — preharvest plan (rights hold)

**Source:** official ICLR 2026 [supplement](https://proceedings.iclr.cc/paper_files/paper/2026/file/7926a9c34166da5a6a681cc0fe6d8a28-Supplemental-Conference.zip) (outer SHA256 `d8abdd06a77318d0af5f6f3414092eafe3b29a3fe10eb890704d6c237c760d71`).  
**Author-associated published nested archive:** `code_and_data_for_our_MeG/data_for_our_MeG.zip`, SHA256 `10f0cad94529f9d1522a34dad9379e6f7e15ea51f9500180fe4f892edffde088`.  
**Source metadata:** [exact 18-member manifest](../../discovery/meg-iclr2026/publisher-intake-plan.json), 453,026,585 uncompressed bytes, separately independently verified by [Model Mechanisms PR #15](https://github.com/SemperSupra/model-mechanisms/pull/15).

This is a **source-location and identity plan**, not an authorized acquisition or completed Model Artifact Foundry product. All 18 SHA256 member digests are frozen for future comparisons. Exact author-associated datasets now exist in the published ICLR archive: we should prefer them over regenerated stage-zero data for faithful scientific reconstruction.

**Rights hold:** the fact that the conference publisher hosts original supplementary data establishes source authenticity but does not by itself authorize copying the bundle to a public OCI repository. Source reuse terms, notices, licenses and the original benchmark data's restrictions must be independently reviewed. This plan explicitly sets every consumer-hydration, public redistribution, OCI publication, approval and acquisition indicator to **false**. The only permitted CI behavior is source-only metadata validation; it does **not** call a provider or download the ZIP.

**Future intake route (requires explicit review):** verify the unchanged official HTTPS source, outer and nested SHA256, individual ZIP members/expected sizes, and file provenance; record acquisition transaction in Foundry's existing artifact lifecycle with a rights-approved private/public disposition and a model/data family validator. Failed or ambiguous licenses remain HOLD. Do not treat any `.pth` as trusted; none of the inspected original supplementary data members is a trained model checkpoint. Do not execute unlicensed author Python to perform hydration.

**Research handoff:** [Model Mechanisms private scientific #5](https://github.com/SemperSupra/model-mechanisms-private/issues/5) owns experimentation; [Foundry private #35](https://github.com/SemperSupra/model-artifact-foundry-private/issues/35) owns acquisition and legal disposition. Both projects should consume one immutable artifact identity once rights and validation are resolved. Do not duplicate schedulers or catalogs.

All output is human-readable and machine-validatable while preserving GitHub DLE authority. This task does not authorize merging this PR or changing repository settings.
