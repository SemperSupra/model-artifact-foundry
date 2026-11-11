#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_KINDS = {"dataset", "benchmark", "benchmark-overlay", "synthetic-generator"}
ALLOWED_MODES = {"mirror", "upstream-hydrate", "manifest-only", "composite"}
ALLOWED_DISTRIBUTIONS = {"mirror", "upstream-hydrate", "manifest-only"}


def validate(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if doc.get("artifact_kind") not in ALLOWED_KINDS:
        errors.append("unsupported artifact_kind")
    if doc.get("materialization_mode") not in ALLOWED_MODES:
        errors.append("unsupported materialization_mode")

    components = doc.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty list")
        return errors

    names: set[str] = set()
    distributions: set[str] = set()
    for index, component in enumerate(components):
        prefix = f"components[{index}]"
        if not isinstance(component, dict):
            errors.append(f"{prefix} must be an object")
            continue
        name = component.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{prefix}.name is required")
        elif name in names:
            errors.append(f"duplicate component name: {name}")
        else:
            names.add(name)

        distribution = component.get("distribution")
        if distribution not in ALLOWED_DISTRIBUTIONS:
            errors.append(f"{prefix}.distribution is invalid")
            continue
        distributions.add(distribution)

        source = component.get("source")
        if not isinstance(source, dict) or not source.get("locator"):
            errors.append(f"{prefix}.source.locator is required")

        license_info = component.get("license")
        if not isinstance(license_info, dict):
            errors.append(f"{prefix}.license is required")
            continue
        status = license_info.get("status")
        redistribution = license_info.get("redistribution_permitted")
        evidence = license_info.get("evidence")
        if status not in {"verified", "unresolved"}:
            errors.append(f"{prefix}.license.status is invalid")
        if not isinstance(redistribution, bool):
            errors.append(f"{prefix}.license.redistribution_permitted must be boolean")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}.license.evidence must be non-empty")
        if distribution == "mirror" and not (status == "verified" and redistribution is True):
            errors.append(f"{prefix}: mirrored component requires verified redistribution permission")

    mode = doc.get("materialization_mode")
    if mode == "mirror" and distributions != {"mirror"}:
        errors.append("mirror materialization requires all components to be mirrored")
    if mode == "upstream-hydrate" and distributions != {"upstream-hydrate"}:
        errors.append("upstream-hydrate materialization requires all components to be upstream-hydrated")
    if mode == "manifest-only" and distributions != {"manifest-only"}:
        errors.append("manifest-only materialization requires all components to be manifest-only")
    if mode == "composite" and len(distributions) < 2:
        errors.append("composite materialization requires at least two component distribution modes")

    if doc.get("artifact_kind") == "benchmark-overlay" and not doc.get("dependencies"):
        errors.append("benchmark-overlay requires at least one dependency")
    if doc.get("promotion_policy", {}).get("mode") != "review-required":
        errors.append("promotion_policy.mode must be review-required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("declaration", type=Path)
    args = parser.parse_args()
    doc = json.loads(args.declaration.read_text(encoding="utf-8"))
    errors = validate(doc)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"valid benchmark declaration: {doc['logical_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
