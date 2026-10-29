"""Show Henry's left ARM level-6 segmentation groups in 3D Slicer.

Version: 0.1.4 (local/unreleased)
Last updated: 2026-10-29
Change history: CHANGELOG.md
Status: candidate

Run in a fresh Slicer scene: --python-script D:/ARMins/henry_preset.py
Uses the supplied atlas_config.json beside armins.py. No source files are written.
"""

from pathlib import Path
from pathlib import PureWindowsPath
import json
import re
import shutil
import sys

VERSION = "0.1.4 (local/unreleased)"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _checkout_files():
    missing = [name for name in ("armins.py", "arm_hierarchy.py", "atlas_config.json")
               if not (SCRIPT_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"incomplete ARMins checkout at {SCRIPT_DIR}: missing "
                                f"{', '.join(missing)}; keep the repository files together")


def _input_paths(config_path=None):
    """Check the supplied inputs with stdlib before starting Slicer."""
    config_path = Path(config_path) if config_path is not None else SCRIPT_DIR / "atlas_config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read atlas config {config_path}: {exc}") from exc
    if not isinstance(config, dict) or set(config) != {"template", "atlas", "hierarchy"}:
        raise ValueError(f"atlas config {config_path} needs template, atlas and hierarchy only")
    paths = {}
    for key in ("template", "atlas", "hierarchy"):
        value = config[key]
        if not isinstance(value, str) or not value or not (
                Path(value).is_absolute() or PureWindowsPath(value).is_absolute()):
            raise ValueError(f"atlas config {config_path}: {key} must be an absolute path")
        path = (Path("//" + value.lstrip("\\").replace("\\", "/"))
                if value.startswith("\\\\") and sys.platform != "win32" else Path(value))
        try:
            with path.open("rb") as stream:
                stream.read(1)
        except OSError as exc:
            raise OSError(f"{key} input is not readable at {path}: {exc}; "
                          "check server connection and account permissions") from exc
        paths[key] = path
    return paths


def _left_l6_groups(hierarchy, insula_ids):
    """Resolve explicit left cortical and subcortical L6 IDs without guessing IDs."""
    groups = {}
    for prefix, namespace in (("CL_", "C"), ("SL_", "S")):
        entries = [entry for entry in hierarchy.search(prefix, side="L", level=6)
                   if entry["namespace"] == namespace and
                   entry["abbreviation"].startswith(prefix)]
        by_id = {int(entry["index"]): entry for entry in entries}
        if not by_id or len(by_id) != len(entries):
            raise ValueError(f"left {namespace} L6 identities are empty or ambiguous")
        groups[namespace] = by_id
    if set(groups["C"]) & set(groups["S"]):
        raise ValueError("left cortical and subcortical L6 IDs overlap")
    if not insula_ids <= set(groups["C"]):
        raise ValueError("left cortical L6 identities are missing Insula preset IDs")
    return groups


