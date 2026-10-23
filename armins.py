"""Create bilateral full-insula editing scopes and mirror candidates.

Version: 0.7.5 (local/unreleased)
Last updated: 2026-10-23
Change history: CHANGELOG.md
Status: experimental

Derived from an earlier standalone editor baseline. Public changes are recorded
in the repository CHANGELOG.md; see that file for source mapping and validation.
"""

from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
try:
    import numpy as np
    NUMPY_IMPORT_ERROR = None
except Exception as exc:  # Keep doctor/help/version usable in a clean Python.
    np = None
    NUMPY_IMPORT_ERROR = str(exc)
try:
    import slicer
except Exception:  # Slicer is optional for CLI preparation and array validation.
    slicer = None

VERSION = "0.7.5 (local/unreleased)"


def _runtime_provenance(nib=None):
    provenance = {
        "loader_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "processing_timezone": "UTC",
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__ if np is not None else None,
    }
    if nib is not None:
        provenance["nibabel_version"] = nib.__version__
    return provenance


def dependency_report(mode="cli"):
    """Read-only runtime preflight; never install packages or change the scene."""
    if mode not in ("cli", "gui"):
        raise ValueError("dependency mode must be cli or gui")
    checks = []

    def check(name, ready, version=None, error=None):
        checks.append({"name": name, "ready": bool(ready), "version": version,
                       "error": error if not ready else None})

    check("python", sys.version_info >= (3, 10), sys.version.split()[0],
          "Python 3.10 or newer is required")
    numpy_version = np.__version__ if np is not None else None
    numpy_parts = tuple(int(v) for v in re.findall(r"\d+", numpy_version or "")[:2])
    check("numpy", np is not None and (1, 24) <= numpy_parts < (3, 0), numpy_version,
          NUMPY_IMPORT_ERROR or "NumPy >=1.24,<3 is required")
    sibling = Path(__file__).resolve().with_name("arm_hierarchy.py")
    check("arm_hierarchy.py", sibling.is_file(), error="Keep the complete ARMins checkout together")
    if mode == "cli":
        try:
            import nibabel
            parts = tuple(int(v) for v in re.findall(r"\d+", nibabel.__version__)[:2])
            check("nibabel", (5, 1) <= parts < (6, 0), nibabel.__version__,
                  "nibabel >=5.1,<6 is required for NIfTI CLI tools")
        except Exception as exc:
            check("nibabel", False, error=str(exc))
        guidance = ["conda env create -f environment.yml", "conda activate armins-cli",
                    "Alternative: python -m pip install -r requirements.txt"]
    else:
        check("3D Slicer application", _has_slicer_scene(),
              getattr(getattr(slicer, "app", None), "applicationVersion", None),
              "Open ARMins in the 3D Slicer Python Console; pip/Conda slicer is not the application")
        for name in ("qt", "vtk"):
            try:
                module = __import__(name)
                supported = (hasattr(module.QPalette, "PlaceholderText") if name == "qt"
                             else hasattr(module, "vtkMatrix4x4"))
                check(name, supported, error="Required Slicer runtime API is unavailable")
            except Exception as exc:
                check(name, False, error=str(exc))
        guidance = ["Use the official 3D Slicer application (tested: 5.12.0).",
                    "GUI dependencies come with Slicer; repair its installation/system prerequisites if missing.",
                    "Do not install Conda/PyQt or pip slicer into Slicer's Python."]
    return {"loader_version": VERSION, "mode": mode,
            "status": "ready" if all(c["ready"] for c in checks) else "missing-dependencies",
            "ready": all(c["ready"] for c in checks), "checks": checks,
            "guidance": guidance, "writes": [], "python_executable": sys.executable}


def _environment_path(name):
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else None


REF_PATH = _environment_path("ARMINS_TEMPLATE")
ARM_PATH = _environment_path("ARMINS_ATLAS")
OUTPUT_DIR = _environment_path("ARMINS_OUTPUT_DIR") or (Path.cwd() / "outputs").resolve()
ACTIVE_OUTPUT_DIR = OUTPUT_DIR
HIERARCHY_PATH = _environment_path("ARMINS_HIERARCHY")
T1_NAME, ARM_NAME = "NMT_v2.1_sym_SS", "ARM_L6_in_NMT_v2.1_sym"
# Public source hashes identify the known NMT reference/ARM-L6 pair regardless of
# its local install path. Other inputs are handled as an explicit custom pair.
DEFAULT_TEMPLATE_SHA256 = "9E37A94C4B9E5865AABB9FD3B51DCC3B2CB16F3DAED39C967E68ACF16CF92BEE"
DEFAULT_ARM_SHA256 = "97DADAB36AED80D20B50919C707166646708109785D79F56CCE6FFD851C7B4FF"
DEFAULT_ARM_SHA256S = {
    DEFAULT_ARM_SHA256,
    "7DF7E53DF5AA1F142BF017AAD89F1FDE3C84A87A3E4F93ADC7DBDED69BC79338",
}
DEFAULT_SEG_NAMES = {"L": "ARM_INS_L6_L_working", "R": "ARM_INS_L6_R_working"}
ACTIVE_SEG_NAMES = dict(DEFAULT_SEG_NAMES)
ACTIVE_T1_NAME = T1_NAME
LAST_MIRROR_CANDIDATE = None
DEFAULT_SCOPE_IDS = {"L": "L-INS-Scope", "R": "R-INS-scope"}
SCOPE_IDS = dict(DEFAULT_SCOPE_IDS)
DEFAULT_FULL_INS_IDS = {"L": (39, 41, 42, 43, 226, 228, 229, 230),
                        "R": (539, 541, 542, 543, 726, 728, 729, 730)}
FULL_INS_IDS = dict(DEFAULT_FULL_INS_IDS)
EXPECTED_VOXELS_PER_SIDE = 30256
SCOPE_COLORS = {"L": (0.10, 0.78, 0.82), "R": (0.95, 0.48, 0.24)}
ARM_TYPES = (
    ("Iam/Iapm", 39, (0.58, 0.30, 0.78)),
    ("Iai", 41, (0.20, 0.42, 0.90)),
    ("Ial", 42, (0.18, 0.68, 0.36)),
    ("Iapl", 43, (0.88, 0.72, 0.18)),
    ("Pi", 226, (0.86, 0.32, 0.58)),
    ("Ia/Id", 228, (0.48, 0.56, 0.72)),
    ("Ig", 229, (0.88, 0.25, 0.20)),
    ("Ri", 230, (0.55, 0.38, 0.22)),
)
DEFAULT_ARM_TYPES = ARM_TYPES
ARM_SEGMENTS = tuple(
    (f"C{prefix}_{name}", label_id + offset, side, color)
    for side, prefix, offset in (("L", "L", 0), ("R", "R", 500))
    for name, label_id, color in ARM_TYPES
)
DEFAULT_ARM_SEGMENTS = ARM_SEGMENTS
ARM_SEGMENT_IDS = {f"ARM_L6_{label_id}": side
                   for _, label_id, side, _ in ARM_SEGMENTS}
ARM_MIRROR_IDS = {label_id: label_id + 500 for label_id in (39, 41, 42, 43, 226, 228, 229, 230)}
DEFAULT_ARM_MIRROR_IDS = dict(ARM_MIRROR_IDS)
ACTIVE_REGION_PROFILE = None
ACTIVE_REGION_LABEL = "insula"
PENDING_GUI_PROFILE = None
MIRROR_SYMMETRY_ATOL = 1e-5
MIRROR_HELPER_TAG = "Insula.MirrorRole"


def _discover_hierarchy_path(atlas_path=None):
    configured = _environment_path("ARMINS_HIERARCHY")
    if configured and configured.is_file():
        return configured
    if atlas_path:
        atlas = Path(atlas_path).expanduser().resolve()
        for directory in (atlas.parent, *list(atlas.parents)[:3]):
            candidate = directory / "tables_ARM" / "ARM_key_table.csv"
            if candidate.is_file():
                return candidate
    return configured


def _load_hierarchy_class(path=None):
    """Load sibling resolver without relying on the current working directory."""
    candidate = Path(path).expanduser().resolve() if path else _discover_hierarchy_path(ARM_PATH)
    resolver = None
    if "__file__" in globals():
        sibling = Path(__file__).resolve().with_name("arm_hierarchy.py")
        if sibling.is_file():
            resolver = sibling
    if resolver is None:
        for folder in sys.path:
            candidate_file = Path(folder or Path.cwd()) / "arm_hierarchy.py"
            if candidate_file.is_file():
                resolver = candidate_file.resolve()
                break
    if resolver is None:
        raise RuntimeError(
            "ARM hierarchy support file arm_hierarchy.py is not available. "
            "Add the ARMins checkout to sys.path before executing armins.py."
        )
    spec = importlib.util.spec_from_file_location("_armins_arm_hierarchy", resolver)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load ARM hierarchy resolver: {resolver}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if candidate is None:
        raise ValueError("hierarchy CSV is not configured; pass --hierarchy or set ARMINS_HIERARCHY")
    return module.ArmHierarchy, candidate


def _validated_profile(profile):
    if not isinstance(profile, dict) or profile.get("schema") != "armins.region-profile.v1":
        raise ValueError("region profile must be an armins.region-profile.v1 dictionary")
    required = ("source_path", "source_sha256", "profile_hash", "selected",
                "left_leaves", "right_leaves", "pair_map")
    if any(key not in profile for key in required):
        raise ValueError("region profile is missing required source, identity, or pair-map fields")
    identity = {key: profile[key] for key in
                ("schema", "source_sha256", "left_node", "right_node",
                 "left_leaves", "right_leaves", "pair_map")}
    actual = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest().upper()
    if actual != str(profile["profile_hash"]).upper():
        raise ValueError("region profile hash does not match its resolved identities and pair map")
    working_side = str(profile.get("working_side", "")).upper()
    if working_side not in ("L", "R"):
        raise ValueError("region profile working_side must be L or R")
    expected_selected = profile["left_node"] if working_side == "L" else profile["right_node"]
    expected_counterpart = profile["right_node"] if working_side == "L" else profile["left_node"]
    if profile.get("selected") != expected_selected or profile.get("counterpart") != expected_counterpart:
        raise ValueError("region profile selected node/counterpart do not match its working side")
    source_path = Path(profile["source_path"]).expanduser().resolve()
    if not source_path.is_file() or _sha256_file(source_path) != str(profile["source_sha256"]).upper():
        raise ValueError("region hierarchy table is missing or its hash changed after profile selection")
    left = profile["left_leaves"]
    right = profile["right_leaves"]
    pairs = profile["pair_map"]
    if not left or not right or len(left) != len(right) or len(pairs) != len(left):
        raise ValueError("region profile must contain equal nonempty bilateral leaves and pairs")
    for side, leaves in (("L", left), ("R", right)):
        for item in leaves:
            if item.get("side") != side or int(item.get("level", 0)) != 6:
                raise ValueError(f"region profile {side} leaves must be explicit level-6 identities")
    left_ids = {int(item["index"]) for item in left}
    right_ids = {int(item["index"]) for item in right}
    pair_left = {int(item["left_id"]) for item in pairs}
    pair_right = {int(item["right_id"]) for item in pairs}
    if pair_left != left_ids or pair_right != right_ids or len(pair_left) != len(pairs) or len(pair_right) != len(pairs):
        raise ValueError("region profile pair map is not a bilateral bijection over its L6 leaves")
    return json.loads(json.dumps(profile))


