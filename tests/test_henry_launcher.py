"""Bounded Henry launcher discovery checks.

Version: 0.1.2 (local/unreleased)
Last updated: 2026-10-26
Change history: CHANGELOG.md
Status: candidate
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import henry_preset


class LauncherTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
