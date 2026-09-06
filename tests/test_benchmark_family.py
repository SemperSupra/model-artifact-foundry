from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBenchmarkFamily(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="foundry-benchmark-test-")
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)

    def test_source_declaration_schema(self) -> None:
        schema_path = REPO_ROOT / "schemas" / "source-declaration.schema.json"
        decl_path = REPO_ROOT / "sources" / "benchmark-content-policy-multilingual.json"

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        decl = json.loads(decl_path.read_text(encoding="utf-8"))

        jsonschema.validate(instance=decl, schema=schema)
        self.assertEqual(decl["artifact"]["family"], "benchmark/dataset")
        self.assertEqual(decl["logical_id"], "benchmark/dataset/content-policy/multilingual-slice-v1")

    def test_approved_catalog_schema(self) -> None:
        schema_path = REPO_ROOT / "schemas" / "approved-catalog.schema.json"
        catalog_path = REPO_ROOT / "catalog" / "approved.json"

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

        jsonschema.validate(instance=catalog, schema=schema)
        entry = catalog["artifacts"]["benchmark/dataset/content-policy/multilingual-slice-v1"]
        self.assertEqual(
            entry["approved_digest"],
            "sha256:b4cfc567559a831464ef6d25c254c838da396bddd251505f4d509a20eca94c34",
        )

    def test_harvest_benchmark_and_candidate_manifest(self) -> None:
        dist_dir = Path(self.tmp_dir) / "dist"
        candidate_output = Path(self.tmp_dir) / "candidate_manifest.json"

        # 1. Prepare
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "harvest_benchmark.py"), "prepare", "--dist-dir", str(dist_dir)],
            check=True,
        )
        self.assertTrue((dist_dir / "model.tar.gz").exists())
        self.assertTrue((dist_dir / "bundle-manifest.json").exists())
        self.assertTrue((dist_dir / "NOTICE.txt").exists())

        # 2. Verify pulled
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "harvest_benchmark.py"), "verify-pulled", "--bundle-dir", str(dist_dir)],
            check=True,
        )

        # 3. Candidate manifest
        tool_rev = "4a82c5d72dd3fef6bef3dccdace23a5c1859636c"
        digest = "sha256:b4cfc567559a831464ef6d25c254c838da396bddd251505f4d509a20eca94c34"
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "harvest_benchmark.py"),
                "candidate-manifest",
                "--dist-dir",
                str(dist_dir),
                "--oci-repository",
                "ghcr.io/sempersupra/model-artifact-foundry",
                "--digest",
                digest,
                "--tool-revision",
                tool_rev,
                "--output",
                str(candidate_output),
            ],
            check=True,
        )

        # 4. Schema validation on generated candidate manifest
        cand_schema = json.loads((REPO_ROOT / "schemas" / "candidate-manifest.schema.json").read_text(encoding="utf-8"))
        candidate = json.loads(candidate_output.read_text(encoding="utf-8"))
        jsonschema.validate(instance=candidate, schema=cand_schema)

        # 5. Check validation claims boundary (mechanical claims only)
        claims = candidate["validation"]["claims"]
        self.assertGreater(len(claims), 0)
        for claim in claims:
            # Must not claim semantic model correctness
            self.assertNotIn("semantic correctness", claim.lower())
            self.assertNotIn("label accuracy", claim.lower())

    def test_multi_consumer_hydration(self) -> None:
        dist_dir = Path(self.tmp_dir) / "dist"
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "harvest_benchmark.py"), "prepare", "--dist-dir", str(dist_dir)],
            check=True,
        )

        # Create mock ORAS executable
        mock_oras = Path(self.tmp_dir) / "mock_oras"
        mock_oras.write_text(
            f"""#!/usr/bin/env python3
import sys, shutil
from pathlib import Path

output_dir = None
for i, arg in enumerate(sys.argv):
    if arg == '--output' and i + 1 < len(sys.argv):
        output_dir = Path(sys.argv[i+1])

dist = Path({repr(str(dist_dir))})
if output_dir and dist.exists():
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in ['model.tar.gz', 'bundle-manifest.json', 'NOTICE.txt']:
        shutil.copy2(dist / f, output_dir / f)
    sys.exit(0)
sys.exit(1)
""",
            encoding="utf-8",
        )
        mock_oras.chmod(mock_oras.stat().st_mode | stat.S_IEXEC)

        logical_id = "benchmark/dataset/content-policy/multilingual-slice-v1"
        catalog_path = REPO_ROOT / "catalog" / "approved.json"

        # Hydrate Consumer A
        cache_a = Path(self.tmp_dir) / "consumer_a" / "cache"
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "hydrate.py"),
                "--catalog",
                str(catalog_path),
                "--id",
                logical_id,
                "--cache-root",
                str(cache_a),
                "--oras",
                str(mock_oras),
            ],
            check=True,
        )

        # Hydrate Consumer B
        cache_b = Path(self.tmp_dir) / "consumer_b" / "cache"
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "hydrate.py"),
                "--catalog",
                str(catalog_path),
                "--id",
                logical_id,
                "--cache-root",
                str(cache_b),
                "--oras",
                str(mock_oras),
            ],
            check=True,
        )

        # Offline second hydration for Consumer A (idempotence)
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "hydrate.py"),
                "--catalog",
                str(catalog_path),
                "--id",
                logical_id,
                "--cache-root",
                str(cache_a),
                "--oras",
                "/bin/false",
            ],
            check=True,
        )

        # Verify selected mappings in both consumer cache roots
        sel_a = json.loads((cache_a / "selected" / "benchmark__dataset__content-policy__multilingual-slice-v1.json").read_text(encoding="utf-8"))
        sel_b = json.loads((cache_b / "selected" / "benchmark__dataset__content-policy__multilingual-slice-v1.json").read_text(encoding="utf-8"))

        expected_digest = "sha256:b4cfc567559a831464ef6d25c254c838da396bddd251505f4d509a20eca94c34"
        self.assertEqual(sel_a["digest"], expected_digest)
        self.assertEqual(sel_b["digest"], expected_digest)

        dir_a = Path(sel_a["model_dir"])
        dir_b = Path(sel_b["model_dir"])

        # Check hydrated data files in both consumer directories
        manifest_a = json.loads((dir_a / "manifest.json").read_text(encoding="utf-8"))
        manifest_b = json.loads((dir_b / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest_a["item_count"], 5)
        self.assertEqual(manifest_b["item_count"], 5)
        self.assertEqual(manifest_a["item_ids"], manifest_b["item_ids"])


if __name__ == "__main__":
    unittest.main()
