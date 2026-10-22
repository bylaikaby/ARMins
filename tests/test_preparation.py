"""Synthetic NIfTI preparation and portable CLI checks for ARMins.

Version: 0.7.2 (local/unreleased)
Last updated: 2026-10-22
Change history: CHANGELOG.md
Status: candidate
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import nibabel as nib
import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
import armins


class PrepareLevel6Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="armins-test-")
        self.root = Path(self.temp.name)
        self.template_path = self.root / "template.nii.gz"
        self.atlas_path = self.root / "arm-levels.nii.gz"
        self.output_dir = self.root / "outputs"
        self.affine = np.array([
            [0.25, 0.0, 0.0, -0.375],
            [0.0, 0.25, 0.0, -0.25],
            [0.0, 0.0, 0.25, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        self.labels = np.zeros((4, 4, 4), dtype=np.int16)
        source_ids = [item[1] for item in armins.ARM_SEGMENTS]
        for index, label_id in enumerate(source_ids):
            self.labels.reshape(-1)[index] = label_id
        self.template = np.arange(64, dtype=np.float32).reshape((4, 4, 4))
        self._save_template()

    def tearDown(self):
        self.temp.cleanup()

    def test_module_version_header_matches_runtime_receipt_version(self):
        header = (REPO / "armins.py").read_text(encoding="utf-8").splitlines()
        version_line = next(line for line in header if line.startswith("Version:"))
        self.assertEqual(version_line.removeprefix("Version: "), armins.VERSION)

    def _save_template(self):
        nib.save(nib.Nifti1Image(self.template, self.affine), str(self.template_path))

    def _save_atlas(self, values, dtype=None):
        image = nib.Nifti1Image(np.asarray(values, dtype=dtype), self.affine)
        image.set_qform(self.affine, 1)
        image.set_sform(self.affine, 1)
        nib.save(image, str(self.atlas_path))

    def _multilevel(self, form):
        if form == "4d":
            values = np.zeros((4, 4, 4, 6), dtype=np.int16)
            values[..., 5] = self.labels
            return values
        values = np.zeros((4, 4, 4, 1, 6), dtype=np.int16)
        values[..., 0, 5] = self.labels
        return values

    def test_extracts_only_explicit_level_six_from_supported_shapes(self):
        for form, expected_form in (("4d", "4D"), ("5d", "5D")):
            labels, detected = armins.extract_arm_level(self._multilevel(form), level=6)
            np.testing.assert_array_equal(labels, self.labels)
            self.assertTrue(detected.startswith(expected_form))
        labels, detected = armins.extract_arm_level(self.labels, level=6)
        np.testing.assert_array_equal(labels, self.labels)
        self.assertEqual(detected, "already-3D-level-6")

    def test_known_provider_pair_is_path_independent_and_only_hash_bound(self):
        with patch.object(armins, "_sha256_file", side_effect=[
                armins.DEFAULT_TEMPLATE_SHA256,
                "7DF7E53DF5AA1F142BF017AAD89F1FDE3C84A87A3E4F93ADC7DBDED69BC79338"]):
            known = armins._input_names(self.template_path, self.atlas_path)
        self.assertTrue(known["default_pair"])
        self.assertEqual(known["segment_names"], armins.DEFAULT_SEG_NAMES)
        with patch.object(armins, "_sha256_file", side_effect=[
                armins.DEFAULT_TEMPLATE_SHA256, "0" * 64]):
            unknown = armins._input_names(self.template_path, self.atlas_path)
        self.assertFalse(unknown["default_pair"])

    def test_rejects_ambiguous_shapes_wrong_level_and_noninteger_labels(self):
        with self.assertRaisesRegex(ValueError, "ambiguous ARM atlas shape"):
            armins.extract_arm_level(np.zeros((4, 4, 4, 2, 6), dtype=np.int16))
        with self.assertRaisesRegex(ValueError, "only explicit ARM --level 6"):
            armins.extract_arm_level(self._multilevel("5d"), level=5)
        with self.assertRaisesRegex(ValueError, "integer labels"):
            armins.extract_arm_level(self._multilevel("4d").astype(np.float32))

    def test_prepare_dry_run_reports_paths_without_writing(self):
        self._save_atlas(self._multilevel("5d"))
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  (self.template_path, self.atlas_path)}
        result = armins.prepare_level6(
            self.template_path, self.atlas_path, level=6,
            output_dir=self.output_dir, dry_run=True)
        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(result["writes"], [])
        self.assertEqual(result["loader_version"], armins.VERSION)
        self.assertEqual(result["processing_timezone"], "UTC")
        self.assertTrue(result["generated_at"].endswith("+00:00"))
        self.assertIn("python_version", result)
        self.assertIn("numpy_version", result)
        self.assertIn("nibabel_version", result)
        self.assertFalse(self.output_dir.exists())
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})

    def test_prepare_writes_one_3d_integer_atlas_and_receipt_without_copying_template(self):
        self._save_atlas(self._multilevel("5d"))
        template_hash = hashlib.sha256(self.template_path.read_bytes()).hexdigest().upper()
        result = armins.prepare_level6(
            self.template_path, self.atlas_path, level=6,
            output_dir=self.output_dir)
        output_path = Path(result["output_path"])
        receipt_path = Path(result["receipt_path"])
        self.assertTrue(output_path.is_file())
        self.assertTrue(receipt_path.is_file())
        self.assertEqual(len(result["writes"]), 2)
        self.assertEqual(hashlib.sha256(self.template_path.read_bytes()).hexdigest().upper(), template_hash)
        prepared = nib.load(str(output_path))
        self.assertEqual(prepared.shape, self.labels.shape)
        self.assertTrue(np.issubdtype(prepared.get_data_dtype(), np.integer))
        np.testing.assert_array_equal(np.asanyarray(prepared.dataobj), self.labels)
        np.testing.assert_allclose(prepared.affine, self.affine, rtol=0, atol=1e-6)
        saved_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_receipt["output_sha256"], hashlib.sha256(output_path.read_bytes()).hexdigest().upper())
        self.assertEqual(saved_receipt["level"], 6)
        self.assertEqual(saved_receipt["loader_version"], armins.VERSION)
        self.assertEqual(saved_receipt["processing_timezone"], "UTC")
        self.assertTrue(saved_receipt["generated_at"].endswith("+00:00"))

    def test_prepare_refuses_overwrite_and_preserves_existing_product(self):
        self._save_atlas(self._multilevel("4d"))
        first = armins.prepare_level6(self.template_path, self.atlas_path, level=6,
                                      output_dir=self.output_dir)
        output_path = Path(first["output_path"])
        original_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
        with self.assertRaises(FileExistsError):
            armins.prepare_level6(self.template_path, self.atlas_path, level=6,
                                  output_dir=self.output_dir)
        self.assertEqual(hashlib.sha256(output_path.read_bytes()).hexdigest(), original_hash)

    def test_existing_three_dimensional_level_six_is_returned_without_duplicate(self):
        self._save_atlas(self.labels)
        result = armins.prepare_level6(self.template_path, self.atlas_path, level=6,
                                       output_dir=self.output_dir)
        self.assertEqual(result["status"], "already-prepared")
        self.assertEqual(result["loader_version"], armins.VERSION)
        self.assertEqual(result["processing_timezone"], "UTC")
        self.assertTrue(result["generated_at"].endswith("+00:00"))
        self.assertEqual(result["level"], 6)
        self.assertEqual(result["template_path"], str(self.template_path.resolve()))
        self.assertIn("template_sha256", result)
        self.assertIn("python_version", result)
        self.assertIn("numpy_version", result)
        self.assertIn("nibabel_version", result)
        self.assertEqual(Path(result["output_path"]), self.atlas_path.resolve())
        self.assertEqual(result["writes"], [])
        self.assertFalse(self.output_dir.exists())

    def test_requires_matching_template_spatial_grid_and_full_arm_id_set(self):
        self._save_atlas(self._multilevel("5d"))
        changed = np.eye(4)
        changed[:3, :3] *= 0.3
        nib.save(nib.Nifti1Image(self.template, changed), str(self.template_path))
        with self.assertRaisesRegex(ValueError, "geometry differ"):
            armins.check_inputs(self.template_path, self.atlas_path)
        self._save_template()
        missing = self._multilevel("5d")
        missing[..., 0, 5] = 0
        self._save_atlas(missing)
        with self.assertRaisesRegex(ValueError, "IDs are absent"):
            armins.check_inputs(self.template_path, self.atlas_path)

    def test_cli_help_runs_outside_slicer(self):
        completed = subprocess.run(
            [sys.executable, str(REPO / "armins.py"), "--help"],
            check=True, capture_output=True, text=True)
        self.assertIn("{check,prepare,search,gui}", completed.stdout)
        self.assertIn(armins.VERSION, completed.stdout)
        version = subprocess.run(
            [sys.executable, str(REPO / "armins.py"), "--version"],
            check=True, capture_output=True, text=True, cwd=self.root)
        self.assertEqual(version.stdout.strip(), f"ARMins {armins.VERSION}")


    def test_cli_check_dry_run_resolves_and_validates_without_writes(self):
        self._save_atlas(self._multilevel("5d"))
        completed = subprocess.run(
            [sys.executable, str(REPO / "armins.py"), "check",
             "--template", str(self.template_path), "--atlas", str(self.atlas_path),
             "--level", "6", "--dry-run"],
            check=True, capture_output=True, text=True)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["loader_version"], armins.VERSION)
        self.assertEqual(result["processing_timezone"], "UTC")
        self.assertTrue(result["generated_at"].endswith("+00:00"))
        self.assertIn("python_version", result)
        self.assertIn("numpy_version", result)
        self.assertIn("nibabel_version", result)
        self.assertEqual(result["level6_shape"], [4, 4, 4])
        self.assertEqual(result["level6_form"], "5D-spatial-plus-singleton-and-six-levels")
        self.assertFalse(self.output_dir.exists())

    def test_cli_prepare_dry_run_reports_output_without_creating_it(self):
        self._save_atlas(self._multilevel("4d"))
        completed = subprocess.run(
            [sys.executable, str(REPO / "armins.py"), "prepare",
             "--template", str(self.template_path), "--atlas", str(self.atlas_path),
             "--level", "6", "--output-dir", str(self.output_dir), "--dry-run"],
            check=True, capture_output=True, text=True)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(len(result["writes"]), 0)
        self.assertFalse(self.output_dir.exists())


if __name__ == "__main__":
    unittest.main()
