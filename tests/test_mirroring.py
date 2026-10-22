"""Synthetic tests for ARMins exact-grid mirror preflight.

Version: 0.7.0 (local/unreleased)
Last updated: 2026-10-22
Change history: CHANGELOG.md
Status: candidate

Synthetic reflection, identity mapping, symmetry, and partition checks use no
Slicer scene or scientific inputs.
"""

import importlib.util
from pathlib import Path
import sys
import types
import unittest

import numpy as np


MODULE_PATH = Path(__file__).resolve().parents[1] / "armins.py"
if not MODULE_PATH.is_file():
    raise FileNotFoundError(f"ARMins module not found: {MODULE_PATH}")

# The production module imports Slicer at module scope. Supply a temporary stub
# for pure-array tests, then restore the test process's original module table.
_prior_slicer = sys.modules.get("slicer")
if _prior_slicer is None:
    _slicer_stub = types.ModuleType("slicer")
    _slicer_stub.mrmlScene = object()
    sys.modules["slicer"] = _slicer_stub
try:
    spec = importlib.util.spec_from_file_location("armins_mirror_test_target", MODULE_PATH)
    insula = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(insula)
finally:
    if _prior_slicer is None:
        sys.modules.pop("slicer", None)


class MirrorGeometryTests(unittest.TestCase):
    def setUp(self):
        self.shape = (4, 3, 8)  # KJI; mirrored I is numpy axis 2
        self.affine = np.eye(4)
        self.affine[0, 0] = 0.25
        self.affine[1, 1] = 0.25
        self.affine[2, 2] = 0.25
        self.affine[:3, 3] = (-0.875, -0.25, 0.0)

    def test_exact_physical_reflection_uses_correct_kji_axis_and_roundtrips(self):
        mapping = insula.reflection_index_mapping(self.affine, self.shape)
        self.assertEqual(mapping["ijk_axis"], 0)
        self.assertEqual(mapping["numpy_axis"], 2)
        values = np.zeros(self.shape, dtype=np.uint8)
        values[1, 2, 0] = 7
        reflected = insula.reflect_kji_array(values, mapping)
        self.assertEqual(reflected[1, 2, 7], 7)
        np.testing.assert_array_equal(insula.reflect_kji_array(reflected, mapping), values)

    def test_half_voxel_shift_and_oblique_grid_are_rejected(self):
        shifted = self.affine.copy()
        shifted[0, 3] += 0.125
        with self.assertRaisesRegex(ValueError, "voxel centers|shifted"):
            insula.reflection_index_mapping(shifted, self.shape)
        oblique = self.affine.copy()
        angle = np.deg2rad(20)
        oblique[:2, :2] = 0.25 * np.array([[np.cos(angle), -np.sin(angle)],
                                           [np.sin(angle), np.cos(angle)]])
        with self.assertRaisesRegex(ValueError, "unsupported oblique|voxel centers"):
            insula.reflection_index_mapping(oblique, self.shape)

    def test_segment_lattice_allows_integer_origin_offset_only(self):
        shifted = self.affine.copy()
        shifted[0, 3] += 0.25
        self.assertEqual(insula.integer_lattice_offset(self.affine, shifted), [1, 0, 0])
        shifted[0, 3] += 0.125
        with self.assertRaisesRegex(ValueError, "off the reference voxel lattice"):
            insula.integer_lattice_offset(self.affine, shifted)
        different_spacing = self.affine.copy()
        different_spacing[0, 0] = 0.3
        with self.assertRaisesRegex(ValueError, "spacing or orientation"):
            insula.integer_lattice_offset(self.affine, different_spacing)

    def test_candidate_name_probe_does_not_reserve_scene_names(self):
        class Scene:
            def __init__(self, names):
                self.names = set(names)

            def GetFirstNodeByName(self, name):
                return object() if name in self.names else None

        scene = Scene({"candidate", "candidate_1"})
        self.assertEqual(insula._candidate_name_available(scene, "candidate"), "candidate_2")
        self.assertEqual(scene.names, {"candidate", "candidate_1"})

    def test_cropped_segment_embedding_preserves_foreground_or_rejects_fov_loss(self):
        cropped = np.zeros((2, 2, 3), dtype=bool)
        cropped[1, 0, 2] = True
        extent = (1, 3, 1, 2, 1, 2)
        full = insula.embed_segment_mask(cropped, extent, [0, 0, 0], (4, 3, 8))
        self.assertEqual(int(full.sum()), 1)
        self.assertTrue(full[2, 1, 3])
        outside = np.ones((1, 1, 1), dtype=bool)
        with self.assertRaisesRegex(ValueError, "outside the reference field of view"):
            insula.embed_segment_mask(outside, (-2, -2, 0, 0, 0, 0), [0, 0, 0], (4, 3, 8))


