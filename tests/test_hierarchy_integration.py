"""Hierarchy profile integration and portable CLI checks.

Version: 0.7.0 (local/unreleased)
Last updated: 2026-10-22
Change history: CHANGELOG.md
Status: candidate
"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from test_hierarchy import FIELDS, _acc_rows
import armins


class HierarchyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="armins-hier-integration-")
        self.root = Path(self.temp.name)
        self.csv_path = self.root / "ARM_key_table.csv"
        rows = _acc_rows()
        with self.csv_path.open("w", encoding="utf-8", newline="") as stream:
            import csv
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        hierarchy_type, _ = armins._load_hierarchy_class(self.csv_path)
        self.resolver = hierarchy_type.from_file(self.csv_path)
        self.profile_l = self.resolver.profile_for(3, 3, "L")
        self.profile_r = self.resolver.profile_for(3, 3, "R")

    def tearDown(self):
        armins.configure_region(None)
        self.temp.cleanup()

    def test_profile_switch_isolated_from_default_and_paired_side_shares_identity(self):
        armins.configure_region(None)
        default_names = dict(armins.ACTIVE_SEG_NAMES)
        self.assertEqual(len(armins.ARM_SEGMENTS), 16)
        first = armins.configure_region(self.profile_l)
        hierarchy_names = dict(armins.ACTIVE_SEG_NAMES)
        self.assertEqual(first["mode"], "hierarchy")
        self.assertEqual(len(armins.ARM_SEGMENTS), 6)
        self.assertNotEqual(hierarchy_names, default_names)
        armins.configure_region(self.profile_r)
        self.assertEqual(armins.ACTIVE_SEG_NAMES, hierarchy_names)
        armins.configure_region(None)
        self.assertEqual(armins.ACTIVE_SEG_NAMES, default_names)
        self.assertEqual(len(armins.ARM_SEGMENTS), 16)

    def test_hierarchy_segment_identity_uses_explicit_non_offset_pair(self):
        armins.configure_region(self.profile_l)
        left_id = self.profile_l["pair_map"][0]["left_id"]
        right_id = self.profile_l["pair_map"][0]["right_id"]
        left_name = self.profile_l["pair_map"][0]["left_abbreviation"]
        right_name = self.profile_l["pair_map"][0]["right_abbreviation"]
        left_color = next(item[3] for item in armins.ARM_SEGMENTS if item[1] == left_id)
        right_color = next(item[3] for item in armins.ARM_SEGMENTS if item[1] == right_id)
        self.assertEqual(left_color, right_color)
        self.assertNotEqual(right_id, left_id + 500)
        self.assertEqual(armins.mirrored_segment_identity(
            f"ARM_L6_{left_id}", left_name, "L", {"ARM.SourceLabelID": str(left_id)}),
            (f"ARM_L6_{right_id}", right_name, "parcel"))
        self.assertEqual(armins.mirrored_segment_identity(
            f"ARM_L6_{right_id}", right_name, "R", {"ARM.SourceLabelID": str(right_id)}),
            (f"ARM_L6_{left_id}", left_name, "parcel"))

    def test_search_cli_resolves_external_table_from_an_unrelated_working_directory(self):
        completed = subprocess.run(
            [sys.executable, str(REPO / "armins.py"), "search", "--hierarchy", str(self.csv_path),
             "--query", "3", "--side", "L", "--level", "3", "--dry-run"],
            cwd=self.root, capture_output=True, text=True, check=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "read-only-search")
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["descendant_ids"], [20, 21, 22])
        self.assertEqual(result["writes"], [])

    def test_cli_requires_explicit_level_and_rejects_ambiguous_profile(self):
        with self.assertRaisesRegex(ValueError, "--region-level is required"):
            armins._cli_region_profile(str(self.csv_path), "ACC", None, "L")
        with self.assertRaisesRegex(ValueError, "exact abbreviation match"):
            armins._cli_region_profile(str(self.csv_path), "ACC", 3, "L")


if __name__ == "__main__":
    unittest.main()
