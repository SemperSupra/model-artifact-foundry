# Received local adoption receipt integrity (offline, nonpublishing)

Existing Model Artifact Foundry local adoption and the draft native-HF
adapter generate deterministic `content-manifest` identity from actual bytes.
A downstream consumer may nevertheless receive a forged/truncated JSON
receipt with an unchanged `artifact_identity.digest`.

`tools/verify_local_adoption_receipt.py --receipt <receipt.json>
--expected-digest sha256:<64-hex>` independently validates that every
canonical relative file record, source and logical ID actually hashes
to the **authorized** expected Foundry digest, and that public publication
remains prohibited. The script never downloads or accesses model bytes.

**This is only receipt integrity.** Before validation, the actor must
rehash the *current* local cache using the appropriate Foundry adopter
(`adopt_hf_native_snapshot.py` or `adopt_local_artifact.py`).
A self-consistent stale receipt does not prove present model bytes.
The expected digest must come from independent DLE authority (not from the
same untrusted receipt). Approval of a particular use, rights,
distribution, runtime/device compatibility and model/output quality are
distinct policy and validation decisions.

No daemon, new cache, new model selection scheme or license verdict.
