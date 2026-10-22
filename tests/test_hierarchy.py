"""Synthetic hierarchy resolution tests for ARMins.

Version: 0.7.0 (local/unreleased)
Last updated: 2026-10-22
Change history: CHANGELOG.md
Status: candidate
"""

import csv
import hashlib
from pathlib import Path
import tempfile
import unittest

from arm_hierarchy import ArmHierarchy


FIELDS = ["WM/GM"] + [column for level in range(1, 7)
    for column in (f"Level_{level}", f"Level_{level}_abbr", f"Level_{level}_index")]


def _row(side, namespace, leaf_id, leaf_name, leaf_full, root_index=1,
         region_index=3, region_name="ACC", region_full="anterior_cingulate_cortex",
         tissue="grey_matter"):
    prefix = {("C", "L"): "CL", ("C", "R"): "CR",
              ("S", "L"): "SL", ("S", "R"): "SR"}[(namespace, side)]
    region_parent = root_index + 1
    levels = [
        (f"{prefix}_Frontal_Lobe", f"{prefix}_Front", root_index),
        (f"{prefix}_anterior_cingulate_gyrus", f"{prefix}_ACgG", region_parent),
        (f"{prefix}_{region_full}", f"{prefix}_{region_name}", region_index),
        (f"{prefix}_area_group", f"{prefix}_area_group", region_index + 1),
        (f"{prefix}_{leaf_name}", f"{prefix}_{leaf_name}", leaf_id),
        (f"{prefix}_{leaf_full}", f"{prefix}_{leaf_name}", leaf_id),
    ]
    row = {"WM/GM": tissue}
    for level, (full, abbr, index) in enumerate(levels, 1):
        row[f"Level_{level}"] = full
        row[f"Level_{level}_abbr"] = abbr
        row[f"Level_{level}_index"] = str(index)
    return row


def _acc_rows():
    pairs = [(20, 920, "area_32"), (21, 930, "area_24a"), (22, 940, "area_25")]
    rows = []
    for left, right, name in pairs:
        rows.append(_row("L", "C", left, name, name))
        rows.append(_row("R", "C", right, name, name))
    return rows


def _pi_rows():
    rows = []
    rows.extend([
        _row("L", "C", 30, "Pi", "posterior_insular_area", region_name="Pi",
             region_full="posterior_insular_area", region_index=13),
        _row("R", "C", 1930, "Pi", "posterior_insular_area", region_name="Pi",
             region_full="posterior_insular_area", region_index=1013),
        _row("L", "S", 130, "Pi", "pyramidal_decussation", region_name="Pi",
             region_full="pyramidal_decussation", root_index=1001, region_index=1003),
        _row("R", "S", 1130, "Pi", "pyramidal_decussation", region_name="Pi",
             region_full="pyramidal_decussation", root_index=2001, region_index=2003),
    ])
    return rows


class ArmHierarchyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="armins-hierarchy-")
        self.root = Path(self.temp.name)
        self.path = self.root / "ARM_key_table.csv"
        self.rows = _acc_rows() + _pi_rows()
        self._write(self.rows)

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, rows, fields=FIELDS):
        with self.path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_profile_builds_bilateral_leaf_sets_and_explicit_non_offset_pairing(self):
        hierarchy = ArmHierarchy.from_file(self.path)
        profile = hierarchy.profile_for(3, 3, "L")
        self.assertEqual([item["index"] for item in profile["left_leaves"]], [20, 21, 22])
        self.assertEqual([item["index"] for item in profile["right_leaves"]], [920, 930, 940])
        self.assertEqual([(item["left_id"], item["right_id"]) for item in profile["pair_map"]],
                         [(20, 920), (21, 930), (22, 940)])
        self.assertNotEqual(profile["pair_map"][0]["right_id"], profile["pair_map"][0]["left_id"] + 500)
        self.assertEqual(profile["source_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest().upper())
        self.assertEqual(profile["profile_hash"], hierarchy.profile_for(3, 3, "L")["profile_hash"])
        right_selected = hierarchy.profile_for(3, 3, "R")
        self.assertEqual(profile["profile_hash"], right_selected["profile_hash"])
        self.assertEqual(right_selected["working_side"], "R")

    def test_search_returns_separate_candidates_and_deduplicated_descendant_count(self):
        hierarchy = ArmHierarchy.from_file(self.path)
        matches = hierarchy.search("acc", side="L", level=3)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["descendant_count"], 3)
        self.assertEqual(matches[0]["descendant_ids"], [20, 21, 22])
        ambiguous = hierarchy.search("Pi", side="L", level=5)
        self.assertEqual({item["namespace"] for item in ambiguous}, {"C", "S"})
        self.assertEqual(len(ambiguous), 2)

    def test_numeric_search_is_exact_not_substring(self):
        other_left = _row("L", "C", 100, "area_100", "area_100", root_index=10,
                          region_index=33, region_name="Other", region_full="other_cortex")
        other_right = _row("R", "C", 1100, "area_100", "area_100", root_index=1010,
                           region_index=1033, region_name="Other", region_full="other_cortex")
        for row, prefix in ((other_left, "CL"), (other_right, "CR")):
            row["Level_1"] = f"{prefix}_second_lobe"
            row["Level_1_abbr"] = f"{prefix}_Second"
            row["Level_2"] = f"{prefix}_other_gyrus"
            row["Level_2_abbr"] = f"{prefix}_OtherG"
        rows = self.rows + [other_left, other_right]
        self._write(rows)
        hierarchy = ArmHierarchy.from_file(self.path)
        results = hierarchy.search("1", side="L", level=1)
        self.assertEqual([item["index"] for item in results], [1])
        exact = hierarchy.profile_for(1, 1, "L")
        self.assertEqual(exact["selected"]["index"], 1)

    def test_exact_abbreviation_resolves_one_node_and_requires_level(self):
        hierarchy = ArmHierarchy.from_file(self.path)
        self.assertEqual(hierarchy.resolve("CL_ACC", "L", 3)["selected"]["index"], 3)
        with self.assertRaisesRegex(ValueError, "level is required"):
            hierarchy.resolve("CL_ACC", "L")
        with self.assertRaisesRegex(ValueError, "exact abbreviation"):
            hierarchy.resolve("ACC", "L", 3)

    def test_namespaces_remain_distinct_for_duplicate_pi_label(self):
        hierarchy = ArmHierarchy.from_file(self.path)
        matches = hierarchy.search("Pi", side="L", level=5)
        self.assertEqual({item["namespace"] for item in matches}, {"C", "S"})
        self.assertEqual(hierarchy.profile_for(30, 5, "L", namespace="C")["selected"]["namespace"], "C")
        self.assertEqual(hierarchy.profile_for(130, 5, "L", namespace="S")["selected"]["namespace"], "S")

    def test_missing_opposite_counterpart_fails_closed(self):
        rows = [row for row in self.rows if not row["Level_1_abbr"].startswith("CR_")]
        self._write(rows)
        with self.assertRaisesRegex(ValueError, "counterpart.*missing"):
            ArmHierarchy.from_file(self.path).profile_for(3, 3, "L")

    def test_inconsistent_duplicate_identity_path_is_rejected(self):
        rows = list(self.rows)
        changed = dict(rows[1])
        changed["Level_2"] = "CL_different_gyrus"
        rows.append(changed)
        self._write(rows)
        with self.assertRaisesRegex(ValueError, "conflicting hierarchy identity/path"):
            ArmHierarchy.from_file(self.path)

    def test_conflicting_hemisphere_path_is_rejected(self):
        rows = list(self.rows)
        changed = dict(rows[0])
        changed["Level_4_abbr"] = "CR_area_group"
        rows.append(changed)
        self._write(rows)
        with self.assertRaisesRegex(ValueError, "mixed hemisphere"):
            ArmHierarchy.from_file(self.path)

    def test_flat_key_schema_is_refused(self):
        self._write([], fields=["Index", "Abbreviation", "First_Level", "Last_Level"])
        with self.assertRaisesRegex(ValueError, "flat First_Level/Last_Level"):
            ArmHierarchy.from_file(self.path)

    def test_noninteger_identity_is_rejected(self):
        rows = list(self.rows)
        rows[0] = dict(rows[0])
        rows[0]["Level_6_index"] = "20.0"
        self._write(rows)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            ArmHierarchy.from_file(self.path)

    def test_ambiguous_numeric_identity_across_namespaces_requires_namespace(self):
        rows = list(self.rows)
        cortical = dict(rows[0])
        subcortical = _row("L", "S", 20, "area_32", "area_32", root_index=1001,
                           region_index=2003, region_name="ACC", region_full="anterior_cingulate_cortex")
        rows.extend([cortical, subcortical])
        self._write(rows)
        hierarchy = ArmHierarchy.from_file(self.path)
        with self.assertRaisesRegex(ValueError, "ambiguous across namespaces"):
            hierarchy.profile_for(20, 6, "L")
        self.assertEqual(hierarchy.profile_for(20, 6, "L", "C")["selected"]["namespace"], "C")


if __name__ == "__main__":
    unittest.main()
