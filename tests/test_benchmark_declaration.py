import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


validator = load_module("benchmark_validator", "tools/validate_benchmark_declaration.py")
SYNTHETIC = json.loads((ROOT / "examples/benchmarks/visual-contract-generator.json").read_text())
OPEN_IMAGES = json.loads((ROOT / "examples/benchmarks/open-images-v7.json").read_text())


class BenchmarkDeclarationTests(unittest.TestCase):
    def test_synthetic_manifest_only_fixture_passes(self):
        self.assertEqual(validator.validate(SYNTHETIC), [])

    def test_open_images_composite_fixture_passes(self):
        self.assertEqual(validator.validate(OPEN_IMAGES), [])

    def test_mirror_requires_verified_redistribution(self):
        doc = copy.deepcopy(OPEN_IMAGES)
        annotations = doc["components"][0]
        annotations["license"]["redistribution_permitted"] = False
        errors = validator.validate(doc)
        self.assertTrue(any("mirrored component requires verified redistribution permission" in e for e in errors))

    def test_composite_requires_multiple_distribution_modes(self):
        doc = copy.deepcopy(OPEN_IMAGES)
        doc["components"][1]["distribution"] = "mirror"
        doc["components"][1]["license"]["status"] = "verified"
        doc["components"][1]["license"]["redistribution_permitted"] = True
        errors = validator.validate(doc)
        self.assertTrue(any("composite materialization requires" in e for e in errors))

    def test_overlay_requires_dependency(self):
        doc = copy.deepcopy(SYNTHETIC)
        doc["artifact_kind"] = "benchmark-overlay"
        errors = validator.validate(doc)
        self.assertTrue(any("benchmark-overlay requires" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