def show():
    """Create left Insula, cortex, and combined cortex/subcortex L6 groups."""
    print(f"Henry preset {VERSION}: validating config and server inputs", flush=True)
    _checkout_files()
    paths = _input_paths()
    import numpy as np
    import slicer
    import armins
    from arm_hierarchy import ArmHierarchy

    print(f"Henry preset {VERSION}: reading hierarchy", flush=True)
    hierarchy = ArmHierarchy.from_file(paths["hierarchy"])
    insula_ids = set(armins.DEFAULT_FULL_INS_IDS["L"])
    groups = _left_l6_groups(hierarchy, insula_ids)
    by_id = {**groups["C"], **groups["S"]}
    if slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLVolumeNode") or \
            slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLSegmentationNode"):
        raise RuntimeError("open a fresh Slicer scene; existing scene nodes were preserved")

    print(f"Henry preset {VERSION}: loading template and ARM6", flush=True)
    template = slicer.util.loadVolume(str(paths["template"]), properties={"name": "NMT_v2.1_sym_SS"})
    source = slicer.util.loadLabelVolume(str(paths["atlas"]),
                                         properties={"name": "ARM_L6_source_temporary", "show": False})
    if template is None or source is None:
        raise RuntimeError("Slicer could not load the template and ARM6 volumes")
    template_array = slicer.util.arrayFromVolume(template)
    labels = np.array(slicer.util.arrayFromVolume(source), copy=True)
    if labels.ndim != 3 or not np.issubdtype(labels.dtype, np.integer) or labels.shape != template_array.shape:
        raise ValueError("template and ARM6 must be matching 3-D grids with integer labels")
    matrix = armins._node_geometry_matrix(template)
    if not np.allclose(matrix, armins._node_geometry_matrix(source), rtol=0, atol=1e-4):
        raise ValueError("template and ARM6 IJK-to-RAS geometry differ")
    counts = {value: int(np.count_nonzero(labels == value)) for value in by_id}
    missing_cortex = sorted(value for value in groups["C"] if counts[value] == 0)
    if missing_cortex:
        raise ValueError(f"declared CL L6 labels absent from ARM6: {missing_cortex}")
    missing_subcortex = sorted(value for value in groups["S"] if counts[value] == 0)
    for value in missing_subcortex:
        print(f"Henry preset {VERSION}: declared subcortical L6 ID absent from ARM6: "
              f"{value} {by_id[value]['abbreviation']}; omitted from display", flush=True)
    present_ids = set(by_id) - set(missing_subcortex)
    source_hashes = {key: armins._sha256_file(path) for key, path in paths.items()}
    import_colors = []
    palette = ((0.17, 0.65, 0.72), (0.72, 0.35, 0.67), (0.87, 0.58, 0.24),
               (0.36, 0.63, 0.31), (0.34, 0.43, 0.80), (0.80, 0.35, 0.38))

    def build_group(ids, name, visible):
        selected = [by_id[value] for value in sorted(ids)]
        masked = np.where(np.isin(labels, list(ids)), labels, 0).astype(labels.dtype, copy=False)
        slicer.util.updateVolumeFromArray(source, masked)
        colors = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", name + " import colors")
        import_colors.append(colors)
        colors.SetTypeToUser()
        colors.SetNumberOfColors(max(ids) + 1)
        colors.SetColor(0, "Background", 0.0, 0.0, 0.0, 0.0)
        for index, entry in enumerate(selected):
            colors.SetColor(int(entry["index"]), entry["abbreviation"], *palette[index % len(palette)], 1.0)
        source.GetDisplayNode().SetAndObserveColorNodeID(colors.GetID())
        segmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", name)
        segmentation.CreateDefaultDisplayNodes()
        segmentation.SetReferenceImageGeometryParameterFromVolumeNode(template)
        if not slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(source, segmentation):
            raise RuntimeError(f"Slicer could not import {name}")
        data = segmentation.GetSegmentation()
        actual_names = {data.GetSegment(data.GetNthSegmentID(i)).GetName()
                        for i in range(data.GetNumberOfSegments())}
        expected_names = {entry["abbreviation"] for entry in selected}
        if actual_names != expected_names:
            raise RuntimeError(f"{name} names differ from hierarchy: missing={sorted(expected_names-actual_names)[:8]}; unexpected={sorted(actual_names-expected_names)[:8]}")
        name_to_id = {entry["abbreviation"]: int(entry["index"]) for entry in selected}
        for i in range(data.GetNumberOfSegments()):
            segment = data.GetSegment(data.GetNthSegmentID(i))
            segment.SetTag("ARM.SourceLabelID", str(name_to_id[segment.GetName()]))
            segment.SetTag("ARM.Hemisphere", "L")
            segment.SetTag("ARM.Namespace", by_id[name_to_id[segment.GetName()]]["namespace"])
            segment.SetTag("ARM.HierarchySHA256", hierarchy.source_sha256)
        for key, path in paths.items():
            segmentation.SetAttribute("ARM." + key.title() + "Path", str(path))
            segmentation.SetAttribute("ARM." + key.title() + "SHA256", source_hashes[key])
        segmentation.SetAttribute("ARM.ViewerVersion", VERSION)
        segmentation.SetAttribute("ARM.Selection", name)
        segmentation.GetDisplayNode().SetVisibility(visible)
        return segmentation, masked

    print(f"Henry preset {VERSION}: building left segmentation groups", flush=True)
    insula, insula_masked = build_group(insula_ids, "Henry preset v0.1.4 - Left insula (8 CL L6)", True)
    cortex, _ = build_group(set(groups["C"]), "Henry preset v0.1.4 - Left cortex (all CL L6)", False)
    all_left, _ = build_group(present_ids, "Henry preset v0.1.4 - Left cortex+subcortex (present L6)", False)
    all_left.SetAttribute("ARM.DeclaredAbsentIDs", ",".join(map(str, missing_subcortex)))
    slicer.mrmlScene.RemoveNode(source)
    for colors in import_colors:
        slicer.mrmlScene.RemoveNode(colors)
    slicer.util.setSliceViewerLayers(background=template)
    slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    for plane in ("Red", "Yellow", "Green"):
        slicer.app.layoutManager().sliceWidget(plane).mrmlSliceCompositeNode().SetLabelVolumeID(None)
    slicer.util.resetSliceViews()
    center_kji = np.argwhere(insula_masked != 0).mean(axis=0)
    center_ijk = np.asarray([center_kji[2], center_kji[1], center_kji[0], 1.0])
    focus_ras = matrix @ center_ijk
    slicer.modules.markups.logic().JumpSlicesToLocation(*focus_ras[:3].tolist(), False)
    slicer.util.selectModule("SegmentEditor")
    editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    editor.setSegmentationNode(insula)
    editor.setSourceVolumeNode(template)
    print(f"Henry preset {VERSION}: left insula {len(insula_ids)} visible; left cortex {len(groups['C'])} hidden; left cortex+subcortex {len(present_ids)} hidden/selectable; {len(missing_subcortex)} declared IDs absent", flush=True)
    return {"insula": insula, "cortex": cortex, "all_left": all_left, "template": template,
            "insula_ids": sorted(insula_ids), "cortex_ids": sorted(groups["C"]),
            "all_left_ids": sorted(present_ids), "declared_absent_ids": missing_subcortex,
            "source_hashes": source_hashes}


