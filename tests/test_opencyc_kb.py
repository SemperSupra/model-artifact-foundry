import json
from pathlib import Path
from unittest.mock import patch
import unittest

import jsonschema

from tools.public_metadata_lint import lint_file
from tools.validate_opencyc_kb import (
    DEFAULT_EVIDENCE_PATH,
    REQUIRED_FOUNDRY_START_SHA,
    SOURCE_DECL,
    SOURCE_SCHEMA,
    UPSTREAM_REVISION,
    get_git_info,
    is_ancestor,
    run_qualification,
    validate_declaration,
)


class TestOpenCycKBCandidate(unittest.TestCase):
    def test_source_declaration_schema(self):
        decl = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
        schema = json.loads(SOURCE_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(decl, schema)
        self.assertEqual(decl["logical_id"], "kb/opencyc/4.0")
        self.assertEqual(decl["source"]["provider"], "github-release")
        self.assertEqual(decl["source"]["repository"], "openmindproject/opencyc-backups")
        self.assertEqual(decl["source"]["discovery_ref"], UPSTREAM_REVISION)

    def test_validate_declaration_helper(self):
        decl = validate_declaration()
        self.assertEqual(decl["logical_id"], "kb/opencyc/4.0")

    def test_ancestry_check(self):
        head, tree = get_git_info()
        self.assertTrue(len(head) == 40)
        self.assertTrue(len(tree) == 40)
        self.assertTrue(is_ancestor(REQUIRED_FOUNDRY_START_SHA, head))

    def test_stale_target_when_ancestry_missing(self):
        unrelated_sha = "0000000000000000000000000000000000000000"
        with patch("tools.validate_opencyc_kb.REQUIRED_FOUNDRY_START_SHA", unrelated_sha):
            res = run_qualification(Path("/tmp/unused-cache"), Path("/tmp/unused-out.json"))
            self.assertEqual(res.get("terminal_state"), "STALE_TARGET")

    def test_evidence_record(self):
        self.assertTrue(DEFAULT_EVIDENCE_PATH.exists(), f"Evidence file missing at {DEFAULT_EVIDENCE_PATH}")
        evidence = json.loads(DEFAULT_EVIDENCE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(evidence["terminal_state"], "PARTIAL_LOCAL_CANDIDATE")
        self.assertEqual(evidence["logical_id"], "kb/opencyc/4.0")
        self.assertEqual(evidence["foundry_start_commit"], REQUIRED_FOUNDRY_START_SHA)
        self.assertEqual(evidence["upstream"]["provider"], "github-release")
        self.assertEqual(evidence["upstream"]["repository"], "openmindproject/opencyc-backups")
        self.assertEqual(evidence["upstream"]["exact_revision"], UPSTREAM_REVISION)

        self.assertEqual(evidence["license"]["observed_spdx_id"], "OPL-1.0")
        self.assertTrue(evidence["license"]["redistribution_verified"])

        self.assertEqual(len(evidence["files"]), 65)
        self.assertTrue(len(evidence["content_fingerprint"]) == 64)

        self.assertTrue(evidence["validation"]["determinism_verified"])
        self.assertEqual(evidence["validation"]["status"], "passed")
        self.assertEqual(
            evidence["validation"]["kb_structure_verification"]["manifest_unit_id"],
            "68b3e314d8491f0e51f5b92faa98d4726d3b38da18383e37d5a510103670385a",
        )
        self.assertEqual(
            evidence["validation"]["kb_structure_verification"]["counts"]["constant-count.text"], 188111
        )

        limitations = evidence["limitations_and_stop_state"]
        self.assertFalse(limitations["approved_catalog_promoted"])
        self.assertFalse(limitations["registry_published"])

    def test_public_metadata_lint(self):
        findings_sources = lint_file(SOURCE_DECL)
        self.assertEqual(findings_sources, [])

        findings_evidence = lint_file(DEFAULT_EVIDENCE_PATH)
        self.assertEqual(findings_evidence, [])


if __name__ == "__main__":
    unittest.main()
