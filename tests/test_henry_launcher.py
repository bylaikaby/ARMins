"""Bounded Henry launcher discovery checks.

Version: 0.1.4 (local/unreleased)
Last updated: 2026-10-29
Change history: CHANGELOG.md
Status: candidate
"""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import henry_preset


class LauncherTests(unittest.TestCase):
    def test_left_l6_selection_rejects_overlap_and_missing_insula(self):
        class Hierarchy:
            def __init__(self, ids):
                self.ids = ids

            def search(self, prefix, side=None, level=None):
                self_side, namespace = ("L", "C") if prefix == "CL_" else ("L", "S")
                return [{"index": value, "abbreviation": f"{prefix}{value}",
                         "namespace": namespace, "side": self_side, "level": 6}
                        for value in self.ids[namespace]]

        groups = henry_preset._left_l6_groups(Hierarchy({"C": [39, 40], "S": [51]}), {39})
        self.assertEqual(set(groups["C"]) | set(groups["S"]), {39, 40, 51})
        with self.assertRaisesRegex(ValueError, "overlap"):
            henry_preset._left_l6_groups(Hierarchy({"C": [39], "S": [39]}), {39})
        with self.assertRaisesRegex(ValueError, "missing Insula"):
            henry_preset._left_l6_groups(Hierarchy({"C": [40], "S": [51]}), {39})

    def test_newest_stable_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "Program Files" / "slicer.org"
            for name in ("3D Slicer 5.9", "Slicer-5.12.3", "Slicer5.12.2", "3D Slicer 5.13.0 preview"):
                candidate = root / name / "Slicer.exe"
                candidate.parent.mkdir(parents=True)
                candidate.touch()
            chosen = henry_preset._installed_slicer(roots=[root], path_match="", registry_candidates=[])
            self.assertEqual(chosen.parent.name, "Slicer-5.12.3")
            override = root / "3D Slicer 5.9" / "Slicer.exe"
            self.assertEqual(henry_preset._installed_slicer(override, roots=[]), override.resolve())
            custom = Path(folder) / "Custom Install" / "Slicer.exe"
            custom.parent.mkdir()
            custom.touch()
            self.assertEqual(henry_preset._installed_slicer(roots=[], path_match="",
                             registry_candidates=[custom]), custom.resolve())
            self.assertEqual(henry_preset._installed_slicer(roots=[], path_match=str(custom),
                             registry_candidates=[]), custom.resolve())
            impostor = Path(folder) / "PrusaSlicer.exe"
            impostor.touch()
            with self.assertRaisesRegex(FileNotFoundError, "--slicer"):
                henry_preset._installed_slicer(roots=[], path_match="",
                                                 registry_candidates=[impostor])
            with patch.object(henry_preset, "_input_paths", return_value={}):
                with patch("subprocess.Popen") as popen:
                    popen.return_value.pid = 123
                    self.assertEqual(henry_preset.main(["--slicer", str(override)]), 0)
                    self.assertEqual(popen.call_args.args[0][0], str(override.resolve()))
                    self.assertEqual(popen.call_args.args[0][-1], str(ROOT / "henry_preset.py"))

    def test_missing_install(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(FileNotFoundError, "--slicer"):
                henry_preset._installed_slicer(roots=[folder], path_match="", registry_candidates=[])
            with self.assertRaisesRegex(FileNotFoundError, "Slicer executable not found"):
                henry_preset._installed_slicer(Path(folder) / "missing.exe")

    def test_input_preflight_reports_missing_and_unreadable_field_before_spawn(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "atlas_config.json"
            paths = {key: str(root / f"{key}.nii.gz")
                     for key in ("template", "atlas", "hierarchy")}
            for key in ("template", "atlas"):
                Path(paths[key]).write_bytes(b"x")
            config.write_text(json.dumps(paths), encoding="utf-8")
            for name in ("armins.py", "arm_hierarchy.py"):
                (root / name).write_text("# synthetic companion\n", encoding="utf-8")
            with self.assertRaisesRegex(OSError, "hierarchy input is not readable"):
                henry_preset._input_paths(config)
            with patch.object(henry_preset, "SCRIPT_DIR", root), \
                    patch("subprocess.Popen") as popen:
                with self.assertRaises(SystemExit):
                    henry_preset.main(["--slicer", str(root / "Slicer.exe")])
                popen.assert_not_called()
            Path(paths["hierarchy"]).write_bytes(b"x")
            self.assertEqual(henry_preset._input_paths(config)["hierarchy"],
                             Path(paths["hierarchy"]))
            config.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot read atlas config"):
                henry_preset._input_paths(config)

    def test_incomplete_checkout_is_reported_before_launch(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(henry_preset, "SCRIPT_DIR", Path(folder)), \
                patch("subprocess.Popen") as popen:
            with self.assertRaisesRegex(FileNotFoundError, "armins.py, arm_hierarchy.py"):
                henry_preset._checkout_files()
            with self.assertRaises(SystemExit):
                henry_preset.main([])
            popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