def _running_in_slicer():
    try:
        import slicer
    except ImportError:
        return False
    return (getattr(slicer, "mrmlScene", None) is not None
            and getattr(slicer, "app", None) is not None
            and hasattr(slicer, "util"))


def _slicer_rank(path):
    name = path.parent.name.lower()
    match = re.search(r"(?:3d\s+)?slicer[\s_-]*(\d+(?:\.\d+)*)", name)
    version = tuple(int(part) for part in match.group(1).split(".")) if match else ()
    preview = bool(re.search(r"(?:preview|nightly|alpha|beta|rc|dev)", name))
    return (not preview, version, str(path).lower())


def _registry_slicer_candidates():
    """Read bounded Windows installation registrations, if available."""
    if sys.platform != "win32":
        return []
    import winreg

    found = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for key_name in (r"Software\Microsoft\Windows\CurrentVersion\App Paths\Slicer.exe",
                         r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
                         r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"):
            try:
                with winreg.OpenKey(hive, key_name) as key:
                    if key_name.endswith("Slicer.exe"):
                        found.append(Path(str(winreg.QueryValueEx(key, "")[0]).strip('"')))
                    else:
                        for index in range(winreg.QueryInfoKey(key)[0]):
                            child_name = winreg.EnumKey(key, index)
                            try:
                                with winreg.OpenKey(key, child_name) as child:
                                    display_name = winreg.QueryValueEx(child, "DisplayName")[0]
                                    if not re.match(r"^(?:3d[\s_-]*)?slicer(?:[\s_-]|\d|$)",
                                                    str(display_name).lower()):
                                        continue
                                    try:
                                        location = winreg.QueryValueEx(child, "InstallLocation")[0]
                                        if location:
                                            found.append(Path(location) / "Slicer.exe")
                                            continue
                                    except OSError:
                                        pass
                                    try:
                                        icon = winreg.QueryValueEx(child, "DisplayIcon")[0]
                                        icon_path = Path(str(icon).split(",")[0].strip('"'))
                                        if icon_path.name.lower() == "slicer.exe":
                                            found.append(icon_path)
                                    except OSError:
                                        pass
                            except (OSError, ValueError):
                                continue
            except (OSError, ValueError):
                continue
    return found


def _installed_slicer(explicit=None, *, roots=None, path_match=None, registry_candidates=None):
    """Find a local Slicer executable using bounded, nonrecursive probes."""
    import os

    if explicit is not None:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Slicer executable not found: {path}")
        return path
    if roots is None:
        roots = []
        for name in ("LOCALAPPDATA", "ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = os.environ.get(name)
            if value:
                roots.extend((Path(value), Path(value) / "slicer.org"))
    if path_match is None:
        path_match = shutil.which("Slicer.exe") or shutil.which("Slicer")
    candidates = []
    if path_match:
        candidates.append(Path(path_match))
    candidates.extend(_registry_slicer_candidates() if registry_candidates is None
                      else registry_candidates)
    for root in roots:
        root = Path(root)
        candidates.append(root / "Slicer.exe")
        if root.is_dir():
            candidates.extend(folder / "Slicer.exe" for folder in root.iterdir()
                              if folder.is_dir() and re.match(r"^(?:3d[\s_-]*)?slicer(?:[\s_-]|\d|$)",
                                                              folder.name.lower()))
    available = {path.resolve() for path in candidates
                 if path.name.lower() == "slicer.exe" and path.is_file()}
    if not available:
        raise FileNotFoundError('No installed Slicer found; pass --slicer "C:\\path\\to\\Slicer.exe"')
    return max(available, key=_slicer_rank)


def main(argv=None):
    """Launch the installed Slicer application from ordinary Python."""
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description="Open Henry's three left ARM L6 groups in a fresh Slicer process")
    parser.add_argument("--slicer", type=Path, help="explicit path to Slicer.exe")
    parser.add_argument("--version", action="version", version=f"Henry preset {VERSION}")
    args = parser.parse_args(argv)
    try:
        _checkout_files()
        _input_paths()
        executable = _installed_slicer(args.slicer)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    process = subprocess.Popen([str(executable), "--no-splash", "--python-script",
                                str(Path(__file__).resolve())], cwd=str(SCRIPT_DIR))
    print(f"Opened Henry preset {VERSION} with {executable} (PID {process.pid})")
    return 0


if __name__ == "__main__":
    if _running_in_slicer():
        import qt
        import slicer
        import traceback

        def _safe_show():
            try:
                show()
            except Exception:
                details = traceback.format_exc()
                print(details, file=sys.stderr, flush=True)
                try:
                    slicer.util.pythonConsole().show()
                except Exception:
                    pass
                qt.QMessageBox.critical(slicer.util.mainWindow(),
                                        "Henry preset startup failed", details)

        qt.QTimer.singleShot(0, _safe_show)
    else:
        raise SystemExit(main())
