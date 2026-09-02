#!/usr/bin/env python3
"""Public-safe KV-Ground external GPU compatibility smoke.

This is intentionally not target qualification. It tests one public artifact on a
synthetic GUI fixture and emits a machine-readable execution receipt.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import sys
import time
from pathlib import Path
from typing import Any

MODEL_ID = "vocaela/KV-Ground-8B-BaseGuiOwl1.5-0315"
MODEL_REVISION = "fe7563292bb52ab6c235fc3c87157e6a14017479"
FIXTURE_SIZE = (1000, 1000)
TARGET_BBOX = (350, 420, 650, 580)
INSTRUCTION = "Click the TARGET button."

SYSTEM_PROMPT = """You are a GUI grounding assistant.
The user will give an instruction about the supplied screenshot.
Return exactly one tool call in this form:
<tool_call>
{"name":"computer_use","arguments":{"action":"left_click","coordinate":[x,y]}}
</tool_call>
Coordinates are in a 1000x1000 screen coordinate system.
Place the click near the center of the requested UI element.
"""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_contract() -> dict[str, Any]:
    return {
        "schema_version": "kv-ground-external-smoke-contract-v1",
        "model": {
            "provider": "huggingface",
            "repository": MODEL_ID,
            "revision": MODEL_REVISION,
        },
        "fixture": {
            "kind": "generated_synthetic_gui",
            "size": list(FIXTURE_SIZE),
            "target_bbox_1000": list(TARGET_BBOX),
            "instruction": INSTRUCTION,
        },
        "loaders": {
            "legacy_equivalent": {
                "class": "transformers.AutoModelForCausalLM",
                "intent": "characterize compatibility of the legacy desktop-ui-cv loader class",
                "kwargs": {
                    "device_map": "auto",
                    "trust_remote_code": True,
                },
            },
            "provider_eval": {
                "class": "transformers.AutoModelForImageTextToText",
                "intent": "match the public kv-ground evaluation repository loader class",
                "kwargs": {
                    "device_map": "auto",
                    "dtype": "torch.bfloat16",
                },
            },
        },
        "non_qualification": [
            "not desktop-ui-cv private holdout quality evidence",
            "not target Windows compatibility evidence",
            "not target VRAM/load/latency qualification",
            "not a Foundry qualification subject",
        ],
    }


def parse_tool_call(text: str) -> dict[str, Any]:
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, flags=re.DOTALL)
    if not match:
        raise ValueError("missing <tool_call> JSON envelope")
    payload = json.loads(match.group(1))
    if payload.get("name") != "computer_use":
        raise ValueError("tool call name is not computer_use")
    arguments = payload.get("arguments")
    if not isinstance(arguments, dict) or arguments.get("action") != "left_click":
        raise ValueError("tool call action is not left_click")
    coordinate = arguments.get("coordinate")
    if (
        not isinstance(coordinate, list)
        or len(coordinate) != 2
        or not all(isinstance(value, (int, float)) for value in coordinate)
    ):
        raise ValueError("coordinate must be a two-number array")
    x, y = coordinate
    if not (0 <= x <= 1000 and 0 <= y <= 1000):
        raise ValueError("coordinate is outside the 1000x1000 contract")
    return {"x": float(x), "y": float(y)}


def point_hits_target(point: dict[str, Any]) -> bool:
    left, top, right, bottom = TARGET_BBOX
    return left <= point["x"] <= right and top <= point["y"] <= bottom


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def environment_snapshot(torch_module: Any | None = None) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            "accelerate": _version("accelerate"),
            "pillow": _version("pillow"),
            "torch": _version("torch"),
            "transformers": _version("transformers"),
        },
    }
    if torch_module is not None:
        cuda_available = bool(torch_module.cuda.is_available())
        snapshot["cuda"] = {
            "available": cuda_available,
            "runtime": getattr(torch_module.version, "cuda", None),
            "device_count": torch_module.cuda.device_count() if cuda_available else 0,
            "device_name": (
                torch_module.cuda.get_device_name(0) if cuda_available else None
            ),
        }
    return snapshot


def generate_fixture() -> Any:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", FIXTURE_SIZE, "white")
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = TARGET_BBOX
    draw.rectangle((left, top, right, bottom), outline="black", width=6)
    draw.text((455, 492), "TARGET", fill="black")
    draw.rectangle((70, 100, 260, 210), outline="black", width=3)
    draw.text((110, 145), "OTHER", fill="black")
    return image


def build_messages(image: Any) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": INSTRUCTION},
            ],
        },
    ]


def run_smoke(loader: str) -> dict[str, Any]:
    started = time.monotonic()
    receipt: dict[str, Any] = {
        "schema_version": "kv-ground-external-smoke-result-v1",
        "contract": build_contract(),
        "loader": loader,
        "status": "started",
    }

    try:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoModelForImageTextToText,
            AutoProcessor,
        )

        receipt["environment"] = environment_snapshot(torch)
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available; external GPU smoke requires CUDA")

        image = generate_fixture()
        messages = build_messages(image)

        processor_started = time.monotonic()
        processor = AutoProcessor.from_pretrained(
            MODEL_ID,
            revision=MODEL_REVISION,
            trust_remote_code=True,
        )
        receipt["processor_load_seconds"] = round(
            time.monotonic() - processor_started, 6
        )

        model_started = time.monotonic()
        if loader == "legacy_equivalent":
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                revision=MODEL_REVISION,
                device_map="auto",
                trust_remote_code=True,
            )
        elif loader == "provider_eval":
            model = AutoModelForImageTextToText.from_pretrained(
                MODEL_ID,
                revision=MODEL_REVISION,
                device_map="auto",
                dtype=torch.bfloat16,
            )
        else:
            raise ValueError(f"unsupported loader: {loader}")

        model.eval()
        receipt["model_load_seconds"] = round(time.monotonic() - model_started, 6)

        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            return_tensors="pt",
            return_dict=True,
            add_generation_prompt=True,
        ).to(model.device)

        inference_started = time.monotonic()
        with torch.inference_mode():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=128,
                do_sample=False,
            )
        receipt["inference_seconds"] = round(
            time.monotonic() - inference_started, 6
        )

        input_ids = inputs["input_ids"]
        generated_trimmed = [
            output_ids[len(input_row) :]
            for input_row, output_ids in zip(input_ids, generated_ids)
        ]
        generated_text = processor.batch_decode(
            generated_trimmed,
            skip_special_tokens=False,
            clean_up_tokenization_spaces=False,
        )[0]

        receipt["raw_output"] = generated_text
        try:
            point = parse_tool_call(generated_text)
            receipt["parser"] = {
                "status": "pass",
                "point_1000": point,
                "hits_synthetic_target": point_hits_target(point),
            }
        except Exception as exc:
            receipt["parser"] = {
                "status": "fail",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

        receipt["status"] = "pass"
    except Exception as exc:
        receipt["status"] = "fail"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
        if "environment" not in receipt:
            receipt["environment"] = environment_snapshot()
    finally:
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 6)

    return receipt


def write_receipt(receipt: dict[str, Any], output: Path | None) -> None:
    rendered = canonical_json(receipt) + "\n"
    if output is None:
        sys.stdout.write(rendered)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    os.replace(temporary, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--loader",
        choices=("legacy_equivalent", "provider_eval"),
        help="GPU loader path to exercise",
    )
    parser.add_argument(
        "--contract-only",
        action="store_true",
        help="emit the public experiment contract without importing ML dependencies",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.contract_only:
        write_receipt(build_contract(), args.output)
        return 0

    if not args.loader:
        parser.error("--loader is required unless --contract-only is used")

    receipt = run_smoke(args.loader)
    write_receipt(receipt, args.output)
    return 0 if receipt["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
