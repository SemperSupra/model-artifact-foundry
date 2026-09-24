#!/usr/bin/env python3
from __future__ import annotations

import argparse
from array import array
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request
import wave


HF_REPO = "rhasspy/piper-voices"
REVISION = "6249c8a9178e606f0de19227d5426e5dfaf9fc9e"
PREFIX = "de/de_DE/thorsten/medium"
MODEL_NAME = "de_DE-thorsten-medium.onnx"
CONFIG_NAME = "de_DE-thorsten-medium.onnx.json"
CARD_NAME = "MODEL_CARD"
EXPECTED_FULL_PATHS = {
    f"{PREFIX}/{MODEL_NAME}",
    f"{PREFIX}/{CONFIG_NAME}",
    f"{PREFIX}/{CARD_NAME}",
}
FIXED_TEXT = "Dies ist ein kurzer Test der deutschen Sprachausgabe."
LOGICAL_ID = "tts/piper/de-de-thorsten-medium"
MAX_BYTES = 80_000_000


def request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={"User-Agent": "SemperSupra-model-artifact-foundry/1"},
    )


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(request(url), timeout=60) as response:
        return json.load(response)


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(request(url), timeout=240) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_metadata(meta: dict) -> dict:
    if meta.get("id") != HF_REPO:
        raise RuntimeError(f"unexpected upstream id: {meta.get('id')!r}")
    if meta.get("sha") != REVISION:
        raise RuntimeError(
            f"exact revision mismatch: expected {REVISION}, observed {meta.get('sha')!r}"
        )
    if meta.get("private"):
        raise RuntimeError("upstream unexpectedly became private")
    if meta.get("gated") not in (False, None):
        raise RuntimeError(f"upstream is gated: {meta.get('gated')!r}")
    if meta.get("disabled"):
        raise RuntimeError("upstream is disabled")

    card = meta.get("cardData") or {}
    license_id = str(card.get("license") or "").upper()
    if license_id != "MIT":
        raise RuntimeError(f"expected MIT repository metadata, observed {license_id!r}")

    siblings = {row.get("rfilename") for row in meta.get("siblings", [])}
    missing = EXPECTED_FULL_PATHS - siblings
    if missing:
        raise RuntimeError(f"exact revision missing expected files: {sorted(missing)}")

    return {
        "id": meta["id"],
        "sha": meta["sha"],
        "private": bool(meta.get("private")),
        "gated": meta.get("gated"),
        "disabled": bool(meta.get("disabled")),
        "license": license_id,
    }


def parse_model_card(text: str) -> dict:
    required = {
        "language": r"(?im)^\s*\*\s*Language:\s*de_DE\s*\(German,\s*Germany\)\s*$",
        "sample_rate": r"(?im)^\s*\*\s*Samplerate:\s*22,?050\s*Hz\s*$",
        "dataset_license": r"(?im)^\s*\*\s*License:\s*CC0\s*$",
    }
    missing = [name for name, pattern in required.items() if not re.search(pattern, text)]
    if missing:
        raise RuntimeError(f"model card missing required provenance fields: {missing}")
    return {
        "language": "de_DE",
        "sample_rate_hz": 22050,
        "training_dataset_license_observed": "CC0",
    }


def validate_voice_config(config: dict) -> dict:
    audio = config.get("audio")
    if not isinstance(audio, dict):
        raise RuntimeError("voice config is missing audio object")
    sample_rate = audio.get("sample_rate")
    if sample_rate != 22050:
        raise RuntimeError(f"unexpected voice sample rate: {sample_rate!r}")

    language = config.get("language")
    if isinstance(language, dict):
        code = language.get("code")
        if code not in (None, "de_DE", "de-de", "de-DE"):
            raise RuntimeError(f"unexpected language code: {code!r}")

    return {
        "sample_rate_hz": sample_rate,
        "language": language,
    }


