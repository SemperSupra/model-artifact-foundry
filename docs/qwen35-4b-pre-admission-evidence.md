# Qwen3.5 4B pre-admission evidence

State: **pre-admission evidence only**. This is not a Foundry candidate manifest, compatibility claim, redistribution approval, or approved-catalog entry.

## Why this record exists

A bounded persona-qualification run in `SemperSupra/model-spelunker` pulled Ollama `qwen3.5:4b` once on a public CPU runner and captured the local manifest/layer identities as an observational side effect. Retaining those identities here avoids a second multi-GB public download solely to recover provenance.

Evidence source:
- repository: `SemperSupra/model-spelunker`
- workflow run: `35247410518`
- commit: `d73f97ea4ffb1722cdff2852c7bd74eb5e71e2ef`
- workflow artifact: `persona-openworker-001`
- artifact id: `10509010461`
- artifact digest: `sha256:d2cf629c59745c8378b675f644692ab4fc4a1a6f186993dde779ab8266b46f1f`
- Ollama runtime: `0.34.0`
- model locator: `qwen3.5:4b`

## Captured immutable identities

- Ollama manifest SHA-256: `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`
- model layer: `sha256:81fb60c7daa80fc1123380b98970b320ae233409f0f71a72ed7b9b0d62f40490`
  - observed size: `3389971840` bytes
- license layer: `sha256:7339fa418c9ad3e8e12e74ad0fd26a9cc4be8703f9c110728a992b193be85cb2`
- params layer: `sha256:9371364b27a52acac9d87f88bd93c9db1174d8d6ec57f6888925cdc1788871ff`
- config: `sha256:de9fed2251b37295b763727a59ca35cf5cfe5c7379bc3e2104b2ce3c145aa887`
- observed pull wall time: `24 s`

## What this evidence establishes

It establishes the exact Ollama manifest and layer identities used by that run and provides a durable cross-repository pointer to the execution evidence.

It does **not** establish:
- a canonical upstream exact source revision corresponding to the Ollama representation;
- verified redistribution/license evidence under the Foundry source policy;
- per-file acquisition hashes in a Foundry candidate manifest;
- a Foundry OCI package digest or pullback verification;
- compatibility outside the recorded persona experiment;
- model quality, safety, or persona qualification.

## Next gate

Before candidate admission, map this representation to an acceptable Foundry source declaration and verify the license/redistribution evidence and exact acquired bytes required by the current candidate schema. Promotion remains review-required.
