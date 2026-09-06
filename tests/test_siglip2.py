import json
from pathlib import Path
from unittest.mock import patch
import unittest

import jsonschema

from tools.validate_siglip2 import (
    REPO_ROOT,
    REQUIRED_FOUNDRY_BASE_SHA,
    SOURCE_DECL,
    SOURCE_SCHEMA,
    get_git_info,
    is_ancestor,
    run_local_qualification,
    validate_declaration,
)


class TestSigLIP2Candidate(unittest.TestCase):
    def test_source_declaration_schema(self):
        decl = json.loads(SOURCE_DECL.read_text(encoding="utf-8"))
        schema = json.loads(SOURCE_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.validate(decl, schema)
        self.assertEqual(decl["logical_id"], "embed/siglip2/base-patch16-224")
        self.assertEqual(decl["source"]["provider"], "huggingface")
        self.assertEqual(decl["source"]["repository"], "google/siglip2-base-patch16-224")
        self.assertEqual(decl["source"]["discovery_ref"], "75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2")

    def test_validate_declaration_helper(self):
        decl = validate_declaration()
        self.assertEqual(decl["logical_id"], "embed/siglip2/base-patch16-224")

    def test_ancestry_check(self):
        head, tree = get_git_info()
        self.assertTrue(len(head) == 40)
        self.assertTrue(len(tree) == 40)
        self.assertTrue(is_ancestor(REQUIRED_FOUNDRY_BASE_SHA, head))

    def test_stale_target_when_ancestry_missing(self):
        unrelated_sha = "0000000000000000000000000000000000000000"
        with patch("tools.validate_siglip2.REQUIRED_FOUNDRY_BASE_SHA", unrelated_sha):
            res = run_local_qualification(Path("/tmp/unused-cache"))
            self.assertEqual(res.get("terminal_state"), "STALE_TARGET")


if __name__ == "__main__":
    unittest.main()