class MirrorIdentityAndDataTests(unittest.TestCase):
    def test_official_and_custom_names_map_explicitly(self):
        self.assertEqual(insula.mirrored_segment_identity(
            "ARM_L6_39", "CL_Iam/Iapm", "L", {"ARM.SourceLabelID": "39"}),
            ("ARM_L6_539", "CR_Iam/Iapm", "parcel"))
        self.assertEqual(insula.mirrored_segment_identity("L-child", "L-child", "L"),
                         ("R-child", "R-child", "parcel"))
        self.assertEqual(insula.mirrored_segment_identity(
            "L-parent-mask", "L-parent-mask", "L", {insula.MIRROR_HELPER_TAG: "helper_mask"}),
            ("R-parent-mask", "R-parent-mask", "helper_mask"))

    def test_unknown_wrong_side_and_renamed_official_parcels_fail_closed(self):
        bad = [
            ("ARM_L6_539", "CR_Iam/Iapm", "L", {}),
            ("ARM_L6_39", "renamed", "L", {}),
            ("L-", "L-", "L", {}),
            ("L-unknown", "wrong-name", "L", {}),
            ("unmapped", "unmapped", "L", {}),
        ]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                insula.mirrored_segment_identity(*args)

    def test_atlas_left_right_ids_mirror_exactly(self):
        shape = (2, 3, 8)
        affine = np.eye(4)
        affine[0, 0] = affine[1, 1] = affine[2, 2] = 1
        affine[0, 3] = -3.5
        mapping = insula.reflection_index_mapping(affine, shape)
        atlas = np.zeros(shape, dtype=np.uint16)
        positions = [(0, 0, 0), (0, 1, 1), (0, 2, 2), (1, 0, 3),
                     (1, 1, 0), (1, 2, 1), (0, 0, 2), (1, 1, 3)]
        for (left_id, right_id), (k, j, i) in zip(insula.ARM_MIRROR_IDS.items(), positions):
            atlas[k, j, i] = left_id
            atlas[k, j, atlas.shape[2] - 1 - i] = right_id
        report = insula.validate_atlas_symmetry(atlas, mapping)
        self.assertEqual(report["scope_mismatch_voxels"], 0)
        self.assertTrue(all(pair["mismatch_voxels"] == 0 for pair in report["pairs"]))
        atlas[0, 0, 7] = 0
        with self.assertRaisesRegex(ValueError, "atlas symmetry failed"):
            insula.validate_atlas_symmetry(atlas, mapping)

    def test_template_symmetry_is_measured_and_enforced(self):
        shape = (2, 2, 4)
        affine = np.eye(4)
        affine[0, 0] = 1
        affine[0, 3] = -1.5
        mapping = insula.reflection_index_mapping(affine, shape)
        template = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
        template[:] = (template + template[..., ::-1]) / 2
        report = insula.validate_template_symmetry(template, mapping)
        self.assertEqual(report["voxels_over_tolerance"], 0)
        template[0, 0, 0] += 1
        with self.assertRaisesRegex(ValueError, "not symmetric"):
            insula.validate_template_symmetry(template, mapping)

    def test_partition_accepts_exact_tiling_and_rejects_overlap_gap_and_leak(self):
        scope = np.ones((2, 2, 4), dtype=bool)
        first = np.zeros_like(scope)
        first[..., :2] = True
        second = ~first
        self.assertEqual(insula.validate_partition(scope, {"a": first, "b": second})["gap_voxels"], 0)
        overlap = second.copy()
        overlap[0, 0, 0] = True
        with self.assertRaisesRegex(ValueError, "gaps=0, overlaps=1.*leaks=0"):
            insula.validate_partition(scope, {"a": first, "b": overlap})
        gap = second.copy()
        gap[0, 0, 3] = False
        with self.assertRaisesRegex(ValueError, "gaps=1, overlaps=0.*leaks=0"):
            insula.validate_partition(scope, {"a": first, "b": gap})
        leak = second.copy()
        leak[0, 0, 0] = True
        narrow_scope = scope.copy()
        narrow_scope[0, 0, 0] = False
        first_without = first.copy()
        first_without[0, 0, 0] = False
        with self.assertRaisesRegex(ValueError, "leaks=1"):
            insula.validate_partition(narrow_scope, {"a": first_without, "b": leak})


if __name__ == "__main__":
    unittest.main()
