from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "kv_ground_external_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("kv_ground_external_smoke", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExternalSmokeContractTest(unittest.TestCase):
    def test_contract_pins_exact_public_subject(self):
        module = load_module()
        contract = module.build_contract()
        self.assertEqual(
            contract["model"]["revision"],
            "fe7563292bb52ab6c235fc3c87157e6a14017479",
        )
        self.assertEqual(
            contract["loaders"]["legacy_equivalent"]["class"],
            "transformers.AutoModelForCausalLM",
        )
        self.assertEqual(
            contract["loaders"]["provider_eval"]["class"],
            "transformers.AutoModelForImageTextToText",
        )

    def test_parser_accepts_valid_tool_call(self):
        module = load_module()
        point = module.parse_tool_call(
            '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[500,500]}}</tool_call>'
        )
        self.assertTrue(module.point_hits_target(point))

    def test_parser_rejects_out_of_range_coordinate(self):
        module = load_module()
        with self.assertRaisesRegex(ValueError, "outside"):
            module.parse_tool_call(
                '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[1200,500]}}</tool_call>'
            )

    def test_contract_cli_is_byte_repeatable_and_stdlib_only(self):
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "a.json"
            second = Path(td) / "b.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--contract-only",
                    "--output",
                    str(first),
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--contract-only",
                    "--output",
                    str(second),
                ],
                check=True,
            )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            json.loads(first.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