def configure_region(profile=None):
    """Select the built-in insula preset or install one validated external region profile."""
    global ACTIVE_REGION_PROFILE, ACTIVE_REGION_LABEL, ACTIVE_SEG_NAMES
    global SCOPE_IDS, FULL_INS_IDS, EXPECTED_VOXELS_PER_SIDE
    global ARM_SEGMENTS, ARM_SEGMENT_IDS, ARM_MIRROR_IDS, ARM_TYPES
    if profile is None:
        ACTIVE_REGION_PROFILE = None
        ACTIVE_REGION_LABEL = "insula"
        ACTIVE_SEG_NAMES = dict(DEFAULT_SEG_NAMES)
        SCOPE_IDS = dict(DEFAULT_SCOPE_IDS)
        FULL_INS_IDS = dict(DEFAULT_FULL_INS_IDS)
        EXPECTED_VOXELS_PER_SIDE = 30256
        ARM_SEGMENTS = DEFAULT_ARM_SEGMENTS
        ARM_SEGMENT_IDS = {f"ARM_L6_{label_id}": side
                           for _, label_id, side, _ in ARM_SEGMENTS}
        ARM_MIRROR_IDS = dict(DEFAULT_ARM_MIRROR_IDS)
        ARM_TYPES = DEFAULT_ARM_TYPES
        return {"mode": "insula", "profile_hash": None}

    resolved = _validated_profile(profile)
    ACTIVE_REGION_PROFILE = resolved
    selected = resolved["selected"]
    ACTIVE_REGION_LABEL = resolved["left_node"]["abbreviation"]
    token = re.sub(r"[^A-Za-z0-9]+", "_", ACTIVE_REGION_LABEL).strip("_") or "region"
    profile_token = resolved["profile_hash"][:10]
    ACTIVE_SEG_NAMES = {side: f"ARM_HIER_{token}_{side}_working_{profile_token}" for side in ("L", "R")}
    SCOPE_IDS = {side: f"ARM_HIER_{token}_{side}_scope_{profile_token}" for side in ("L", "R")}
    FULL_INS_IDS = {
        "L": tuple(int(item["index"]) for item in resolved["left_leaves"]),
        "R": tuple(int(item["index"]) for item in resolved["right_leaves"]),
    }
    EXPECTED_VOXELS_PER_SIDE = None
    palette = (
        (0.58, 0.30, 0.78), (0.20, 0.42, 0.90), (0.18, 0.68, 0.36),
        (0.88, 0.72, 0.18), (0.86, 0.32, 0.58), (0.48, 0.56, 0.72),
        (0.88, 0.25, 0.20), (0.55, 0.38, 0.22),
    )
    paired_names = {}
    paired_colors = {}
    for i, pair in enumerate(resolved["pair_map"]):
        paired_names[int(pair["left_id"])] = pair["left_abbreviation"]
        paired_names[int(pair["right_id"])] = pair["right_abbreviation"]
        paired_colors[int(pair["left_id"])] = paired_colors[int(pair["right_id"])] = palette[i % len(palette)]
    leaves = [*resolved["left_leaves"], *resolved["right_leaves"]]
    ARM_SEGMENTS = tuple(
        (paired_names[int(leaf["index"])], int(leaf["index"]), leaf["side"],
         paired_colors[int(leaf["index"])])
        for leaf in leaves
    )
    ARM_SEGMENT_IDS = {f"ARM_L6_{label_id}": side
                       for _, label_id, side, _ in ARM_SEGMENTS}
    ARM_MIRROR_IDS = {int(item["left_id"]): int(item["right_id"])
                      for item in resolved["pair_map"]}
    ARM_TYPES = tuple((name, label_id, color) for name, label_id, side, color in ARM_SEGMENTS if side == "L")
    return {"mode": "hierarchy", "profile_hash": profile_token,
            "region": ACTIVE_REGION_LABEL, "working_side": resolved.get("working_side", "L")}


def configure(template_path=None, atlas_path=None, output_dir=None):
    """Set optional local inputs and output folder without changing scene data."""
    global REF_PATH, ARM_PATH, OUTPUT_DIR, ACTIVE_OUTPUT_DIR
    if template_path is not None:
        REF_PATH = Path(template_path).expanduser().resolve()
    if atlas_path is not None:
        ARM_PATH = Path(atlas_path).expanduser().resolve()
    if output_dir is not None:
        OUTPUT_DIR = Path(output_dir).expanduser().resolve()
    ACTIVE_OUTPUT_DIR = OUTPUT_DIR
    return {"template": str(REF_PATH) if REF_PATH else None,
            "atlas": str(ARM_PATH) if ARM_PATH else None,
            "output_dir": str(OUTPUT_DIR)}


def _has_slicer_scene():
    return (slicer is not None and getattr(slicer, "app", None) is not None
            and getattr(slicer, "mrmlScene", None) is not None)


def _require_slicer():
    """Fail clearly only when a scene or GUI operation actually needs Slicer."""
    if not _has_slicer_scene():
        raise RuntimeError("This operation needs the 3D Slicer Python environment")
    return slicer