def validate_wav(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        frames = wav.readframes(frame_count)

    if channels != 1:
        raise RuntimeError(f"expected mono WAV, observed channels={channels}")
    if sample_width != 2:
        raise RuntimeError(f"expected 16-bit PCM WAV, observed sample_width={sample_width}")
    if sample_rate != 22050:
        raise RuntimeError(f"expected 22050-Hz WAV, observed {sample_rate}")
    if frame_count <= sample_rate // 2:
        raise RuntimeError(f"synthesized WAV is too short: {frame_count} frames")

    pcm = array("h")
    pcm.frombytes(frames)
    if not pcm:
        raise RuntimeError("synthesized WAV contains no PCM samples")
    peak = max(abs(sample) for sample in pcm)
    nonzero = sum(1 for sample in pcm if sample != 0)
    if peak == 0 or nonzero < max(100, len(pcm) // 100):
        raise RuntimeError("synthesized WAV is effectively silent")

    return {
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sample_rate,
        "peak_abs_pcm16": peak,
        "nonzero_samples": nonzero,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-declaration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wav-output", type=Path)
    args = parser.parse_args()

    declaration = json.loads(args.source_declaration.read_text(encoding="utf-8"))
    if declaration["logical_id"] != LOGICAL_ID:
        raise RuntimeError("logical id mismatch")
    if declaration["source"]["repository"] != HF_REPO:
        raise RuntimeError("source repository mismatch")
    if declaration["source"]["discovery_ref"] != REVISION:
        raise RuntimeError("source revision mismatch")
    if set(declaration["artifact"]["expected_file_patterns"]) != {
        CARD_NAME,
        MODEL_NAME,
        CONFIG_NAME,
    }:
        raise RuntimeError("source declaration file allowlist mismatch")
    if declaration["artifact"]["max_unpacked_bytes"] != MAX_BYTES:
        raise RuntimeError("source declaration max bytes mismatch")

    metadata_url = f"https://huggingface.co/api/models/{HF_REPO}/revision/{REVISION}"
    source_meta = validate_metadata(fetch_json(metadata_url))

    with tempfile.TemporaryDirectory(prefix="foundry-piper-") as temp_dir:
        root = Path(temp_dir)
        files = {}
        total = 0
        for name in (CARD_NAME, MODEL_NAME, CONFIG_NAME):
            remote_path = f"{PREFIX}/{name}"
            url = f"https://huggingface.co/{HF_REPO}/resolve/{REVISION}/{remote_path}?download=true"
            dest = root / name
            download(url, dest)
            size = dest.stat().st_size
            total += size
            files[name] = {
                "source_path": remote_path,
                "size_bytes": size,
                "sha256": sha256_file(dest),
            }

        if total > MAX_BYTES:
            raise RuntimeError(f"voice artifact exceeds declared max bytes: {total}")

        card_text = (root / CARD_NAME).read_text(encoding="utf-8")
        card_evidence = parse_model_card(card_text)

        config = json.loads((root / CONFIG_NAME).read_text(encoding="utf-8"))
        config_evidence = validate_voice_config(config)

        from piper import PiperVoice

        voice = PiperVoice.load(str(root / MODEL_NAME))
        wav_path = root / "validation.wav"
        with wave.open(str(wav_path), "wb") as wav:
            voice.synthesize_wav(FIXED_TEXT, wav)
        wav_evidence = validate_wav(wav_path)

        if args.wav_output:
            args.wav_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(wav_path, args.wav_output)

    runtime_version = importlib.metadata.version("piper-tts")
    if runtime_version != "1.8.0":
        raise RuntimeError(f"unexpected piper-tts runtime version: {runtime_version}")

    result = {
        "schema_version": 1,
        "logical_id": LOGICAL_ID,
        "status": "passed",
        "upstream": {
            "provider": "huggingface",
            "repository": HF_REPO,
            "exact_revision": REVISION,
            "metadata": source_meta,
        },
        "license_provenance": {
            "repository_license_metadata": "MIT",
            "training_dataset_license_observed_in_model_card": "CC0",
            "claims": [
                "Repository license metadata and model-card dataset license were observed and checked.",
                "This validation does not make an independent legal determination.",
            ],
        },
        "artifact": {
            "family": "tts/piper-vits",
            "format": "piper-onnx-voice",
            "files": files,
            "total_bytes": sum(row["size_bytes"] for row in files.values()),
            "model_card": card_evidence,
            "voice_config": config_evidence,
        },
        "runtime": {
            "package": "piper-tts",
            "version": runtime_version,
            "device": "cpu",
        },
        "validation": {
            "profile": "piper-de-de-thorsten-structural-v1",
            "fixed_text": FIXED_TEXT,
            "wav": wav_evidence,
            "claims": [
                "The exact pinned voice artifact can be acquired without authentication.",
                "The exact voice loads in piper-tts 1.8.0 on CPU.",
                "A bounded German phrase produces a non-silent mono 22050-Hz 16-bit PCM WAV.",
            ],
            "non_claims": [
                "intelligibility",
                "naturalness",
                "speaker similarity",
                "semantic accuracy",
                "multilingual transfer",
                "product suitability",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "logical_id": LOGICAL_ID,
                "status": "passed",
                "model_sha256": files[MODEL_NAME]["sha256"],
                "wav_sha256": wav_evidence["sha256"],
                "duration_seconds": wav_evidence["duration_seconds"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
