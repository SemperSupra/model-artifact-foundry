#!/usr/bin/env python3
"""Deterministically match a Foundry artifact representation to an environment.

This tool is intentionally not a scheduler or environment solver. It consumes
JSON records, makes conservative compatibility decisions, and emits JSON.
Optional private overlay evidence may be supplied locally; the tool never
publishes or persists that evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


_VERSION_RE = re.compile(r"^(==|>=|<=|>|<)?\s*([0-9]+(?:\.[0-9]+)*)$")


def _norm(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _version_tuple(value: str) -> tuple[int, ...] | None:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", value.strip()):
        return None
    return tuple(int(part) for part in value.split("."))


def _compare_version(actual: str | None, constraint: str | None) -> str:
    """Return match, mismatch, or unknown for a deliberately small constraint set."""
    if not constraint:
        return "match"
    if not actual:
        return "unknown"
    m = _VERSION_RE.fullmatch(constraint.strip())
    if not m:
        # Exact non-numeric versions can still be compared safely.
        return "match" if actual.strip() == constraint.strip() else "unknown"
    op, expected_text = m.groups()
    op = op or "=="
    a = _version_tuple(actual)
    e = _version_tuple(expected_text)
    if a is None or e is None:
        return "unknown"
    width = max(len(a), len(e))
    a = a + (0,) * (width - len(a))
    e = e + (0,) * (width - len(e))
    result = {
        "==": a == e,
        ">=": a >= e,
        "<=": a <= e,
        ">": a > e,
        "<": a < e,
    }[op]
    return "match" if result else "mismatch"


def _hard_match(profile: dict[str, Any], env: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    unknown = False

    checks = [
        ("platform.os_family", profile["platform"].get("os_family"), env["platform"].get("os_family")),
        ("platform.architecture", profile["platform"].get("architecture"), env["platform"].get("architecture")),
        ("accelerator.backend", profile["accelerator"].get("backend"), env["accelerator"].get("backend")),
        ("accelerator.vendor", profile["accelerator"].get("vendor"), env["accelerator"].get("vendor")),
        ("runtime.family", profile["runtime"].get("family"), env["runtime"].get("family")),
    ]
    for name, required, actual in checks:
        if required is None:
            continue
        if actual is None:
            unknown = True
            reasons.append(f"missing environment value for {name}")
        elif _norm(required) != _norm(actual):
            return "mismatch", [f"{name}: requires {required!r}, environment has {actual!r}"]

    version_checks = [
        (
            "runtime.framework_version",
            env["runtime"].get("framework_version"),
            profile["runtime"].get("framework_version_constraint"),
        ),
        (
            "runtime.backend_runtime_version",
            env["runtime"].get("backend_runtime_version"),
            profile["runtime"].get("backend_runtime_constraint"),
        ),
    ]
    for name, actual, constraint in version_checks:
        state = _compare_version(actual, constraint)
        if state == "mismatch":
            return "mismatch", [f"{name}: {actual!r} does not satisfy {constraint!r}"]
        if state == "unknown":
            unknown = True
            reasons.append(f"cannot safely decide {name} against {constraint!r}")

    return ("unknown" if unknown else "match"), reasons


def _private_result(
    artifact_digest: str,
    profile: dict[str, Any],
    env: dict[str, Any],
    overlay: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    if not overlay or overlay.get("artifact_digest") != artifact_digest:
        return None, None

    for record in overlay.get("records", []):
        private_env = record.get("environment", {})
        # Map the private overlay environment into the same generic shape.
        candidate = {
            "platform": private_env.get("platform", {}),
            "accelerator": private_env.get("accelerator", {}),
            "runtime": {
                "family": private_env.get("runtime", {}).get("family"),
                "framework_version": private_env.get("runtime", {}).get("framework_version"),
                "backend_runtime_version": private_env.get("runtime", {}).get("backend_runtime_version"),
            },
        }
        # A private record is relevant only if the supplied environment describes
        # the same generic execution family. Model class/memory remain diagnostic.
        comparable = all(
            _norm(candidate[group].get(key)) == _norm(env[group].get(key))
            for group, key in (
                ("platform", "os_family"),
                ("platform", "architecture"),
                ("accelerator", "backend"),
                ("runtime", "family"),
            )
            if candidate[group].get(key) is not None and env[group].get(key) is not None
        )
        if not comparable:
            continue
        hard, _ = _hard_match(profile, env)
        if hard == "mismatch":
            continue
        validation = record.get("validation", {})
        result = validation.get("result")
        if result == "passed":
            return "privately-validated", record.get("profile_id")
        if result == "failed":
            return "incompatible", record.get("profile_id")
    return None, None


def match(
    artifact: dict[str, Any],
    env: dict[str, Any],
    overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    digest = artifact["artifact_digest"]
    outcomes: list[dict[str, Any]] = []

    for profile in artifact.get("profiles", []):
        hard, reasons = _hard_match(profile, env)
        if hard == "mismatch":
            outcomes.append({"profile_id": profile["profile_id"], "state": "incompatible", "reasons": reasons})
            continue
        if hard == "unknown":
            outcomes.append({"profile_id": profile["profile_id"], "state": "unqualified", "reasons": reasons})
            continue

        private_state, private_profile = _private_result(digest, profile, env, overlay)
        if private_state:
            return {
                "artifact_digest": digest,
                "representation_id": artifact["representation"]["representation_id"],
                "result": private_state,
                "matched_public_profile": profile["profile_id"],
                "private_profile_id": private_profile,
            }

        claim_type = profile["claim"]["type"]
        return {
            "artifact_digest": digest,
            "representation_id": artifact["representation"]["representation_id"],
            "result": claim_type,
            "matched_public_profile": profile["profile_id"],
        }

    if outcomes and all(item["state"] == "incompatible" for item in outcomes):
        result = "incompatible"
    else:
        result = "unqualified"
    return {
        "artifact_digest": digest,
        "representation_id": artifact["representation"]["representation_id"],
        "result": result,
        "profiles": outcomes,
    }


def _load(path: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, help="artifact compatibility JSON")
    parser.add_argument("--environment", required=True, help="environment profile JSON")
    parser.add_argument("--private-overlay", help="optional private overlay JSON; never persisted")
    args = parser.parse_args()

    result = match(_load(args.artifact) or {}, _load(args.environment) or {}, _load(args.private_overlay))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
