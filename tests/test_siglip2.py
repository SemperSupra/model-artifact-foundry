import json
from pathlib import Path
import unittest

import jsonschema

from tools.validate_siglip2 import REPO_ROOT, SOURCE_DECL, SOURCE_SCHEMA, validate_declaration


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


if __name__ == "__main__":
    unittest.main()