def reflection_index_mapping(ijk_to_ras, shape_kji, atol=1e-6):
    """Return the exact voxel flip for reflection across physical RAS x=0.

    Only an axis-aligned grid whose reflected voxel centers map exactly onto
    integer voxel centers is supported. ``numpy_axis`` indexes KJI arrays.
    """
    matrix = np.asarray(ijk_to_ras, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError("IJK-to-RAS geometry must be a finite 4x4 matrix")
    if len(shape_kji) != 3 or any(int(size) <= 0 for size in shape_kji):
        raise ValueError("reference volume must have a positive 3-D KJI shape")
    if abs(np.linalg.det(matrix[:3, :3])) < 1e-12:
        raise ValueError("IJK-to-RAS geometry is singular")
    reflection = np.diag([-1.0, 1.0, 1.0, 1.0])
    voxel_map = np.linalg.inv(matrix) @ reflection @ matrix
    rounded = np.rint(voxel_map)
    if not np.allclose(voxel_map, rounded, rtol=0, atol=atol):
        raise ValueError("RAS x=0 reflection does not map voxel centers to integer indices")
    linear = rounded[:3, :3].astype(int)
    translation = rounded[:3, 3].astype(int)
    diagonal = np.diag(linear)
    if (not np.array_equal(linear, np.diag(diagonal))
            or sorted(diagonal.tolist()) != [-1, 1, 1]):
        raise ValueError("RAS x=0 reflection requires an unsupported oblique or multi-axis grid mapping")
    ijk_axis = int(np.flatnonzero(diagonal == -1)[0])
    shape_ijk = tuple(int(n) for n in shape_kji[::-1])
    expected_translation = np.zeros(3, dtype=int)
    expected_translation[ijk_axis] = shape_ijk[ijk_axis] - 1
    if not np.array_equal(translation, expected_translation):
        raise ValueError("RAS x=0 reflection is shifted relative to the reference voxel grid")
    expected_map = np.eye(4, dtype=int)
    expected_map[ijk_axis, ijk_axis] = -1
    expected_map[ijk_axis, 3] = shape_ijk[ijk_axis] - 1
    if not np.array_equal(rounded.astype(int), expected_map):
        raise ValueError("RAS x=0 reflection has an unsupported voxel-index transform")
    return {
        "plane": "RAS x=0",
        "ijk_axis": ijk_axis,
        "numpy_axis": 2 - ijk_axis,
        "shape_kji": [int(n) for n in shape_kji],
        "voxel_index_matrix": expected_map.tolist(),
    }


def reflect_kji_array(array, mapping):
    """Reflect a full-grid KJI array using the verified integer voxel flip."""
    values = np.asarray(array)
    expected = tuple(mapping["shape_kji"])
    if values.ndim != 3 or values.shape != expected:
        raise ValueError(f"array must have reference KJI shape {expected}; got {values.shape}")
    return np.flip(values, axis=int(mapping["numpy_axis"])).copy()


def integer_lattice_offset(reference_ijk_to_ras, segment_ijk_to_ras, atol=1e-6):
    """Resolve a segment image to the reference lattice without interpolation."""
    reference = np.asarray(reference_ijk_to_ras, dtype=float)
    segment = np.asarray(segment_ijk_to_ras, dtype=float)
    if reference.shape != (4, 4) or segment.shape != (4, 4):
        raise ValueError("reference and segment geometries must be 4x4 matrices")
    transform = np.linalg.inv(reference) @ segment
    if not np.allclose(transform[:3, :3], np.eye(3), rtol=0, atol=atol):
        raise ValueError("segment spacing or orientation differs from the reference lattice")
    offset = np.rint(transform[:3, 3]).astype(int)
    if not np.allclose(transform[:3, 3], offset, rtol=0, atol=atol):
        raise ValueError("segment origin is shifted off the reference voxel lattice")
    expected = np.eye(4)
    expected[:3, 3] = offset
    if not np.allclose(transform, expected, rtol=0, atol=atol):
        raise ValueError("segment geometry cannot be represented as an integer voxel offset")
    return offset.tolist()


def embed_segment_mask(cropped_kji, extent_ijk, offset_ijk, reference_shape_kji):
    """Place a cropped segment mask on the reference grid, refusing lost foreground."""
    cropped = np.asarray(cropped_kji, dtype=bool)
    reference_shape = tuple(int(size) for size in reference_shape_kji)
    if cropped.ndim != 3:
        raise ValueError("cropped segment mask must be three dimensional")
    extent = tuple(int(v) for v in extent_ijk)
    if len(extent) != 6 or any(extent[i] > extent[i + 1] for i in (0, 2, 4)):
        raise ValueError("segment extent must contain valid inclusive IJK bounds")
    expected_shape = (extent[5] - extent[4] + 1,
                      extent[3] - extent[2] + 1,
                      extent[1] - extent[0] + 1)
    if cropped.shape != expected_shape:
        raise ValueError(f"cropped mask shape {cropped.shape} disagrees with segment extent {expected_shape}")
    offset = np.asarray(offset_ijk, dtype=int)
    if offset.shape != (3,):
        raise ValueError("integer lattice offset must contain three IJK values")
    start_ijk = np.asarray([extent[0], extent[2], extent[4]], dtype=int) + offset
    end_ijk = start_ijk + np.asarray([cropped.shape[2], cropped.shape[1], cropped.shape[0]])
    ref_ijk_shape = np.asarray(reference_shape[::-1])
    clipped_start = np.maximum(start_ijk, 0)
    clipped_end = np.minimum(end_ijk, ref_ijk_shape)
    output = np.zeros(reference_shape, dtype=bool)
    foreground = int(cropped.sum())
    if np.any(clipped_start >= clipped_end):
        if foreground:
            raise ValueError(f"segment has {foreground} foreground voxels outside the reference field of view")
        return output
    src_start = clipped_start - start_ijk
    src_end = src_start + (clipped_end - clipped_start)
    src_slices = (slice(src_start[2], src_end[2]),
                  slice(src_start[1], src_end[1]),
                  slice(src_start[0], src_end[0]))
    dst_slices = (slice(clipped_start[2], clipped_end[2]),
                  slice(clipped_start[1], clipped_end[1]),
                  slice(clipped_start[0], clipped_end[0]))
    output[dst_slices] = cropped[src_slices]
    retained = int(output.sum())
    if retained != foreground:
        raise ValueError(f"reference field of view loses segment foreground: {foreground-retained} of {foreground} voxels")
    return output


def validate_template_symmetry(template, mapping, atol=MIRROR_SYMMETRY_ATOL):
    """Measure full-volume intensity symmetry and reject values beyond tolerance."""
    values = np.asarray(template)
    reflected = reflect_kji_array(values, mapping)
    if not np.isfinite(values).all():
        raise ValueError("template contains non-finite intensity values")
    difference = np.abs(values.astype(np.float64) - reflected.astype(np.float64))
    max_abs = float(difference.max(initial=0.0))
    rms = float(np.sqrt(np.mean(np.square(difference))))
    unequal = int(np.count_nonzero(difference > atol))
    report = {"max_abs_difference": max_abs, "rms_difference": rms,
              "voxels_over_tolerance": unequal, "atol": float(atol)}
    if unequal:
        raise ValueError(
            f"template is not symmetric within atol={atol:g}: "
            f"max_abs={max_abs:g}, rms={rms:g}, voxels_over_tolerance={unequal}")
    return report


def validate_atlas_symmetry(arm_l6, mapping):
    """Require exact reflected equality for the full insula scopes and 8 ARM pairs."""
    labels = np.asarray(arm_l6)
    if labels.ndim != 3 or labels.shape != tuple(mapping["shape_kji"]):
        raise ValueError("ARM L6 atlas must match the reference 3-D KJI grid")
    reflected = reflect_kji_array(labels, mapping)
    pairs = []
    mismatches = []
    for left_id, right_id in ARM_MIRROR_IDS.items():
        mismatch = int(np.count_nonzero((reflected == left_id) != (labels == right_id)))
        pairs.append({"left_id": left_id, "right_id": right_id, "mismatch_voxels": mismatch})
        if mismatch:
            mismatches.append(f"{left_id}->{right_id}:{mismatch}")
    scope_left = np.isin(reflected, FULL_INS_IDS["L"])
    scope_right = np.isin(labels, FULL_INS_IDS["R"])
    scope_mismatch = int(np.count_nonzero(scope_left != scope_right))
    if scope_mismatch:
        mismatches.append(f"scope:{scope_mismatch}")
    if mismatches:
        raise ValueError("ARM L/R atlas symmetry failed: " + ", ".join(mismatches))
    return {"scope_mismatch_voxels": scope_mismatch, "pairs": pairs}


def validate_partition(scope_mask, parcel_masks):
    """Require parcels to partition the same-side scope with no gaps, overlaps or leaks."""
    scope = np.asarray(scope_mask, dtype=bool)
    if scope.ndim != 3:
        raise ValueError("scope mask must be a 3-D array")
    names = list(parcel_masks)
    if not names:
        raise ValueError("no parcel segments were supplied for partition validation")
    masks = []
    for name in names:
        mask = np.asarray(parcel_masks[name], dtype=bool)
        if mask.shape != scope.shape:
            raise ValueError(f"parcel {name!r} shape {mask.shape} differs from scope {scope.shape}")
        masks.append(mask)
    counts = np.sum(np.stack(masks, axis=0), axis=0, dtype=np.uint16)
    gap_mask = scope & (counts == 0)
    overlap_mask = scope & (counts > 1)
    leak_mask = (counts > 0) & ~scope
    overlaps = []
    for i, first in enumerate(names):
        for j in range(i + 1, len(names)):
            n = int(np.count_nonzero(masks[i] & masks[j]))
            if n:
                overlaps.append({"first": first, "second": names[j], "voxels": n})
    report = {
        "scope_voxels": int(scope.sum()),
        "parcel_union_voxels": int(np.count_nonzero(counts > 0)),
        "gap_voxels": int(gap_mask.sum()),
        "overlap_voxels": int(overlap_mask.sum()),
        "leak_voxels": int(leak_mask.sum()),
        "overlap_pairs": overlaps,
    }
    if report["gap_voxels"] or report["overlap_voxels"] or report["leak_voxels"]:
        raise ValueError(
            "source parcel partition invalid: "
            f"gaps={report['gap_voxels']}, overlaps={report['overlap_voxels']} "
            f"across pairs={overlaps}, leaks={report['leak_voxels']}")
    return report


def mirrored_segment_identity(segment_id, name, side, tags=None):
    """Resolve a source segment to its explicit opposite-side ID and display name."""
    side = str(side).upper()
    if side not in SCOPE_IDS:
        raise ValueError("side must be L or R")
    tags = tags or {}
    other = "R" if side == "L" else "L"
    if segment_id == SCOPE_IDS[side]:
        return SCOPE_IDS[other], SCOPE_IDS[other], "scope"
    if segment_id in SCOPE_IDS.values():
        raise ValueError(f"wrong-side scope segment {segment_id!r} in {side} source node")
    if segment_id.startswith("ARM_L6_"):
        source_label_id = int(segment_id.removeprefix("ARM_L6_"))
        entry = next((item for item in ARM_SEGMENTS if item[1] == source_label_id), None)
        if entry is None:
            raise ValueError(f"unknown ARM segment ID {segment_id!r}; refusing to drop or guess it")
        expected_name, _, label_side, _ = entry
        if label_side != side:
            raise ValueError(f"wrong-side ARM segment {segment_id!r} in {side} source node")
        if name != expected_name:
            raise ValueError(f"ARM segment {segment_id!r} has unexpected name {name!r}; expected {expected_name!r}")
        if tags.get(MIRROR_HELPER_TAG) is not None:
            raise ValueError(f"official ARM segment {segment_id!r} cannot be tagged as a helper mask")
        if side == "L":
            target_id = ARM_MIRROR_IDS.get(source_label_id)
        else:
            target_id = next((left_id for left_id, right_id in ARM_MIRROR_IDS.items()
                              if right_id == source_label_id), None)
        target_entry = next((item for item in ARM_SEGMENTS if item[1] == target_id), None)
        if target_entry is None:
            raise ValueError(f"no official ARM mirror mapping for {segment_id!r}")
        return f"ARM_L6_{target_id}", target_entry[0], "parcel"
    prefix = side + "-"
    if not segment_id.startswith(prefix) or name != segment_id:
        wrong_prefix = other + "-"
        if segment_id.startswith(wrong_prefix) or name.startswith("C" + other + "_"):
            raise ValueError(f"wrong-side custom segment {segment_id!r}/{name!r} in {side} source node")
        raise ValueError(f"unmapped segment {segment_id!r}/{name!r}; custom parcels must use {side}-<name>")
    suffix = segment_id[len(prefix):]
    if not suffix.strip():
        raise ValueError(f"custom parcel ID {segment_id!r} has an empty name")
    if tags.get(MIRROR_HELPER_TAG) not in (None, "helper_mask"):
        raise ValueError(f"unsupported mirror role {tags[MIRROR_HELPER_TAG]!r} on {segment_id!r}")
    role = "helper_mask" if tags.get(MIRROR_HELPER_TAG) == "helper_mask" else "parcel"
    return f"{other}-{suffix}", f"{other}-{suffix}", role


def validate_input_arrays(template_array, arm_l6, template_ijk_to_ras, atlas_ijk_to_ras):
    """Validate one intensity grid and a 3-D integer ARM-L6-compatible atlas."""
    template = np.asarray(template_array)
    labels = np.asarray(arm_l6)
    if template.ndim != 3 or not np.isfinite(template).all():
        raise ValueError("template must be a finite 3-D intensity volume")
    if labels.ndim != 3 or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("atlas must be a 3-D integer label volume; resample outside this tool")
    if template.shape != labels.shape:
        raise ValueError(f"template/atlas array shape mismatch: {template.shape} vs {labels.shape}")
    required = [label_id for _, label_id, _, _ in ARM_SEGMENTS]
    counts = {label_id: int(np.count_nonzero(labels == label_id)) for label_id in required}
    missing = [label_id for label_id, count in counts.items() if count == 0]
    if missing:
        label_context = ("selected hierarchy region" if ACTIVE_REGION_PROFILE is not None
                         else "ARM level-6 atlas")
        raise ValueError(f"{label_context} is missing required source IDs (IDs are absent): {missing}")
    template_matrix = np.asarray(template_ijk_to_ras, dtype=float)
    atlas_matrix = np.asarray(atlas_ijk_to_ras, dtype=float)
    if (template_matrix.shape != (4, 4) or atlas_matrix.shape != (4, 4)
            or not np.isfinite(template_matrix).all() or not np.isfinite(atlas_matrix).all()):
        raise ValueError("template and atlas must have finite 4x4 IJK-to-RAS geometry")
    if not np.allclose(template_matrix, atlas_matrix, rtol=0, atol=1e-4):
        raise ValueError("template and atlas IJK-to-RAS geometry differ; regrid/align externally first")
    return counts


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load_nifti_inputs(template_path, atlas_path, level=6):
    """Load and validate a template plus 3-D or multi-level ARM NIfTI input."""
    try:
        import nibabel as nib
    except ImportError as exc:
        raise RuntimeError("Install nibabel to use the command-line NIfTI tools") from exc
    template_path, atlas_path = Path(template_path).expanduser().resolve(), Path(atlas_path).expanduser().resolve()
    if not template_path.is_file():
        raise FileNotFoundError(f"template file not found: {template_path}")
    if not atlas_path.is_file():
        raise FileNotFoundError(f"ARM atlas file not found: {atlas_path}")
    template_image, atlas_image = nib.load(str(template_path)), nib.load(str(atlas_path))
    template = np.asanyarray(template_image.dataobj)
    atlas_all_levels = np.asanyarray(atlas_image.dataobj)
    labels, level_form = extract_arm_level(atlas_all_levels, level=level)
    counts = validate_input_arrays(template, labels, template_image.affine, atlas_image.affine)
    return {
        "nibabel": nib,
        "template_path": template_path,
        "atlas_path": atlas_path,
        "template_image": template_image,
        "atlas_image": atlas_image,
        "template": template,
        "atlas_all_levels": atlas_all_levels,
        "labels": labels,
        "level_form": level_form,
        "counts": counts,
    }


def extract_arm_level(atlas, level=6):
    """Extract explicit ARM level 6 from a 3-D, 4-D, or original 5-D atlas.

    Accepted layouts are spatial 3-D labels, spatial+(6,) and spatial+(1, 6).
    All other added axes are ambiguous and rejected.
    """
    values = np.asarray(atlas)
    if level != 6:
        raise ValueError("this tool currently supports only explicit ARM --level 6")
    if values.ndim == 3:
        labels, form = values, "already-3D-level-6"
    elif values.ndim == 4 and values.shape[-1] == 6:
        labels, form = values[..., 5], "4D-spatial-plus-six-levels"
    elif values.ndim == 5 and values.shape[-2:] == (1, 6):
        labels, form = values[..., 0, 5], "5D-spatial-plus-singleton-and-six-levels"
    else:
        raise ValueError(
            f"ambiguous ARM atlas shape {values.shape}; expected 3-D L6, spatial+(6,), or spatial+(1,6)"
        )
    if not np.issubdtype(labels.dtype, np.integer):
        raise ValueError(f"ARM level-6 atlas must contain integer labels; got {labels.dtype}")
    return labels, form


def _resolved_inputs(template_path=None, atlas_path=None):
    template = Path(template_path).expanduser().resolve() if template_path else REF_PATH
    atlas = Path(atlas_path).expanduser().resolve() if atlas_path else ARM_PATH
    if template is None:
        raise ValueError("template is not configured; pass --template or set ARMINS_TEMPLATE")
    if atlas is None:
        raise ValueError("ARM atlas is not configured; pass --atlas or set ARMINS_ATLAS")
    return template, atlas


def check_inputs(template_path=None, atlas_path=None, level=6, region_profile=None):
    """Read-only validation used by the portable CLI and operator receipt."""
    configure_region(region_profile)
    template_path, atlas_path = _resolved_inputs(template_path, atlas_path)
    loaded = _load_nifti_inputs(template_path, atlas_path, level=level)
    return {
        **_runtime_provenance(loaded["nibabel"]),
        "status": "validated",
        "template_path": str(template_path),
        "template_sha256": _sha256_file(template_path),
        "atlas_path": str(atlas_path),
        "atlas_sha256": _sha256_file(atlas_path),
        "template_shape": list(loaded["template"].shape),
        "atlas_source_shape": list(loaded["atlas_all_levels"].shape),
        "level": int(level),
        "level6_shape": list(loaded["labels"].shape),
        "level6_form": loaded["level_form"],
        "affine": loaded["template_image"].affine.tolist(),
        "level6_counts": loaded["counts"],
        "region_profile": ACTIVE_REGION_PROFILE,
        "dry_run": True,
        "writes": [],
    }


def prepare_level6(template_path=None, atlas_path=None, level=6, output_dir=None, dry_run=False,
                   region_profile=None):
    """Extract one ARM L6 NIfTI and a receipt; preserve all input files."""
    configure_region(region_profile)
    template_path, atlas_path = _resolved_inputs(template_path, atlas_path)
    loaded = _load_nifti_inputs(template_path, atlas_path, level=level)
    if loaded["level_form"] == "already-3D-level-6":
        return {
            **_runtime_provenance(loaded["nibabel"]),
            "status": "already-prepared",
            "template_path": str(template_path),
            "template_sha256": _sha256_file(template_path),
            "template_shape": list(loaded["template"].shape),
            "atlas_path": str(atlas_path),
            "atlas_sha256": _sha256_file(atlas_path),
            "atlas_source_shape": list(loaded["atlas_all_levels"].shape),
            "level": int(level),
            "level_form": loaded["level_form"],
            "level6_shape": list(loaded["labels"].shape),
            "affine": loaded["atlas_image"].affine.tolist(),
            "level6_counts": loaded["counts"],
            "region_profile": ACTIVE_REGION_PROFILE,
            "output_path": str(atlas_path),
            "dry_run": False,
            "writes": [],
        }
    destination_dir = (Path(output_dir).expanduser().resolve() if output_dir
                       else OUTPUT_DIR)
    output_path = destination_dir / "ARM_L6.nii.gz"
    receipt_path = destination_dir / "armins_prepare_receipt.json"
    result = {
        **_runtime_provenance(loaded["nibabel"]),
        "status": "dry-run" if dry_run else "prepared",
        "template_path": str(template_path),
        "template_sha256": _sha256_file(template_path),
        "atlas_path": str(atlas_path),
        "atlas_sha256": _sha256_file(atlas_path),
        "atlas_source_shape": list(loaded["atlas_all_levels"].shape),
        "level": 6,
        "level_form": loaded["level_form"],
        "template_shape": list(loaded["template"].shape),
        "level6_shape": list(loaded["labels"].shape),
        "affine": loaded["atlas_image"].affine.tolist(),
        "level6_counts": loaded["counts"],
        "region_profile": ACTIVE_REGION_PROFILE,
        "output_path": str(output_path),
        "receipt_path": str(receipt_path),
        "dry_run": bool(dry_run),
        "writes": [] if dry_run else [str(output_path), str(receipt_path)],
    }
    if dry_run:
        return result
    destination_dir.mkdir(parents=True, exist_ok=True)
    if output_path.exists() or receipt_path.exists():
        raise FileExistsError(f"refusing to overwrite {output_path} or {receipt_path}")
    nib = loaded["nibabel"]
    header = loaded["atlas_image"].header.copy()
    header.set_data_shape(loaded["labels"].shape)
    header.set_data_dtype(loaded["labels"].dtype)
    output_image = nib.Nifti1Image(loaded["labels"], loaded["atlas_image"].affine, header)
    qform, qcode = loaded["atlas_image"].get_qform(coded=True)
    sform, scode = loaded["atlas_image"].get_sform(coded=True)
    if qform is not None:
        output_image.set_qform(qform, int(qcode))
    if sform is not None:
        output_image.set_sform(sform, int(scode))
    output_image.header.set_data_dtype(loaded["labels"].dtype)
    receipt = {
        **result,
        "output_sha256": None,
        "output_bytes": None,
    }
    created = []
    try:
        for path in (output_path, receipt_path):
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            created.append(path)
        nib.save(output_image, str(output_path))
        receipt["output_sha256"] = _sha256_file(output_path)
        receipt["output_bytes"] = output_path.stat().st_size
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return receipt


def _input_names(template_path, atlas_path, region_profile=None):
    template_path, atlas_path = Path(template_path).resolve(), Path(atlas_path).resolve()
    template_hash, atlas_hash = _sha256_file(template_path), _sha256_file(atlas_path)
    profile = region_profile if region_profile is not None else ACTIVE_REGION_PROFILE
    default_pair = (template_hash == DEFAULT_TEMPLATE_SHA256
                    and atlas_hash in DEFAULT_ARM_SHA256S)
    input_signature = hashlib.sha256(
        f"{template_path}|{template_hash}|{atlas_path}|{atlas_hash}".encode("utf-8")
    ).hexdigest()[:10]
    signature = (input_signature if profile is None else hashlib.sha256(
        f"{input_signature}|region={profile['profile_hash']}".encode("utf-8")
    ).hexdigest()[:10])
    suffix = "" if default_pair and profile is None else f"_{signature}"
    template_name = T1_NAME if default_pair else f"NMT_template_{input_signature}"
    atlas_name = ARM_NAME if default_pair else f"ARM_L6_{input_signature}"
    if profile is None:
        segment_names = {side: f"{name}{suffix}" for side, name in DEFAULT_SEG_NAMES.items()}
    else:
        token = re.sub(r"[^A-Za-z0-9]+", "_", profile["left_node"]["abbreviation"]).strip("_") or "region"
        segment_names = {side: f"ARM_HIER_{token}_{side}_working_{signature}" for side in ("L", "R")}
    return {
        "signature": signature,
        "input_signature": input_signature,
        "template_hash": template_hash,
        "atlas_hash": atlas_hash,
        "template_name": template_name,
        "atlas_name": atlas_name,
        "segment_names": segment_names,
        "default_pair": default_pair,
        "region_profile": profile,
        "region_profile_hash": profile["profile_hash"] if profile else None,
    }


def _node_geometry_matrix(node):
    import vtk
    matrix = vtk.vtkMatrix4x4()
    node.GetIJKToRASMatrix(matrix)
    return np.asarray([[matrix.GetElement(i, j) for j in range(4)] for i in range(4)])


def build_scope_masks(arm_l6):
    """Return full-insula left/right masks for a Slicer KJI integer array."""
    labels = np.asarray(arm_l6)
    if labels.ndim != 3 or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("ARM L6 must be a 3-D integer label array")
    masks = {side: np.isin(labels, ids) for side, ids in FULL_INS_IDS.items()}
    if np.any(masks["L"] & masks["R"]):
        raise ValueError("left and right full-insula masks overlap")
    return masks


def build_arm6_masks(arm_l6):
    """Return the 16 bilateral seed masks keyed by source ARM label ID."""
    labels = np.asarray(arm_l6)
    if labels.ndim != 3 or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("ARM L6 must be a 3-D integer label array")
    return {label_id: labels == label_id for _, label_id, _, _ in ARM_SEGMENTS}


def seed_arm6_segments(segmentation, arm_l6, source_volume, side):
    """Add missing seeds for one hemisphere; never replace existing edits."""
    seed_side = side.upper()
    if seed_side not in SCOPE_IDS:
        raise ValueError("side must be L or R")
    masks = build_arm6_masks(arm_l6)
    data = segmentation.GetSegmentation()
    added = []
    for name, label_id, label_side, color in ARM_SEGMENTS:
        if label_side != seed_side:
            continue
        segment_id = f"ARM_L6_{label_id}"
        if data.GetSegment(segment_id) is not None:
            continue
        for index in range(data.GetNumberOfSegments()):
            other_id = data.GetNthSegmentID(index)
            if data.GetSegment(other_id).GetName() == name:
                raise RuntimeError(f"display name {name!r} already exists as {other_id}; preserving it")
        data.AddEmptySegment(segment_id, name, color)
        segment = data.GetSegment(segment_id)
        segment.SetTag("ARM.SourceLabelID", str(label_id))
        segment.SetTag("ARM.Hemisphere", label_side)
        if ACTIVE_REGION_PROFILE is not None:
            segment.SetTag("Insula.RegionProfileHash", ACTIVE_REGION_PROFILE["profile_hash"])
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            masks[label_id].astype(np.uint8), segmentation, segment_id, source_volume)
        added.append(segment_id)
    return added


