# Piper German Thorsten medium — structural TTS admission

This is the deliberately narrow structural-admission proof for the multimodal qualification program. It establishes reproducible artifact/runtime feasibility only; it does **not** establish speech quality or actor qualification.

## Result — validation passed

- logical artifact ID: `tts/piper/de-de-thorsten-medium`
- upstream repository: `rhasspy/piper-voices`
- exact upstream revision: `6249c8a9178e606f0de19227d5426e5dfaf9fc9e`
- validation run: `36055157072`
- validation head: `209dc618da59b6d17d7a6b3864e418ec729c1895`
- short-retention Actions artifact: `10831399586`
- artifact ZIP digest: `sha256:2142fddb8d422b4da4d14301b6f0fd280279bd3c557a9888909bbc70d36306d2`
- runtime: `piper-tts==1.8.0`, CPU
- observed repository license metadata: MIT
- training-dataset license observed in voice model card: CC0

Exact source-file evidence:

- `MODEL_CARD`
  - SHA-256: `5196b5ab0794e6056263a1f37c18bec407b61ac187529bee29d1c366871e5c9e`
  - size: 285 bytes
- `de_DE-thorsten-medium.onnx`
  - SHA-256: `7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819`
  - size: 63,201,294 bytes
- `de_DE-thorsten-medium.onnx.json`
  - SHA-256: `974adee790533adb273a1ac88f49027d2a1b8f0f2cf4905954a4791e79264e85`
  - size: 4,819 bytes

The exact revision reported:

- repository ID `rhasspy/piper-voices`;
- `private=false`;
- `gated=false`;
- `disabled=false`;
- repository license metadata `MIT`.

The voice model card and configuration independently identify:

- language: `de_DE`;
- sample rate: 22,050 Hz;
- model-card training dataset license: `CC0`.

## Structural synthesis proof

Fixed text:

`Dies ist ein kurzer Test der deutschen Sprachausgabe.`

Observed WAV:

- mono;
- 16-bit PCM;
- 22,050 Hz;
- 63,232 frames;
- 2.867664399 seconds;
- 62,678 non-zero samples;
- SHA-256 `edd63c2e1eb4fc0932e00cd3200108fea2b552163534f41507fceb6d1d72b09d`.

This proves only that the exact pinned voice can be acquired, loaded by the pinned Piper runtime, and used to produce structurally valid non-silent audio on the tested CPU GHA environment.

## Claim boundary

Not established here:

- intelligibility;
- word/character error rate;
- naturalness or prosody;
- speaker similarity;
- semantic accuracy;
- multilingual transfer;
- product suitability.

Those are Model Spelunker experiment questions and require independent oracles.

This validation also does not make an independent legal determination. It records and checks upstream repository/model-card metadata and keeps voice-model provenance separate from the GPL-licensed Piper validation runtime.

## Promotion boundary

No OCI candidate was published and no approved-catalog mapping was created by this proof.

Any candidate packaging/publication must reuse the existing Foundry lifecycle and remain distinct from reviewed approval/promotion.
