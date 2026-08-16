import ast
import json
import pathlib
import unittest
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).parents[1]


class ModuleStructureTest(unittest.TestCase):
    def test_python_is_syntactically_valid(self):
        for path in ROOT.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_manifest_and_views_exist(self):
        manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
        self.assertEqual(manifest["license"], "AGPL-3")
        for name in manifest["data"]:
            self.assertTrue((ROOT / name).is_file(), name)
            if name.endswith(".xml"):
                ET.parse(ROOT / name)

    def test_contract_platform_and_idempotency_are_explicit(self):
        source = (ROOT / "models" / "stock_picking.py").read_text(encoding="utf-8")
        self.assertIn('"platform": "odoo"', source)
        self.assertIn("_govp_idempotency_key", source)


if __name__ == "__main__":
    unittest.main()