def _find(name):
    return _require_slicer().mrmlScene.GetFirstNodeByName(name)


def _load_or_reuse(path, name, loader):
    node = _find(name)
    if node:
        storage = node.GetStorageNode()
        current = Path(storage.GetFileName()).resolve() if storage and storage.GetFileName() else None
        if current != path.resolve():
            raise RuntimeError(f"scene node {name!r} already exists from {current}; resolve it manually")
        return node
    result = loader(str(path), properties={"name": name})
    # Normalize older Slicer APIs or compatible wrappers that return (success, node).
    if isinstance(result, tuple):
        if len(result) != 2 or not isinstance(result[0], bool):
            raise RuntimeError(f"unexpected result loading {path}: {type(result).__name__}")
        success, result = result
        if not success or result is None:
            raise RuntimeError(f"Slicer failed to load {path}")
    if result is None or not hasattr(result, "GetImageData"):
        raise RuntimeError(f"Slicer did not return a volume node for {path}")
    return result


def add_parcel(name, side, color=(0.95, 0.75, 0.25)):
    """Add one empty parcel segment, e.g. add_parcel('candidate', 'L')."""
    side = side.upper()
    if side not in SCOPE_IDS or not name.strip() or name.strip().casefold() == "ins-scope":
        raise ValueError("side must be L/R and name must be a non-scope parcel name")
    segmentation = _find(ACTIVE_SEG_NAMES[side])
    if segmentation is None:
        raise RuntimeError("run this loader first")
    segment_id = f"{side}-{name.strip()}"
    if segmentation.GetSegmentation().GetSegment(segment_id):
        raise RuntimeError(f"segment already exists: {segment_id}")
    segmentation.GetSegmentation().AddEmptySegment(segment_id, segment_id, color)
    return segment_id


def use_scope(side, target_segment_id=None):
    """Restrict Segment Editor to one scope; scope segments are hidden during drawing."""
    if not isinstance(side, str):
        raise ValueError("side must be L or R")
    side = side.upper()
    if side not in SCOPE_IDS:
        raise ValueError("side must be L or R")
    segmentation = _find(ACTIVE_SEG_NAMES[side])
    if segmentation is None:
        raise RuntimeError("run this loader first")
    segmentation_data = segmentation.GetSegmentation()
    scope_id = SCOPE_IDS[side]
    if segmentation_data.GetSegment(scope_id) is None:
        raise RuntimeError(f"scope segment missing: {scope_id}")
    resolved_target = None
    if target_segment_id:
        target_segment_id = str(target_segment_id).strip()
        ids = [segmentation_data.GetNthSegmentID(i)
               for i in range(segmentation_data.GetNumberOfSegments())]
        matches = [sid for sid in ids
                   if sid == target_segment_id
                   or segmentation_data.GetSegment(sid).GetName() == target_segment_id]
        if len(matches) != 1:
            raise ValueError(f"target {target_segment_id!r} is not one unique existing segment ID/name")
        resolved_target = matches[0]
        target_side = ARM_SEGMENT_IDS.get(resolved_target)
        if target_side is None and resolved_target.startswith(("L-", "R-")):
            target_side = resolved_target[0]
        if resolved_target in SCOPE_IDS.values() or target_side != side:
            raise ValueError(f"target must be an existing {side}- parcel, never a scope")

    slicer.util.selectModule("SegmentEditor")
    editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    editor.setSegmentationNode(segmentation)
    editor.setSourceVolumeNode(_find(ACTIVE_T1_NAME))
    parameters = editor.mrmlSegmentEditorNode()
    modify_state = parameters.StartModify()
    try:
        parameters.SetMaskSegmentID(scope_id)
        parameters.SetMaskMode(slicer.vtkMRMLSegmentationNode.EditAllowedInsideSingleSegment)
        parameters.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteVisibleSegments)
        parameters.SetSelectedSegmentID(resolved_target or "")
        parameters.SetActiveEffectName("")
    finally:
        parameters.EndModify(modify_state)
    if (parameters.GetMaskSegmentID() != scope_id
            or parameters.GetMaskMode() != slicer.vtkMRMLSegmentationNode.EditAllowedInsideSingleSegment):
        raise RuntimeError("Segment Editor did not retain the requested mask; verify Editable area in the UI")
    segmentation.GetDisplayNode().SetSegmentVisibility(scope_id, False)
    return (f"Mask applied: mode={parameters.GetMaskMode()}, segment={parameters.GetMaskSegmentID()}; "
            f"target={resolved_target or 'none'}; no effect active")


def _bind_segmentation_source(segmentation, node_name, template_path, atlas_path, source_info,
                              new_node=False):
    expected = {
        "Insula.SourceSignature": source_info["signature"],
        "Insula.TemplatePath": str(Path(template_path).resolve()),
        "Insula.TemplateSHA256": source_info["template_hash"],
        "Insula.ARMAtlasPath": str(Path(atlas_path).resolve()),
        "Insula.ARMAtlasSHA256": source_info["atlas_hash"],
        "Insula.RegionProfileHash": source_info.get("region_profile_hash") or "insula-default",
        "Insula.RegionProfile": json.dumps(source_info.get("region_profile"), sort_keys=True)
        if source_info.get("region_profile") else "",
    }
    signature = segmentation.GetAttribute("Insula.SourceSignature")
    if signature and signature != source_info["signature"]:
        raise RuntimeError(f"{node_name} is bound to different inputs; preserve it and choose another source pair")
    if not signature and not source_info["default_pair"] and not new_node:
        raise RuntimeError(f"{node_name} has no input binding; custom inputs will not reuse it")
    old_profile_text = segmentation.GetAttribute("Insula.RegionProfile")
    if old_profile_text:
        old_profile = _validated_profile(json.loads(old_profile_text))
        if old_profile["profile_hash"] != source_info["region_profile_hash"]:
            raise RuntimeError(f"{node_name} has conflicting hierarchy profile binding; existing node was preserved")
    for key, value in expected.items():
        if key == "Insula.RegionProfile":
            continue
        old = segmentation.GetAttribute(key)
        if old and old != value:
            raise RuntimeError(f"{node_name} has conflicting {key}; existing node was preserved")
    for key, value in expected.items():
        segmentation.SetAttribute(key, value)


def _segment_tags(segment):
    """Read only tags needed for validation; candidate copies retain all metadata."""
    import vtk
    result = {}
    for key in ("ARM.SourceLabelID", "ARM.Hemisphere", MIRROR_HELPER_TAG):
        value = vtk.mutable("")
        if segment.GetTag(key, value):
            result[key] = str(value)
    return result


def _resolve_mirror_source(side, source_node=None):
    if not isinstance(side, str) or side.upper() not in SCOPE_IDS:
        raise ValueError("side must be L or R")
    side = side.upper()
    if source_node is None:
        name = ACTIVE_SEG_NAMES.get(side, DEFAULT_SEG_NAMES[side])
        node = _find(name)
    elif isinstance(source_node, str):
        node = _find(source_node)
    else:
        node = source_node
    if node is None or not node.IsA("vtkMRMLSegmentationNode"):
        raise ValueError("source_node must be a loaded segmentation node or its scene name")
    return side, node


def _candidate_name_available(scene, base_name):
    """Choose a unique name without mutating/reserving a name during dry-run."""
    name = base_name
    suffix = 1
    while scene.GetFirstNodeByName(name) is not None:
        name = f"{base_name}_{suffix}"
        suffix += 1
    return name


def _segment_mask_on_reference_grid(segmentation, segment_id, reference_volume, reference_matrix, shape_kji):
    """Read native segment voxels, check their lattice, and embed by integer offset."""
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    image = slicer.vtkOrientedImageData()
    segmentation.GetBinaryLabelmapRepresentation(segment_id, image)
    scalars = image.GetPointData().GetScalars()
    if scalars is None:
        return np.zeros(shape_kji, dtype=bool)
    if scalars.GetNumberOfComponents() != 1:
        raise ValueError(f"segment {segment_id!r} binary labelmap is not scalar")
    extent = tuple(int(v) for v in image.GetExtent())
    if len(extent) != 6 or any(extent[i] > extent[i + 1] for i in (0, 2, 4)):
        if int(scalars.GetNumberOfTuples()) == 0:
            return np.zeros(shape_kji, dtype=bool)
        raise ValueError(f"segment {segment_id!r} has invalid native image extent {extent}")
    segment_matrix_vtk = vtk.vtkMatrix4x4()
    image.GetImageToWorldMatrix(segment_matrix_vtk)
    segment_matrix = np.asarray([[segment_matrix_vtk.GetElement(i, j) for j in range(4)]
                                 for i in range(4)], dtype=float)
    offset = integer_lattice_offset(reference_matrix, segment_matrix)
    array = vtk_to_numpy(scalars)
    expected = (extent[5] - extent[4] + 1,
                extent[3] - extent[2] + 1,
                extent[1] - extent[0] + 1)
    if array.size != int(np.prod(expected)):
        raise ValueError(f"segment {segment_id!r} scalar count does not match native extent")
    cropped = array.reshape(expected).astype(bool)
    full = embed_segment_mask(cropped, extent, offset, shape_kji)
    if int(full.sum()) != int(cropped.sum()):
        raise ValueError(f"segment {segment_id!r} foreground count changed on the reference grid")
    return full


