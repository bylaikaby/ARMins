"""Show Henry's two left-cortical ARM level-6 segmentation groups in 3D Slicer.

Version: 0.1.1 (local/unreleased)
Last updated: 2026-10-26
Change history: CHANGELOG.md
Status: candidate

Run in a fresh Slicer scene: --python-script D:/ARMins/henry_preset.py
Requires the ignored local_atlas_config.json beside armins.py. No source files are written.
"""

from pathlib import Path
import sys

VERSION = "0.1.1 (local/unreleased)"
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def show():
    """Create separate left Insula (8) and left cortex (all CL L6) groups."""
    import numpy as np
    import slicer
    import armins
    from arm_hierarchy import ArmHierarchy

    config = armins._read_local_atlas_config()
    if not config:
        raise ValueError(f"explicit atlas config is required: {armins.LOCAL_ATLAS_CONFIG_PATH}")
    paths = {key: Path(value).resolve() for key, value in config.items()}
    for key, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"{key} input is unavailable: {path}")
    hierarchy = ArmHierarchy.from_file(paths["hierarchy"])
    cortical = [entry for entry in hierarchy.search("CL_", side="L", level=6)
                if entry["namespace"] == "C" and entry["abbreviation"].startswith("CL_")]
    by_id = {int(entry["index"]): entry for entry in cortical}
    insula_ids = set(armins.DEFAULT_FULL_INS_IDS["L"])
    if len(by_id) != len(cortical) or not by_id or not insula_ids <= set(by_id):
        raise ValueError("left cortical L6 identities are empty, ambiguous or missing Insula preset IDs")
    if slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLVolumeNode") or \
            slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLSegmentationNode"):
        raise RuntimeError("open a fresh Slicer scene; existing scene nodes were preserved")

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
    missing = [value for value, count in counts.items() if count == 0]
    if missing:
        raise ValueError(f"declared CL L6 labels absent from ARM6: {sorted(missing)}")
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
            segment.SetTag("ARM.HierarchySHA256", hierarchy.source_sha256)
        for key, path in paths.items():
            segmentation.SetAttribute("ARM." + key.title() + "Path", str(path))
            segmentation.SetAttribute("ARM." + key.title() + "SHA256", source_hashes[key])
        segmentation.SetAttribute("ARM.ViewerVersion", VERSION)
        segmentation.SetAttribute("ARM.Selection", name)
        segmentation.GetDisplayNode().SetVisibility(visible)
        return segmentation, masked

    insula, insula_masked = build_group(insula_ids, "Henry preset v0.1.1 - Left insula (8 CL L6)", True)
    cortex, _ = build_group(set(by_id), "Henry preset v0.1.1 - Left cortex (all CL L6)", False)
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
    print(f"Henry preset {VERSION}: left insula {len(insula_ids)} parcels visible; left cortex {len(by_id)} parcels hidden/selectable")
    return {"insula": insula, "cortex": cortex, "template": template,
            "insula_ids": sorted(insula_ids), "cortex_ids": sorted(by_id),
            "source_hashes": source_hashes}


def _running_in_slicer():
    try:
        import slicer
    except ImportError:
        return False
    return (getattr(slicer, "mrmlScene", None) is not None
            and getattr(slicer, "app", None) is not None
            and hasattr(slicer, "util"))


def main(argv=None):
    """Launch the installed Slicer application from ordinary Python."""
    import argparse
    import os
    import subprocess

    parser = argparse.ArgumentParser(description="Open Henry's two left ARM L6 groups in a fresh Slicer process")
    parser.add_argument("--slicer", type=Path, help="explicit path to Slicer.exe")
    parser.add_argument("--version", action="version", version=f"Henry preset {VERSION}")
    args = parser.parse_args(argv)
    if args.slicer is not None:
        executable = args.slicer.expanduser().resolve()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        executable = (Path(local_app_data) / "slicer.org" / "3D Slicer 5.12.0" / "Slicer.exe"
                      if local_app_data else None)
    if executable is None or not executable.is_file():
        parser.error("Slicer.exe not found; pass --slicer with the installed application path")
    process = subprocess.Popen([str(executable), "--no-splash", "--python-script",
                                str(Path(__file__).resolve())], cwd=str(SCRIPT_DIR))
    print(f"Opened Henry preset {VERSION} in Slicer (PID {process.pid})")
    return 0


if __name__ == "__main__":
    if _running_in_slicer():
        show()
    else:
        raise SystemExit(main())
