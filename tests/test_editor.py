"""Synthetic regression checks for ARMins editor scope and input helpers.

Version: 0.6.0 (local/unreleased)
Last updated: 2026-10-22
Change history: CHANGELOG.md
Status: candidate
"""

import runpy
import sys
import types
import unittest
from pathlib import Path

import numpy as np


_slicer = sys.modules.get("slicer")
sys.modules["slicer"] = types.ModuleType("slicer")
try:
    _LOADER = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "armins.py"),
        run_name="armins_editor_test",
    )
finally:
    if _slicer is None:
        sys.modules.pop("slicer", None)
    else:
        sys.modules["slicer"] = _slicer


class TestInsulaScopeMasks(unittest.TestCase):
    def test_full_insula_scopes_include_full_label_set_and_are_disjoint(self):
        labels = np.array([[[39, 41, 42, 43, 226, 228, 229, 230,
                             539, 541, 542, 543, 726, 728, 729, 730, 37, 537]]], dtype=np.uint16)
        masks = _LOADER["build_scope_masks"](labels)
        self.assertEqual(int(masks["L"].sum()), 8)
        self.assertEqual(int(masks["R"].sum()), 8)
        self.assertFalse(np.any(masks["L"] & masks["R"]))

    def test_scope_masks_reject_non_3d_or_non_integer_input(self):
        with self.assertRaisesRegex(ValueError, "3-D integer"):
            _LOADER["build_scope_masks"](np.zeros((2, 2), dtype=np.uint8))
        with self.assertRaisesRegex(ValueError, "3-D integer"):
            _LOADER["build_scope_masks"](np.zeros((2, 2, 2), dtype=np.float32))

    def test_arm6_seed_masks_partition_the_two_full_insula_scopes(self):
        label_ids = [label_id for _, label_id, _, _ in _LOADER["ARM_SEGMENTS"]]
        labels = np.asarray(label_ids, dtype=np.uint16).reshape((2, 4, 2))
        masks = _LOADER["build_arm6_masks"](labels)
        self.assertEqual(len(masks), 16)
        self.assertTrue(all(int(mask.sum()) == 1 for mask in masks.values()))
        combined = np.logical_or.reduce(list(masks.values()))
        scopes = _LOADER["build_scope_masks"](labels)
        self.assertTrue(np.array_equal(combined, scopes["L"] | scopes["R"]))

    def test_input_validator_requires_compatible_3d_integer_arm6_and_geometry(self):
        labels = np.asarray([label_id for _, label_id, _, _ in _LOADER["ARM_SEGMENTS"]],
                            dtype=np.uint16).reshape((2, 4, 2))
        image = np.ones_like(labels, dtype=np.float32)
        identity = np.eye(4)
        counts = _LOADER["validate_input_arrays"](image, labels, identity, identity)
        self.assertEqual(counts[228], 1)
        with self.assertRaisesRegex(ValueError, "shape mismatch"):
            _LOADER["validate_input_arrays"](np.ones((2, 2, 2)), labels, identity, identity)
        shifted = identity.copy()
        shifted[0, 3] = 1
        with self.assertRaisesRegex(ValueError, "geometry differ"):
            _LOADER["validate_input_arrays"](image, labels, identity, shifted)

    def test_input_validator_rejects_missing_arm_ids_and_float_atlas(self):
        labels = np.zeros((2, 2, 2), dtype=np.uint16)
        with self.assertRaisesRegex(ValueError, "IDs are absent"):
            _LOADER["validate_input_arrays"](np.ones_like(labels), labels, np.eye(4), np.eye(4))
        compatible_ids = [label_id for _, label_id, _, _ in _LOADER["ARM_SEGMENTS"]]
        atlas = np.asarray(compatible_ids, dtype=np.float32).reshape((2, 4, 2))
        with self.assertRaisesRegex(ValueError, "integer label volume"):
            _LOADER["validate_input_arrays"](np.ones_like(atlas), atlas, np.eye(4), np.eye(4))

    def test_custom_inputs_bind_new_groups_but_not_existing_unbound_nodes(self):
        class Segmentation:
            def __init__(self): self.attrs = {}
            def GetAttribute(self, key): return self.attrs.get(key)
            def SetAttribute(self, key, value): self.attrs[key] = value

        info = {"signature": "custom", "template_hash": "t", "atlas_hash": "a",
                "default_pair": False}
        bind = _LOADER["_bind_segmentation_source"]
        with self.assertRaisesRegex(RuntimeError, "custom inputs will not reuse it"):
            bind(Segmentation(), "old", "template.nii", "atlas.nii", info)
        new_group = Segmentation()
        bind(new_group, "new", "template.nii", "atlas.nii", info, new_node=True)
        self.assertEqual(new_group.attrs["Insula.SourceSignature"], "custom")

    def test_arm6_seed_rerun_preserves_existing_segment(self):
        class Segment:
            def __init__(self, name): self.name, self.tags = name, {}
            def GetName(self): return self.name
            def SetTag(self, key, value): self.tags[key] = value

        class Data:
            def __init__(self): self.segments = {"ARM_L6_228": Segment("CL_Ia/Id")}
            def GetSegment(self, sid): return self.segments.get(sid)
            def GetNumberOfSegments(self): return len(self.segments)
            def GetNthSegmentID(self, i): return list(self.segments)[i]
            def AddEmptySegment(self, sid, name, color): self.segments[sid] = Segment(name)

        class Segmentation:
            def __init__(self): self.data = Data()
            def GetSegmentation(self): return self.data

        updates = []
        namespace = _LOADER["seed_arm6_segments"].__globals__
        old_slicer = namespace["slicer"]
        namespace["slicer"] = types.SimpleNamespace(
            util=types.SimpleNamespace(updateSegmentBinaryLabelmapFromArray=
                                       lambda *args: updates.append(args[2])))
        self.addCleanup(namespace.__setitem__, "slicer", old_slicer)
        segmentation = Segmentation()
        source_ids = [label_id for _, label_id, _, _ in _LOADER["ARM_SEGMENTS"]]
        labels = np.asarray(source_ids, dtype=np.uint16).reshape((2, 4, 2))
        first_added = _LOADER["seed_arm6_segments"](segmentation, labels, object(), "L")
        second_added = _LOADER["seed_arm6_segments"](segmentation, labels, object(), "L")
        self.assertEqual(len(first_added), 7)
        self.assertEqual(second_added, [])
        self.assertNotIn("ARM_L6_228", updates)

    def test_volume_loader_returns_node_without_deprecated_flag(self):
        class Node:
            def GetImageData(self):
                return object()

        node = Node()
        kwargs_seen = {}

        def loader(path, **kwargs):
            kwargs_seen.update(kwargs)
            return node

        namespace = _LOADER["_load_or_reuse"].__globals__
        original_find = namespace["_find"]
        namespace["_find"] = lambda name: None
        try:
            result = _LOADER["_load_or_reuse"](Path("sample.nii.gz"), "sample", loader)
        finally:
            namespace["_find"] = original_find
        self.assertIs(result, node)
        self.assertEqual(kwargs_seen, {"properties": {"name": "sample"}})

    def test_volume_loader_reports_failed_legacy_tuple(self):
        namespace = _LOADER["_load_or_reuse"].__globals__
        original_find = namespace["_find"]
        namespace["_find"] = lambda name: None
        try:
            with self.assertRaisesRegex(RuntimeError, "failed to load"):
                _LOADER["_load_or_reuse"](
                    Path("sample.nii.gz"), "sample", lambda *a, **k: (False, None))
        finally:
            namespace["_find"] = original_find

    def _scope_editor_fixture(self):
        class Segment:
            def __init__(self, name): self.name = name
            def GetName(self): return self.name

        class SegmentationData:
            def __init__(self, side):
                scope_id = _LOADER["SCOPE_IDS"][side]
                parcel_id = f"{side}-parcel-a"
                arm_id = "ARM_L6_228" if side == "L" else "ARM_L6_728"
                self.ids = [scope_id, parcel_id, arm_id]
                self.segments = {sid: Segment(name) for sid, name in zip(
                    self.ids, [scope_id, "left parcel A" if side == "L" else "right parcel A",
                               "CL_Ia/Id" if side == "L" else "CR_Ia/Id"])}
            def GetSegment(self, sid): return self.segments.get(sid)
            def GetNumberOfSegments(self): return len(self.ids)
            def GetNthSegmentID(self, i): return self.ids[i]

        class Display:
            def __init__(self): self.visibility = {}
            def SetSegmentVisibility(self, sid, visible): self.visibility[sid] = visible

        class SegNode:
            def __init__(self, side): self.data, self.display = SegmentationData(side), Display()
            def GetSegmentation(self): return self.data
            def GetDisplayNode(self): return self.display

        class Parameters:
            def __init__(self): self.calls, self.mask_id, self.mask_mode = [], "", -1
            def StartModify(self): return 9
            def EndModify(self, previous): self.calls.append(("end", previous))
            def SetMaskSegmentID(self, value): self.calls.append(("id", value)); self.mask_id = value
            def SetMaskMode(self, value): self.calls.append(("mode", value)); self.mask_mode = value
            def SetOverwriteMode(self, value): self.calls.append(("overwrite", value))
            def SetSelectedSegmentID(self, value): self.calls.append(("selected", value))
            def SetActiveEffectName(self, value): self.calls.append(("effect", value))
            def GetMaskSegmentID(self): return self.mask_id
            def GetMaskMode(self): return self.mask_mode

        class Editor:
            def __init__(self, parameters): self.parameters = parameters
            def setSegmentationNode(self, node): pass
            def setSourceVolumeNode(self, node): pass
            def mrmlSegmentEditorNode(self): return self.parameters

        parameters = Parameters()
        segmentations = {"L": SegNode("L"), "R": SegNode("R")}
        editor = Editor(parameters)
        widget = types.SimpleNamespace(self=lambda: types.SimpleNamespace(editor=editor))
        fake_slicer = types.SimpleNamespace(
            util=types.SimpleNamespace(selectModule=lambda name: None),
            modules=types.SimpleNamespace(segmenteditor=types.SimpleNamespace(widgetRepresentation=lambda: widget)),
            vtkMRMLSegmentationNode=types.SimpleNamespace(EditAllowedInsideSingleSegment=2),
            vtkMRMLSegmentEditorNode=types.SimpleNamespace(OverwriteVisibleSegments=1))
        namespace = _LOADER["use_scope"].__globals__
        old_slicer, old_find = namespace["slicer"], namespace["_find"]
        namespace["slicer"] = fake_slicer
        namespace["_find"] = lambda name: (
            segmentations["L"] if name == _LOADER["ACTIVE_SEG_NAMES"]["L"] else
            segmentations["R"] if name == _LOADER["ACTIVE_SEG_NAMES"]["R"] else object())
        self.addCleanup(namespace.__setitem__, "slicer", old_slicer)
        self.addCleanup(namespace.__setitem__, "_find", old_find)
        return parameters, segmentations

    def test_use_scope_resolves_display_name_and_applies_mask_id_first(self):
        parameters, segmentations = self._scope_editor_fixture()
        result = _LOADER["use_scope"]("L", "left parcel A")
        self.assertEqual(parameters.calls[0], ("id", "L-INS-Scope"))
        self.assertEqual(parameters.calls[1], ("mode", 2))
        self.assertIn("segment=L-INS-Scope", result)
        self.assertIn(("selected", "L-parcel-a"), parameters.calls)
        self.assertEqual(segmentations["L"].display.visibility, {"L-INS-Scope": False})
        self.assertEqual(segmentations["R"].display.visibility, {})

    def test_use_scope_accepts_seeded_arm_id_and_rejects_opposite_side(self):
        parameters, _ = self._scope_editor_fixture()
        _LOADER["use_scope"]("L", "CL_Ia/Id")
        self.assertIn(("selected", "ARM_L6_228"), parameters.calls)
        parameters.calls.clear()
        with self.assertRaisesRegex(ValueError, "unique existing"):
            _LOADER["use_scope"]("L", "CR_Ia/Id")
        self.assertEqual(parameters.calls, [])

    def test_invalid_target_does_not_change_editor_or_visibility(self):
        parameters, segmentations = self._scope_editor_fixture()
        with self.assertRaisesRegex(ValueError, "unique existing"):
            _LOADER["use_scope"]("L", "missing parcel")
        self.assertEqual(parameters.calls, [])
        self.assertEqual(segmentations["L"].display.visibility, {})

if __name__ == "__main__":
    unittest.main()