def _mirror_preflight(side, source_node=None):
    """Validate all inputs and edited masks before creating any candidate node."""
    side, source = _resolve_mirror_source(side, source_node)
    source_id = source.GetID()
    if source.GetParentTransformNode():
        raise ValueError("source segmentation has a parent transform; harden it before mirroring")
    template_path = source.GetAttribute("Insula.TemplatePath")
    template_hash = source.GetAttribute("Insula.TemplateSHA256")
    atlas_path = source.GetAttribute("Insula.ARMAtlasPath")
    atlas_hash = source.GetAttribute("Insula.ARMAtlasSHA256")
    signature = source.GetAttribute("Insula.SourceSignature")
    profile_text = source.GetAttribute("Insula.RegionProfile")
    source_profile = json.loads(profile_text) if profile_text else None
    if source_profile is not None:
        source_profile = _validated_profile(source_profile)
        if ACTIVE_REGION_PROFILE is None or ACTIVE_REGION_PROFILE["profile_hash"] != source_profile["profile_hash"]:
            raise ValueError("source group is bound to a different hierarchy profile; configure that exact profile before mirroring")
    elif ACTIVE_REGION_PROFILE is not None:
        raise ValueError("insula source group cannot be mirrored while a hierarchy profile is active")
    expected_profile_hash = source_profile["profile_hash"] if source_profile else "insula-default"
    if source.GetAttribute("Insula.RegionProfileHash") != expected_profile_hash:
        raise ValueError("source group profile binding is missing or inconsistent; reload with the matching region profile")
    if not all((template_path, template_hash, atlas_path, atlas_hash, signature)):
        raise ValueError("source segmentation is missing its template/ARM input binding")
    for path, expected, label in ((template_path, template_hash, "template"),
                                  (atlas_path, atlas_hash, "ARM atlas")):
        if not Path(path).is_file():
            raise FileNotFoundError(f"bound {label} file is missing: {path}")
        actual = _sha256_file(path)
        if actual != expected.upper():
            raise ValueError(f"bound {label} hash changed: expected {expected}, found {actual}")
    source_info = _input_names(template_path, atlas_path, region_profile=source_profile)
    if source_info["signature"] != signature:
        raise ValueError("source segmentation binding signature does not match its input paths and hashes")
    if source.GetAttribute("Insula.TemplatePath") != str(Path(template_path).resolve()):
        raise ValueError("source template path binding is not normalized")
    if source.GetAttribute("Insula.ARMAtlasPath") != str(Path(atlas_path).resolve()):
        raise ValueError("source ARM atlas path binding is not normalized")

    ref = _find(source_info["template_name"])
    arm = _find(source_info["atlas_name"])
    if ref is None or arm is None:
        raise ValueError("bound template and ARM atlas must already be loaded in the current Slicer scene")
    for node, path, label in ((ref, template_path, "template"), (arm, atlas_path, "ARM atlas")):
        storage = node.GetStorageNode()
        actual_path = Path(storage.GetFileName()).resolve() if storage and storage.GetFileName() else None
        if actual_path != Path(path).resolve():
            raise ValueError(f"loaded {label} node is not bound to the source segmentation's input path")
        if node.GetParentTransformNode():
            raise ValueError(f"loaded {label} has a parent transform; harden it before mirroring")
    template = slicer.util.arrayFromVolume(ref)
    atlas = slicer.util.arrayFromVolume(arm)
    if template.shape != atlas.shape:
        raise ValueError(f"template/atlas KJI shape mismatch: {template.shape} vs {atlas.shape}")
    ref_matrix = _node_geometry_matrix(ref)
    atlas_matrix = _node_geometry_matrix(arm)
    if not np.allclose(ref_matrix, atlas_matrix, rtol=0, atol=1e-4):
        raise ValueError("loaded template and ARM atlas IJK-to-RAS geometry differ")
    mapping = reflection_index_mapping(ref_matrix, template.shape)
    template_report = validate_template_symmetry(template, mapping)
    atlas_report = validate_atlas_symmetry(atlas, mapping)

    scope_id = SCOPE_IDS[side]
    data = source.GetSegmentation()
    if data.GetSegment(scope_id) is None:
        raise ValueError(f"source segmentation is missing its {side} full-insula scope {scope_id}")
    if data.GetSegment(SCOPE_IDS["R" if side == "L" else "L"]) is not None:
        raise ValueError("source segmentation contains both hemispheric scopes; refusing ambiguous mirroring")
    expected_scope = np.isin(atlas, FULL_INS_IDS[side])
    scope_mask = _segment_mask_on_reference_grid(source, scope_id, ref, ref_matrix, template.shape)
    if not np.array_equal(scope_mask, expected_scope):
        raise ValueError("source full-insula scope differs from the bound ARM atlas on the reference grid")

    source_segments = []
    parcel_masks = {}
    seen_arm_ids = set()
    for index in range(data.GetNumberOfSegments()):
        segment_id = data.GetNthSegmentID(index)
        segment = data.GetSegment(segment_id)
        name = segment.GetName()
        tags = _segment_tags(segment)
        target_id, target_name, role = mirrored_segment_identity(segment_id, name, side, tags)
        if role == "scope":
            continue
        if segment_id.startswith("ARM_L6_"):
            label_id = int(segment_id.removeprefix("ARM_L6_"))
            if tags.get("ARM.SourceLabelID") != str(label_id) or tags.get("ARM.Hemisphere") != side:
                raise ValueError(f"ARM seed {segment_id!r} has inconsistent source-ID/hemisphere tags")
            seen_arm_ids.add(label_id)
        mask = _segment_mask_on_reference_grid(source, segment_id, ref, ref_matrix, template.shape)
        source_segments.append({
            "source_id": segment_id,
            "source_name": name,
            "target_id": target_id,
            "target_name": target_name,
            "role": role,
            "color": list(segment.GetColor()),
            "tags": tags,
            "mask": mask,
            "voxels": int(mask.sum()),
        })
        if role == "parcel":
            parcel_masks[segment_id] = mask
    required_ids = {label_id for _, label_id, label_side, _ in ARM_SEGMENTS if label_side == side}
    if seen_arm_ids != required_ids:
        raise ValueError(f"source ARM seed IDs incomplete: missing={sorted(required_ids-seen_arm_ids)}, "
                         f"unexpected={sorted(seen_arm_ids-required_ids)}")
    partition = validate_partition(scope_mask, parcel_masks)
    segment_mapping = [{k: item[k] for k in ("source_id", "source_name", "target_id", "target_name", "role", "voxels")}
                       for item in source_segments]
    target_side = "R" if side == "L" else "L"
    base_name = f"ARM_INS_L6_{target_side}_MIRROR_FROM_{side}_candidate"
    candidate_name = _candidate_name_available(slicer.mrmlScene, base_name)
    receipt = {
        "status": "candidate",
        **_runtime_provenance(),
        "slicer_version": str(getattr(slicer.app, "applicationVersion", "unknown")),
        "numpy_version": str(np.__version__),
        "source_side": side,
        "target_side": target_side,
        "source_node_id": source_id,
        "source_node_name": source.GetName(),
        "source_signature": signature,
        "template_path": str(Path(template_path).resolve()),
        "template_sha256": template_hash.upper(),
        "atlas_path": str(Path(atlas_path).resolve()),
        "atlas_sha256": atlas_hash.upper(),
        "region_profile": source_profile,
        "reflection": {**mapping, "plane": "RAS x=0"},
        "template_symmetry": template_report,
        "atlas_symmetry": atlas_report,
        "partition": partition,
        "segments": segment_mapping,
        "candidate_name": candidate_name,
    }
    return source, ref, source_segments, receipt


def mirror_side(side, source_node=None, dry_run=False):
    """Create an opposite-side mirrored candidate after complete read-only preflight.

    ``source_node`` accepts a loaded segmentation MRML node or scene name. With
    no value, the currently loaded working segmentation for ``side`` is used.
    A dry run returns the resolved preflight receipt without changing the scene.
    """
    _require_slicer()
    side, _ = _resolve_mirror_source(side, source_node)
    source, ref, source_segments, receipt = _mirror_preflight(side, source_node)
    if dry_run:
        return {**receipt, "dry_run": True}
    target_side = receipt["target_side"]
    reflected = reflection_index_mapping(_node_geometry_matrix(ref), slicer.util.arrayFromVolume(ref).shape)
    candidate = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", receipt["candidate_name"])
    try:
        candidate.SetReferenceImageGeometryParameterFromVolumeNode(ref)
        candidate.CreateDefaultDisplayNodes()
        target_scope_id = SCOPE_IDS[target_side]
        candidate_data = candidate.GetSegmentation()
        candidate_data.AddEmptySegment(target_scope_id, target_scope_id, SCOPE_COLORS[target_side])
        scope_segment = candidate_data.GetSegment(target_scope_id)
        scope_label_value = scope_segment.GetLabelValue()
        scope_segment.DeepCopyMetadata(source.GetSegmentation().GetSegment(SCOPE_IDS[side]))
        scope_segment.SetLabelValue(scope_label_value)
        scope_segment.SetName(target_scope_id)
        scope_segment.SetColor(*SCOPE_COLORS[target_side])
        scope_segment.SetTag("Insula.MirrorReceipt", json.dumps(receipt, sort_keys=True))
        scope_segment.SetTag("Insula.MirrorSourceNodeID", source.GetID())
        scope_segment.SetTag("Insula.MirrorDirection", f"{side}-to-{target_side}")
        scope_segment.SetTag("Insula.CandidateStatus", "candidate")
        scope_item = _segment_mask_on_reference_grid(
            source, SCOPE_IDS[side], ref, _node_geometry_matrix(ref), tuple(slicer.util.arrayFromVolume(ref).shape))
        slicer.util.updateSegmentBinaryLabelmapFromArray(
            reflect_kji_array(scope_item, reflected).astype(np.uint8), candidate, target_scope_id, ref)
        candidate.GetDisplayNode().SetSegmentVisibility(target_scope_id, False)
        for item in source_segments:
            segment_id = item["target_id"]
            candidate_data.AddEmptySegment(segment_id, item["target_name"], item["color"])
            segment = candidate_data.GetSegment(segment_id)
            label_value = segment.GetLabelValue()
            segment.DeepCopyMetadata(source.GetSegmentation().GetSegment(item["source_id"]))
            segment.SetLabelValue(label_value)
            segment.SetName(item["target_name"])
            segment.SetColor(*item["color"])
            source_label_id = None
            if item["source_id"].startswith("ARM_L6_"):
                source_id = int(item["source_id"].removeprefix("ARM_L6_"))
                source_label_id = (ARM_MIRROR_IDS[source_id] if side == "L" else
                                   next(left_id for left_id, right_id in ARM_MIRROR_IDS.items()
                                        if right_id == source_id))
                segment.SetTag("ARM.SourceLabelID", str(source_label_id))
                segment.SetTag("ARM.Hemisphere", target_side)
            elif item["role"] == "helper_mask":
                segment.SetTag(MIRROR_HELPER_TAG, "helper_mask")
            segment.SetTag("Insula.MirrorSourceNodeID", source.GetID())
            segment.SetTag("Insula.SourceSignature", receipt["source_signature"])
            segment.SetTag("Insula.TemplateSHA256", receipt["template_sha256"])
            segment.SetTag("Insula.ARMAtlasSHA256", receipt["atlas_sha256"])
            segment.SetTag("Insula.MirrorDirection", f"{side}-to-{target_side}")
            segment.SetTag("Insula.CandidateStatus", "candidate")
            slicer.util.updateSegmentBinaryLabelmapFromArray(
                reflect_kji_array(item["mask"], reflected).astype(np.uint8), candidate, segment_id, ref)
            if item["role"] == "helper_mask":
                candidate.GetDisplayNode().SetSegmentVisibility(segment_id, False)
        node_attrs = ("Insula.SourceSignature", "Insula.TemplatePath", "Insula.TemplateSHA256",
                      "Insula.ARMAtlasPath", "Insula.ARMAtlasSHA256", "Insula.RegionProfileHash",
                      "Insula.RegionProfile")
        for key in node_attrs:
            candidate.SetAttribute(key, source.GetAttribute(key))
        candidate.SetAttribute("Insula.CandidateStatus", "candidate")
        candidate.SetAttribute("Insula.MirrorSourceNodeID", source.GetID())
        candidate.SetAttribute("Insula.MirrorReceipt", json.dumps(receipt, sort_keys=True))
        candidate.SetAttribute("Insula.MirrorDirection", f"{side}-to-{target_side}")
        return candidate
    except Exception:
        slicer.mrmlScene.RemoveNode(candidate)
        raise


def save_mirrored_candidate(node, path):
    """Save a mirror candidate to a new path; refuse all existing destinations."""
    _require_slicer()
    if node is None or not node.IsA("vtkMRMLSegmentationNode"):
        raise ValueError("node must be a mirrored candidate segmentation")
    receipt_text = node.GetAttribute("Insula.MirrorReceipt")
    if not receipt_text or not node.GetAttribute("Insula.MirrorSourceNodeID"):
        raise ValueError("node is not a mirrored candidate created by mirror_side")
    target = Path(path).expanduser().resolve()
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing mirror candidate: {target}")
    if not target.name.lower().endswith(".seg.nrrd"):
        raise ValueError("mirrored candidates must be saved with a .seg.nrrd extension")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not slicer.util.saveNode(node, str(target)):
        raise RuntimeError(f"Slicer failed to save mirrored candidate: {target}")
    digest = _sha256_file(target)
    receipt = json.loads(receipt_text)
    receipt.update({"saved_path": str(target), "saved_bytes": target.stat().st_size,
                    "saved_sha256": digest})
    return receipt


def run(dry_run=False, refresh_scopes=False, template_path=None, atlas_path=None, output_dir=None,
        region_profile=None, working_side="L"):
    global ACTIVE_SEG_NAMES, ACTIVE_T1_NAME, ACTIVE_OUTPUT_DIR
    if region_profile is not None:
        configure_region(region_profile)
    working_side = str(working_side).upper()
    if working_side not in ("L", "R"):
        raise ValueError("working_side must be L or R")
    template_path, atlas_path = _resolved_inputs(template_path, atlas_path)
    ACTIVE_OUTPUT_DIR = (Path(output_dir).expanduser().resolve() if output_dir
                         else OUTPUT_DIR)
    for path in (template_path, atlas_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    source_info = _input_names(template_path, atlas_path, region_profile=ACTIVE_REGION_PROFILE)
    print(f"Template      : {template_path}")
    print(f"ARM L6 atlas  : {atlas_path} ({'all 16 ARM L6 IDs required' if ACTIVE_REGION_PROFILE is None else str(sum(len(FULL_INS_IDS[s]) for s in ('L','R'))) + ' selected L6 leaves required'})")
    print(f"region        : {ACTIVE_REGION_LABEL} ({'insula preset' if ACTIVE_REGION_PROFILE is None else ACTIVE_REGION_PROFILE['profile_hash'][:12]})")
    print(f"scope IDs     : {FULL_INS_IDS}")
    print(f"scene nodes   : {source_info['segment_names']}")
    print(f"output folder : {ACTIVE_OUTPUT_DIR}")
    if dry_run:
        print("dry run: resolved input paths and target node names only; scene unchanged")
        return

    _require_slicer()
    ref = _load_or_reuse(template_path, source_info["template_name"], slicer.util.loadVolume)
    arm = _load_or_reuse(atlas_path, source_info["atlas_name"], slicer.util.loadLabelVolume)
    if ref.GetParentTransformNode() or arm.GetParentTransformNode():
        raise ValueError("template and atlas must have no parent transform; harden/align them before loading")
    template_array = slicer.util.arrayFromVolume(ref)
    arm_l6 = slicer.util.arrayFromVolume(arm)
    label_counts = validate_input_arrays(
        template_array, arm_l6, _node_geometry_matrix(ref), _node_geometry_matrix(arm))
    masks = build_scope_masks(arm_l6)
    for side, mask in masks.items():
        count = int(mask.sum())
        if count == 0 or (ACTIVE_REGION_PROFILE is None and source_info["default_pair"]
                          and count != EXPECTED_VOXELS_PER_SIDE):
            raise RuntimeError(f"{side} scope count {count}, expected {EXPECTED_VOXELS_PER_SIDE if ACTIVE_REGION_PROFILE is None else 'nonzero'}")

    # Preflight existing nodes before adding or changing either hemisphere.
    for side, node_name in source_info["segment_names"].items():
        existing = _find(node_name)
        if existing is not None:
            signature = existing.GetAttribute("Insula.SourceSignature")
            if signature and signature != source_info["signature"]:
                raise RuntimeError(f"{node_name} is already bound to different source files")
            if not signature and not source_info["default_pair"]:
                raise RuntimeError(f"{node_name} is unbound; custom inputs will not reuse it")
            bound_profile = existing.GetAttribute("Insula.RegionProfileHash")
            expected_profile = source_info["region_profile_hash"] or "insula-default"
            if bound_profile and bound_profile != expected_profile:
                raise RuntimeError(f"{node_name} is bound to a different region profile; existing edits were preserved")

    ACTIVE_SEG_NAMES = dict(source_info["segment_names"])
    ACTIVE_T1_NAME = source_info["template_name"]
    segmentations = {}
    for side, scope_id in SCOPE_IDS.items():
        node_name = ACTIVE_SEG_NAMES[side]
        segmentation = _find(node_name)
        new_node = segmentation is None
        if new_node:
            segmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", node_name)
            segmentation.SetReferenceImageGeometryParameterFromVolumeNode(ref)
            segmentation.CreateDefaultDisplayNodes()
        _bind_segmentation_source(segmentation, node_name, template_path, atlas_path,
                                  source_info, new_node=new_node)
        data = segmentation.GetSegmentation()
        segment = data.GetSegment(scope_id)
        if segment is None:
            data.AddEmptySegment(scope_id, scope_id, SCOPE_COLORS[side])
            slicer.util.updateSegmentBinaryLabelmapFromArray(
                masks[side].astype(np.uint8), segmentation, scope_id, arm)
        else:
            current = slicer.util.arrayFromSegmentBinaryLabelmap(segmentation, scope_id, arm).astype(bool)
            if not np.array_equal(current, masks[side]):
                if not refresh_scopes:
                    raise RuntimeError(f"{scope_id} differs from source and was preserved; save edits, then rerun with refresh_scopes=True")
                slicer.util.updateSegmentBinaryLabelmapFromArray(
                    masks[side].astype(np.uint8), segmentation, scope_id, arm)
        data.GetSegment(scope_id).SetColor(*SCOPE_COLORS[side])
        if ACTIVE_REGION_PROFILE is not None:
            data.GetSegment(scope_id).SetTag("Insula.RegionProfileHash", ACTIVE_REGION_PROFILE["profile_hash"])
        segmentation.GetDisplayNode().SetSegmentVisibility(scope_id, False)
        seeded = seed_arm6_segments(segmentation, arm_l6, arm, side)
        segmentations[side] = segmentation
        side_counts = {name: label_counts[label_id] for name, label_id, label_side, _ in ARM_SEGMENTS
                       if label_side == side}
        print(f"{node_name}: {scope_id}={int(masks[side].sum())} voxels; seeds={side_counts}; added={len(seeded)}")

    slicer.util.setSliceViewerLayers(background=ref, label=arm, labelOpacity=0.35)
    ref.GetDisplayNode().AutoWindowLevelOn()
    slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    voxels_kji = np.argwhere(masks[working_side])
    center_kji = voxels_kji.mean(axis=0)
    center_ijk = np.asarray([center_kji[2], center_kji[1], center_kji[0], 1.0])
    focus_ras = tuple((_node_geometry_matrix(ref) @ center_ijk)[:3].tolist())
    slicer.modules.markups.logic().JumpSlicesToLocation(*focus_ras, True)
    slicer.util.selectModule("SegmentEditor")
    editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    editor.setSegmentationNode(segmentations[working_side])
    editor.setSourceVolumeNode(ref)
    editor.mrmlSegmentEditorNode().SetSelectedSegmentID("")
    editor.mrmlSegmentEditorNode().SetActiveEffectName("")
    print(f"Ready: separate left/right {ACTIVE_REGION_LABEL} scope+ARM L6 nodes are available; active side={working_side}.")
    print("Example: print(use_scope('L', 'CL_Ia/Id'))  # or 'ARM_L6_228'; R uses its explicit counterpart IDs")
    print("Previous combined nodes are left unchanged; manual edits are not migrated.")
    print("ARM.SourceLabelID tags record source IDs; they do not guarantee exported NIfTI values.")
    return segmentations


NMT_INSTALL_URL = "https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/programs/alpha/@Install_NMT_sphx.html"
NMT_ARCHIVE_URL = "https://afni.nimh.nih.gov/pub/dist/atlases/macaque/nmt/NMT_v2.1_sym.tgz"
ARMINS_ATLAS_SETUP_URL = "https://github.com/bylaikaby/ARMins#atlas-setup"
NMT_INSTALL_COMMAND = "@Install_NMT -nmt_ver 2.1 -sym sym -install_dir ./atlas-data"


def _apply_gui_theme(dialog):
    """Apply a dialog-local navy/teal palette inspired by VisPa's light GUI."""
    dialog.setStyleSheet("""
        QDialog { background: #f6f8fa; color: #102b3a; }
        QLabel { color: #102b3a; }
        QLabel[arminsRole="banner"] {
            background: #263746; color: #f4f7f9;
            border-radius: 6px; padding: 9px 14px;
        }
        QLabel[arminsRole="section"] {
            color: #126b78; font-weight: bold;
            padding: 4px 0px 3px 0px; border-bottom: 1px solid #d9e3e9;
        }
        QLabel[arminsRole="note"] {
            background: #edf6f7; border: 1px solid #d9e3e9;
            border-left: 3px solid #168a91; border-radius: 4px; padding: 7px;
        }
        QLabel[arminsRole="status"] {
            background: #eef3f6; border: 1px solid #d9e3e9;
            border-radius: 4px; padding: 6px; color: #102b3a;
        }
        QLineEdit, QComboBox {
            background: #ffffff; color: #102b3a; border: 1px solid #c6d5df;
            border-radius: 4px; padding: 3px 7px; min-height: 16px;
            selection-background-color: #168a91; selection-color: #ffffff;
        }
        QLineEdit:focus, QComboBox:focus { border: 1px solid #168a91; }
        QComboBox QAbstractItemView {
            background: #ffffff; color: #102b3a;
            selection-background-color: #edf6f7; selection-color: #126b78;
        }
        QPushButton {
            background: #ffffff; color: #102b3a; border: 1px solid #c6d5df;
            border-radius: 4px; padding: 4px 10px; min-height: 16px;
        }
        QPushButton:hover { background: #edf6f7; border-color: #168a91; }
        QPushButton:focus { border: 2px solid #168a91; }
        QPushButton[arminsRole="primary"] {
            background: #168a91; color: #ffffff; border-color: #168a91;
            font-weight: bold;
        }
        QPushButton[arminsRole="primary"]:hover { background: #126b78; }
        QPushButton[arminsRole="region"] {
            background: #168a91; color: #ffffff; border-color: #168a91;
            font-weight: bold;
        }
        QPushButton[arminsRole="region"]:hover { background: #126b78; }
        QPushButton[arminsRole="mirror"] {
            background: #263746; color: #f4f7f9; border-color: #263746;
            font-weight: bold;
        }
        QPushButton[arminsRole="mirror"]:hover { background: #365065; }
        QPushButton[arminsRole="save"] {
            background: #edf6f7; color: #126b78; border-color: #a9cdd1;
        }
        QPushButton:disabled, QPushButton[arminsRole="primary"]:disabled,
        QPushButton[arminsRole="mirror"]:disabled,
        QPushButton[arminsRole="save"]:disabled,
        QLineEdit:disabled, QComboBox:disabled {
            background: #e9eef2; color: #334a59; border: 1px solid #d9e3e9;
        }
        QPushButton[arminsRole="region"]:disabled {
            background: #e5f2f3; color: #126b78; border: 1px solid #a9cdd1;
        }
    """)


def _gui_section(form, parent, title):
    """Add a compact visual divider without changing any workflow controls."""
    import qt
    heading = qt.QLabel(title, parent)
    heading.setProperty("arminsRole", "section")
    form.addRow(heading)


def _colour_working_side(side_combo, direction):
    """Redundant colour/text cues: teal for L, amber for R."""
    left = side_combo.currentText == "L"
    accent, soft = ("#126b78", "#edf6f7") if left else ("#97521f", "#fff3e6")
    side_combo.setStyleSheet(
        f"QComboBox {{ color: {accent}; background: {soft}; "
        f"border: 1px solid {accent}; font-weight: bold; }}")
    direction.setStyleSheet(
        f"QLabel {{ color: {accent}; background: {soft}; "
        f"border: 1px solid {accent}; border-radius: 4px; padding: 4px 8px; font-weight: bold; }}")


def show_atlas_setup_help(parent=None):
    """Open a user-invoked help dialog with official links and a copyable command."""
    _require_slicer()
    import qt

    help_dialog = qt.QDialog(parent or slicer.util.mainWindow())
    help_dialog.setObjectName("NMTAtlasSetupHelpDialog")
    help_dialog.setWindowTitle(f"ARMins {VERSION} · NMT v2.1 setup")
    help_dialog.setMinimumWidth(560)
    _apply_gui_theme(help_dialog)
    layout = qt.QVBoxLayout(help_dialog)
    guidance = qt.QLabel(
        "<b>Atlas setup</b><br>"
        "1. Obtain the <b>NMT v2.1 symmetric</b> release. These links open only "
        "when clicked; ARMins never downloads files automatically.<br>"
        f"<a href=\"{NMT_ARCHIVE_URL}\">Download the official NMT_v2.1_sym archive</a><br>"
        f"<a href=\"{NMT_INSTALL_URL}\">Read AFNI @Install_NMT instructions</a><br>"
        f"<a href=\"{ARMINS_ATLAS_SETUP_URL}\">Open ARMins atlas setup guide</a><br><br>"
        "The archive download works directly. The optional install command below "
        "uses AFNI @Install_NMT on Linux, macOS, or WSL and creates a new "
        "<code>./atlas-data</code> folder; choose a fresh folder outside the ARMins repository.<br><br>"
        "2. Extract the archive outside the ARMins repository. Select "
        "<code>NMT_v2.1_sym_SS.nii.gz</code> as the intensity template and the "
        "ready-to-use <code>supplemental_ARM/ARM_6_in_NMT_v2.1_sym.nii.gz</code> "
        "as the 3-D ARM L6 atlas.<br>"
        "3. The hierarchical <code>ARM_in_NMT_v2.1_sym.nii.gz</code> is also "
        "available; optionally use <code>prepare --level 6</code> to extract its "
        "L6 volume. The template is used by reference and is not copied.", help_dialog)
    guidance.setObjectName("NMTAtlasSetupGuidance")
    guidance.setTextFormat(qt.Qt.RichText)
    guidance.setOpenExternalLinks(True)
    guidance.setWordWrap(True)
    layout.addWidget(guidance)
    command = qt.QLineEdit(NMT_INSTALL_COMMAND, help_dialog)
    command.setObjectName("NMTInstallCommand")
    command.setReadOnly(True)
    layout.addWidget(command)
    buttons = qt.QHBoxLayout()
    copy_button = qt.QPushButton("Copy install command", help_dialog)
    copy_button.setObjectName("CopyNMTInstallCommandButton")
    copy_button.setProperty("arminsRole", "primary")
    close_button = qt.QPushButton("Close", help_dialog)
    close_button.setObjectName("CloseNMTSetupHelpButton")
    buttons.addWidget(copy_button)
    buttons.addStretch(1)
    buttons.addWidget(close_button)
    layout.addLayout(buttons)
    copy_button.clicked.connect(lambda *_: slicer.app.clipboard().setText(NMT_INSTALL_COMMAND))
    close_button.clicked.connect(lambda *_: help_dialog.close())
    help_dialog.show()
    return help_dialog


def show_gui():
    """Show the small input/side/parcel workflow inside 3D Slicer."""
    global INSULA_GUI, PENDING_GUI_PROFILE
    report = dependency_report("gui")
    if not report["ready"]:
        problems = [f"{item['name']}: {item['error']}" for item in report['checks'] if not item['ready']]
        raise RuntimeError("ARMins startup dependency check failed:\n" + "\n".join(problems + report['guidance']))
    _require_slicer()
    import qt
    PENDING_GUI_PROFILE = None

    if "INSULA_GUI" in globals():
        try:
            INSULA_GUI.close()
        except Exception:
            pass

    dialog = qt.QDialog(slicer.util.mainWindow())
    dialog.setObjectName("InsulaAtlasEditorDialog")
    dialog.setWindowTitle(f"ARMins {VERSION} · Atlas editor")
    dialog.setMinimumWidth(680)
    _apply_gui_theme(dialog)
    form = qt.QFormLayout(dialog)
    form.setContentsMargins(12, 12, 12, 12)
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(5)

    banner = qt.QLabel(
        f"<b>ARMins {VERSION}</b> &nbsp; Atlas refinement<br>"
        "<span style='color:#a9c0cc'>NMT v2.1 symmetric · Edit one side, review its mirror</span>",
        dialog)
    banner.setObjectName("ARMinsBanner")
    banner.setProperty("arminsRole", "banner")
    form.addRow(banner)

    setup_help_button = qt.QPushButton("NMT v2.1 setup help", dialog)
    setup_help_button.setObjectName("NMTv21SetupHelpButton")
    form.addRow(setup_help_button)

    def open_setup_help():
        global ATLAS_SETUP_HELP_DIALOG
        ATLAS_SETUP_HELP_DIALOG = show_atlas_setup_help(dialog)

    setup_help_button.connect("clicked()", open_setup_help)
    _gui_section(form, dialog, "01  ·  ATLAS INPUTS AND REGION")

    def file_row(default_path, label):
        row = qt.QWidget(dialog)
        layout = qt.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = qt.QLineEdit(str(default_path) if default_path else "", row)
        browse = qt.QPushButton("Browse…", row)
        layout.addWidget(edit)
        layout.addWidget(browse)

        def choose_file():
            result = qt.QFileDialog.getOpenFileName(
                dialog, label, edit.text, "Volumes (*.nii *.nii.gz *.nrrd);;All files (*)")
            path = result[0] if isinstance(result, (tuple, list)) else result
            if path:
                edit.setText(path)
        browse.connect("clicked()", choose_file)
        form.addRow(label, row)
        return edit

    template_edit = file_row(REF_PATH, "Template intensity volume:")
    atlas_edit = file_row(ARM_PATH, "ARM L6 label volume:")

    region_mode = qt.QComboBox(dialog)
    region_mode.setObjectName("RegionGroupMode")
    region_mode.addItems(["Insula preset", "ARM hierarchy"])
    form.addRow("Region group:", region_mode)
    hierarchy_row = qt.QWidget(dialog)
    hierarchy_layout = qt.QHBoxLayout(hierarchy_row)
    hierarchy_layout.setContentsMargins(0, 0, 0, 0)
    hierarchy_edit = qt.QLineEdit(str(HIERARCHY_PATH or _discover_hierarchy_path(ARM_PATH) or ""), hierarchy_row)
    hierarchy_edit.setObjectName("ARMHierarchyCSVPath")
    hierarchy_browse = qt.QPushButton("Browse…", hierarchy_row)
    hierarchy_layout.addWidget(hierarchy_edit)
    hierarchy_layout.addWidget(hierarchy_browse)
    form.addRow("ARM hierarchy CSV:", hierarchy_row)
    search_row = qt.QWidget(dialog)
    search_layout = qt.QHBoxLayout(search_row)
    search_layout.setContentsMargins(0, 0, 0, 0)
    search_edit = qt.QLineEdit(search_row)
    search_edit.setObjectName("ARMHierarchySearch")
    search_edit.setPlaceholderText("Search name, abbreviation, or exact numeric index")
    search_palette = search_edit.palette
    search_palette.setColor(qt.QPalette.PlaceholderText, qt.QColor("#334a59"))
    search_palette.setColor(qt.QPalette.Disabled, qt.QPalette.PlaceholderText, qt.QColor("#334a59"))
    search_edit.setPalette(search_palette)
    search_side = qt.QComboBox(search_row)
    search_side.addItems(["Both", "L", "R"])
    search_level = qt.QComboBox(search_row)
    search_level.addItems(["Any level", "1", "2", "3", "4", "5", "6"])
    search_button = qt.QPushButton("Search", search_row)
    search_layout.addWidget(search_edit, 3)
    search_layout.addWidget(search_side)
    search_layout.addWidget(search_level)
    search_layout.addWidget(search_button)
    form.addRow("Find ARM region:", search_row)
    hierarchy_results = qt.QComboBox(dialog)
    hierarchy_results.setObjectName("ARMHierarchyResults")
    form.addRow("Search results:", hierarchy_results)
    use_region_button = qt.QPushButton("Work on selected regions", dialog)
    use_region_button.setObjectName("UseSelectedRegionButton")
    use_region_button.setProperty("arminsRole", "region")
    form.addRow(use_region_button)
    region_preview = qt.QLabel("Insula preset is selected. Hierarchy search does not change the scene.", dialog)
    region_preview.setWordWrap(True)
    region_preview.setObjectName("ARMHierarchyProfilePreview")
    region_preview.setProperty("arminsRole", "note")
    form.addRow("Region preview:", region_preview)

    _gui_section(form, dialog, "02  ·  WORKING HEMISPHERE")
    side_combo = qt.QComboBox(dialog)
    side_combo.addItems(["L", "R"])
    side_combo.setObjectName("WorkingHemisphere")
    form.addRow("Working hemisphere:", side_combo)

    def choose_hierarchy_file():
        current = hierarchy_edit.text or str(Path.cwd())
        result = qt.QFileDialog.getOpenFileName(dialog, "Choose ARM_key_table.csv", current,
                                                "CSV tables (*.csv);;All files (*)")
        path = result[0] if isinstance(result, (tuple, list)) else result
        if path:
            hierarchy_edit.setText(path)
    hierarchy_browse.connect("clicked()", choose_hierarchy_file)

    def find_hierarchy():
        try:
            selected_path = hierarchy_edit.text.strip() or str(_discover_hierarchy_path(atlas_edit.text) or "")
            resolver_type, table_path = _load_hierarchy_class(selected_path or None)
            if not hierarchy_edit.text.strip():
                hierarchy_edit.setText(str(table_path))
            resolver = resolver_type.from_file(table_path)
            side_filter = search_side.currentText if search_side.currentText != "Both" else None
            level_filter = None if search_level.currentText == "Any level" else int(search_level.currentText)
            hits = resolver.search(search_edit.text, side=side_filter, level=level_filter)
            hierarchy_results.clear()
            for hit in hits:
                label = (f"L{hit['level']} index {hit['index']} | {hit['abbreviation']} | "
                         f"{hit['full_name']} | {hit['descendant_count']} L6 leaves: "
                         f"{','.join(map(str, hit['descendant_ids']))}")
                hierarchy_results.addItem(label, hit)
            if not hits:
                region_preview.setText("No matches. Refine the query or side/level filter.")
            else:
                region_preview.setText(f"{len(hits)} candidates found. Select one result, then click Work on selected regions. Both hemispheres are included.")
        except Exception as exc:
            hierarchy_results.clear()
            region_preview.setText(f"Hierarchy search failed: {exc}")
            qt.QMessageBox.warning(dialog, "ARM hierarchy search failed", str(exc))

    def choose_region_profile():
        global PENDING_GUI_PROFILE
        try:
            set_ready(False)
            if region_mode.currentIndex == 0:
                PENDING_GUI_PROFILE = None
                region_preview.setText("Insula preset selected. Its historical bilateral 8-label groups will load.")
            else:
                hit = hierarchy_results.itemData(hierarchy_results.currentIndex)
                if not hit:
                    raise ValueError("select one hierarchy search result first")
                resolver_type, table_path = _load_hierarchy_class(hierarchy_edit.text.strip() or None)
                resolver = resolver_type.from_file(table_path)
                PENDING_GUI_PROFILE = resolver.profile_for(
                    hit["index"], hit["level"], hit["side"], namespace=hit["namespace"])
                # A region is bilateral; selecting its L/R search alias must not
                # override the separately chosen working hemisphere.
                if PENDING_GUI_PROFILE["working_side"] != side_combo.currentText:
                    other = PENDING_GUI_PROFILE["counterpart"]
                    PENDING_GUI_PROFILE = resolver.profile_for(
                        other["index"], other["level"], side_combo.currentText,
                        namespace=other["namespace"])
                profile = _validated_profile(PENDING_GUI_PROFILE)
                left_ids = [str(item["index"]) for item in profile["left_leaves"]]
                right_ids = [str(item["index"]) for item in profile["right_leaves"]]
                region_preview.setText(
                    f"Both hemispheres selected: level {profile['selected']['level']} "
                    f"({profile['selected']['full_name']}); left {len(left_ids)} L6 IDs: {','.join(left_ids)}; "
                    f"right {len(right_ids)} L6 IDs: {','.join(right_ids)}. No scene nodes changed.")
            status.setText("Pending region settings changed. Validate and load groups to apply them.")
        except Exception as exc:
            region_preview.setText(f"Region not selected: {exc}")
            qt.QMessageBox.warning(dialog, "Region not selected", str(exc))

    search_button.connect("clicked()", find_hierarchy)
    use_region_button.connect("clicked()", choose_region_profile)
    def mode_changed(*_):
        global PENDING_GUI_PROFILE
        PENDING_GUI_PROFILE = None
        set_ready(False)
        if region_mode.currentIndex == 0:
            region_preview.setText("Insula preset selected. Its historical bilateral groups will load.")
        else:
            region_preview.setText("Search the external ARM hierarchy table, choose one result, then click Work on selected regions. Both hemispheres are included.")
        status.setText("Region mode changed. Validate and load groups to apply the pending settings.")
    region_mode.currentIndexChanged.connect(mode_changed)
    def hierarchy_changed(*_):
        global PENDING_GUI_PROFILE
        PENDING_GUI_PROFILE = None
        hierarchy_results.clear()
        set_ready(False)
        region_preview.setText("Hierarchy table changed. Search and use a new explicit result before loading.")
        status.setText("Hierarchy table changed. Validate and load again before editing.")
    hierarchy_edit.textChanged.connect(hierarchy_changed)
    search_enable = lambda enabled: [widget.setEnabled(enabled) for widget in
                                     (hierarchy_edit, hierarchy_browse, search_edit,
                                      search_side, search_level, search_button,
                                      hierarchy_results, use_region_button)]
    region_mode.currentIndexChanged.connect(lambda *_: search_enable(region_mode.currentIndex == 1))
    search_enable(False)
    guidance = qt.QLabel(
        "1. Validate matching template/ARM6 grids and the selected region's bilateral labels.\n"
        "2. Choose L or R and a parcel; apply its scope, then Paint. Visible donors transfer voxels; hidden siblings may overlap.\n"
        "3. Finish one side, then mirror and review the new opposite-side candidate. Both working groups are preserved.", dialog)
    guidance.setWordWrap(True)
    guidance.setProperty("arminsRole", "note")
    form.addRow(guidance)

    load_button = qt.QPushButton("Validate inputs and load groups", dialog)
    load_button.setProperty("arminsRole", "primary")
    form.addRow(load_button)
    _gui_section(form, dialog, "03  ·  EDIT, MIRROR AND SAVE")
    parcel_combo = qt.QComboBox(dialog)
    refresh_button = qt.QPushButton("Refresh parcel list", dialog)
    select_row = qt.QWidget(dialog)
    select_layout = qt.QHBoxLayout(select_row)
    select_layout.setContentsMargins(0, 0, 0, 0)
    select_layout.addWidget(parcel_combo)
    select_layout.addWidget(refresh_button)
    form.addRow("Editing group / seed:", select_row)
    apply_button = qt.QPushButton("Apply scope restriction", dialog)
    save_button = qt.QPushButton("Save selected side…", dialog)
    save_button.setProperty("arminsRole", "save")
    action_row = qt.QWidget(dialog)
    action_layout = qt.QHBoxLayout(action_row)
    action_layout.setContentsMargins(0, 0, 0, 0)
    action_layout.addWidget(apply_button)
    action_layout.addWidget(save_button)
    form.addRow(action_row)
    mirror_button = qt.QPushButton("Mirror selected side (new candidate)", dialog)
    mirror_button.setProperty("arminsRole", "mirror")
    save_mirror_button = qt.QPushButton("Save mirrored candidate…", dialog)
    save_mirror_button.setProperty("arminsRole", "save")
    mirror_row = qt.QWidget(dialog)
    mirror_layout = qt.QHBoxLayout(mirror_row)
    mirror_layout.setContentsMargins(0, 0, 0, 0)
    mirror_layout.addWidget(mirror_button)
    mirror_layout.addWidget(save_mirror_button)
    form.addRow(mirror_row)
    direction = qt.QLabel("L → R", dialog)
    direction.setObjectName("MirrorDirection")
    _colour_working_side(side_combo, direction)
    form.addRow("Candidate direction:", direction)
    status = qt.QLabel("Choose inputs, then validate and load. Opening this panel does not change the scene.", dialog)
    status.setWordWrap(True)
    status.setObjectName("ARMinsStatus")
    status.setProperty("arminsRole", "status")
    form.addRow("Status:", status)

    gui_ready = False
    def set_ready(ready):
        nonlocal gui_ready
        gui_ready = bool(ready)
        side_combo.setEnabled(True)
        parcel_combo.setEnabled(ready)
        refresh_button.setEnabled(ready)
        apply_button.setEnabled(ready)
        save_button.setEnabled(ready)
        mirror_button.setEnabled(ready)

    def invalidate(*_):
        set_ready(False)
        status.setText("Inputs changed. Validate and load again before applying a scope or saving.")

    def refresh_parcels(*_):
        parcel_combo.clear()
        parcel_combo.addItem("(choose a parcel)", "")
        side = side_combo.currentText
        node = _find(ACTIVE_SEG_NAMES[side])
        if node is None:
            return
        data = node.GetSegmentation()
        for index in range(data.GetNumberOfSegments()):
            segment_id = data.GetNthSegmentID(index)
            if segment_id == SCOPE_IDS[side]:
                continue
            segment = data.GetSegment(segment_id)
            parcel_combo.addItem(segment.GetName(), segment_id)

    def load_groups():
        set_ready(False)
        try:
            if region_mode.currentIndex == 1 and PENDING_GUI_PROFILE is None:
                raise ValueError("search for a hierarchy region and use one explicit result before loading")
            configure_region(PENDING_GUI_PROFILE)
            loaded = run(template_path=template_edit.text, atlas_path=atlas_edit.text,
                          output_dir=ACTIVE_OUTPUT_DIR,
                          region_profile=PENDING_GUI_PROFILE,
                          working_side=side_combo.currentText)
            if not loaded:
                raise RuntimeError("input groups were not loaded")
            refresh_parcels()
            set_ready(True)
            status.setText("Inputs validated and groups loaded. Confirm source, side, seed and mask read-back before painting.")
        except Exception as exc:
            status.setText(f"Load failed: {exc}")
            qt.QMessageBox.critical(dialog, "Insula input validation/load failed", str(exc))

    def apply_restriction():
        side = side_combo.currentText
        target = parcel_combo.itemData(parcel_combo.currentIndex)
        if not target:
            status.setText("Choose a parcel before applying the scope restriction.")
            return
        try:
            result = use_scope(side, target)
            status.setText(result)
        except Exception as exc:
            status.setText(f"Scope not applied: {exc}")
            qt.QMessageBox.warning(dialog, "Scope not applied", str(exc))

    def save_side():
        side = side_combo.currentText
        node_name = ACTIVE_SEG_NAMES[side]
        segmentation = _find(node_name)
        if segmentation is None:
            status.setText(f"Cannot find loaded group {node_name}")
            return
        result = qt.QFileDialog.getSaveFileName(
            dialog, f"Save {node_name}", str(ACTIVE_OUTPUT_DIR / f"{node_name}.seg.nrrd"),
            "Slicer segmentation (*.seg.nrrd)")
        path = result[0] if isinstance(result, (tuple, list)) else result
        if not path:
            return
        if not path.lower().endswith(".seg.nrrd"):
            path += ".seg.nrrd"
        try:
            if not slicer.util.saveNode(segmentation, path):
                raise RuntimeError("Slicer saveNode returned failure")
            status.setText(f"Saved {node_name} to {path}")
        except Exception as exc:
            status.setText(f"Save failed: {exc}")
            qt.QMessageBox.critical(dialog, "Segmentation save failed", str(exc))

    def mirror_selected_side():
        global LAST_MIRROR_CANDIDATE
        side = side_combo.currentText
        try:
            LAST_MIRROR_CANDIDATE = mirror_side(side)
            save_mirror_button.setEnabled(True)
            status.setText(
                f"Created new {('R' if side == 'L' else 'L')} mirror candidate "
                f"{LAST_MIRROR_CANDIDATE.GetName()}; source working groups were preserved. "
                "Inspect the candidate before saving.")
        except Exception as exc:
            status.setText(f"Mirror refused: {exc}")
            qt.QMessageBox.warning(dialog, "Mirror candidate not created", str(exc))

    def save_mirror_candidate():
        if LAST_MIRROR_CANDIDATE is None:
            status.setText("Create a mirror candidate before saving.")
            return
        result = qt.QFileDialog.getSaveFileName(
            dialog, "Save mirrored candidate", str(ACTIVE_OUTPUT_DIR / f"{LAST_MIRROR_CANDIDATE.GetName()}.seg.nrrd"),
            "Slicer segmentation (*.seg.nrrd)")
        path = result[0] if isinstance(result, (tuple, list)) else result
        if not path:
            return
        if not path.lower().endswith(".seg.nrrd"):
            path += ".seg.nrrd"
        try:
            receipt = save_mirrored_candidate(LAST_MIRROR_CANDIDATE, path)
            status.setText(
                f"Saved candidate {receipt['candidate_name']} to {receipt['saved_path']} "
                f"({receipt['saved_bytes']} bytes; SHA-256 {receipt['saved_sha256']}).")
        except Exception as exc:
            status.setText(f"Mirror candidate save refused/failed: {exc}")
            qt.QMessageBox.critical(dialog, "Mirror candidate save failed", str(exc))

    template_edit.textChanged.connect(invalidate)
    atlas_edit.textChanged.connect(invalidate)
    def focus_working_side(*_):
        direction.setText(f"{side_combo.currentText} → {'R' if side_combo.currentText == 'L' else 'L'}")
        _colour_working_side(side_combo, direction)
        if not gui_ready:
            return
        refresh_parcels()
        if not _has_slicer_scene():
            return
        segmentation = _find(ACTIVE_SEG_NAMES[side_combo.currentText])
        if segmentation is not None:
            editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
            editor.setSegmentationNode(segmentation)
            editor.setSourceVolumeNode(_find(ACTIVE_T1_NAME))
            editor.mrmlSegmentEditorNode().SetSelectedSegmentID("")
            editor.mrmlSegmentEditorNode().SetActiveEffectName("")
    side_combo.currentIndexChanged.connect(focus_working_side)
    load_button.connect("clicked()", load_groups)
    refresh_button.connect("clicked()", refresh_parcels)
    apply_button.connect("clicked()", apply_restriction)
    save_button.connect("clicked()", save_side)
    mirror_button.connect("clicked()", mirror_selected_side)
    save_mirror_button.connect("clicked()", save_mirror_candidate)
    set_ready(False)
    save_mirror_button.setEnabled(LAST_MIRROR_CANDIDATE is not None)
    dialog.show()
    INSULA_GUI = dialog
    return dialog


def _build_cli_parser():
    parser = argparse.ArgumentParser(
        prog="armins.py",
        description=f"ARMins {VERSION}. Validate and prepare ARM insula level-6 inputs; open the editor in 3D Slicer.",
    )
    parser.add_argument("--version", action="version", version=f"ARMins {VERSION}")
    commands = parser.add_subparsers(dest="command")
    doctor = commands.add_parser("doctor", help="read-only GUI or CLI dependency check")
    doctor.add_argument("--mode", choices=("cli", "gui"), default="cli")
    check = commands.add_parser("check", help="read-only validate a 3-D ARM L6 label volume")
    check.add_argument("--template", default=str(REF_PATH) if REF_PATH else None)
    check.add_argument("--atlas", default=str(ARM_PATH) if ARM_PATH else None)
    check.add_argument("--level", type=int, choices=(6,), default=6)
    check.add_argument("--hierarchy", help="external ARM_key_table.csv for an explicit region profile")
    check.add_argument("--region", help="exact numeric hierarchy index or exact abbreviation")
    check.add_argument("--region-level", type=int, choices=range(1, 7))
    check.add_argument("--side", choices=("L", "R"), default="L")
    check.add_argument("--dry-run", action="store_true", help="print resolved validation receipt; always read-only")
    prepare = commands.add_parser("prepare", help="extract explicit ARM level 6 from a 3/4/5-D NIfTI")
    prepare.add_argument("--template", default=str(REF_PATH) if REF_PATH else None)
    prepare.add_argument("--atlas", default=str(ARM_PATH) if ARM_PATH else None)
    prepare.add_argument("--level", type=int, choices=(6,), required=True)
    prepare.add_argument("--hierarchy", help="external ARM_key_table.csv for an explicit region profile")
    prepare.add_argument("--region", help="exact numeric hierarchy index or exact abbreviation")
    prepare.add_argument("--region-level", type=int, choices=range(1, 7))
    prepare.add_argument("--side", choices=("L", "R"), default="L")
    prepare.add_argument("--output-dir", default=str(OUTPUT_DIR))
    prepare.add_argument("--dry-run", action="store_true", help="report outputs without writing files")
    search = commands.add_parser("search", help="read-only search of the external ARM hierarchy table")
    search.add_argument("--hierarchy", help="ARM_key_table.csv (or ARMINS_HIERARCHY)")
    search.add_argument("--query", required=True, help="name/abbreviation substring or exact numeric index")
    search.add_argument("--side", choices=("L", "R"), help="optional hemisphere filter")
    search.add_argument("--level", type=int, choices=range(1, 7), help="optional hierarchy-level filter")
    search.add_argument("--dry-run", action="store_true", help="explicitly confirm read-only search")
    commands.add_parser("gui", help="open the editor inside 3D Slicer")
    return parser


def _cli_region_profile(hierarchy_path, region, level, side):
    if not region:
        if level is not None:
            raise ValueError("--region-level requires --region")
        if hierarchy_path:
            raise ValueError("--hierarchy with check/prepare requires --region; use `search` to explore candidates")
        return None
    if level is None:
        raise ValueError("--region-level is required with --region; use `search` to choose a level")
    resolver_type, path = _load_hierarchy_class(hierarchy_path)
    resolver = resolver_type.from_file(path)
    return resolver.resolve(region, side=side, level=level)


def main(argv=None):
    parser = _build_cli_parser()
    args = parser.parse_args(argv)
    if args.command == "doctor":
        report = dependency_report(args.mode)
        print(json.dumps(report, indent=2))
        return 0 if report["ready"] else 1
    if args.command in ("check", "prepare"):
        report = dependency_report("cli")
        if not report["ready"]:
            missing = "; ".join(f"{c['name']}: {c['error']}" for c in report['checks'] if not c['ready'])
            parser.error(f"Dependency check failed: {missing}. Run doctor; use conda env create -f environment.yml or pip install -r requirements.txt")
    if args.command == "check":
        profile = _cli_region_profile(args.hierarchy, args.region, args.region_level, args.side)
        result = check_inputs(args.template, args.atlas, level=args.level, region_profile=profile)
    elif args.command == "prepare":
        profile = _cli_region_profile(args.hierarchy, args.region, args.region_level, args.side)
        result = prepare_level6(args.template, args.atlas, level=args.level,
                                output_dir=args.output_dir, dry_run=args.dry_run,
                                region_profile=profile)
    elif args.command == "search":
        resolver_type, path = _load_hierarchy_class(args.hierarchy)
        resolver = resolver_type.from_file(path)
        result = {
            **_runtime_provenance(),
            "status": "read-only-search",
            "hierarchy_path": str(resolver.path),
            "hierarchy_sha256": resolver.source_sha256,
            "query": args.query,
            "side": args.side,
            "level": args.level,
            "matches": resolver.search(args.query, side=args.side, level=args.level),
            "dry_run": True,
            "writes": [],
        }
    elif args.command == "gui":
        show_gui()
        return 0
    elif args.command is None:
        if _has_slicer_scene():
            show_gui()
            return 0
        parser.print_help()
        return 0
    else:
        parser.error(f"unsupported command: {args.command}")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    # Opening the file from Slicer's Python Console still presents the GUI;
    # ordinary Python runs the portable CLI without importing/starting a GUI.
    if _has_slicer_scene():
        show_gui()
    else:
        raise SystemExit(main())
