# ARMins change log

One consolidated history. README.md is the operator guide.

## Henry preset viewer 0.1.1 - 2026-10-26 (local/unreleased)

- Hide the temporary ARM labelmap during import, retain its color tables until
  the source node is removed, and explicitly clear all slice label IDs. This
  fixes observed VTK lookup-table/scalar-type errors and restores colored CL
  overlays in axial, coronal and sagittal views. Group masks and identities
  remain the same.
- Make `python henry_preset.py` a standard-library launcher for the installed
  Slicer application, with `--slicer`, `--help` and `--version`. The same file
  still builds groups when run by Slicer. No separate launcher or dependency
  install is needed.
- Validation: ordinary-Python help/version and mocked launcher argv passed;
  native Slicer 5.12.0 checked both groups' 141 exact source masks, visibility
  switching and rendered captures; the reported VTK error phrases were absent.
  Scientific anatomical acceptance remains pending. The 0.1.0 native mask
  check passed but its visual rendering failed and is retained below.

## Henry preset viewer 0.1.0 - 2026-10-26 (local/unreleased)

- Consolidated the two temporary CL-only viewers into one `henry_preset.py`
  entry point: separate left Insula eight-parcel and left cortex 133-parcel
  segmentations in one fresh Slicer scene. Insula starts visible, cortex hidden.
  Source files and ARMins editor 0.7.7 remain unchanged. The groups do not
  synchronize later manual edits.
- Validates exact table identities and matching source grids, imports only CL
  labels, clears the full atlas label overlay, fits the complete NMT reference
  and records source hashes on both groups. Native Slicer verification and
  limits are recorded in the project note; scientific acceptance is pending.

## Superseded two-script CL viewers 0.1.0 - 2026-10-26 (local/unreleased)

- Added `show_cl_level6.py` for the 133 declared left cortical level-6 ARM
  labels and `show_cl_insula_level6.py` for ARMins' previous eight-label left
  Insula preset. The second reuses the first viewer; neither changes the ARMins
  0.7.7 editor, source atlas or working segmentation nodes.
- Both scripts use the ignored explicit local config, import one selected-label
  segmentation, clear the full atlas label layer, fit the full template and
  position slice planes through the selected mask. They refuse a populated
  scene. Validated by source-ID voxel equality in Slicer (see project note).

## 0.7.7 - 2026-10-26 (local/unreleased)

- Fixed the local-config precedence test to supply both synthetic input paths.
  Its earlier implicit atlas path came from an ignored personal config, causing
  the first clean Ubuntu Conda CI run to fail. All 53 synthetic tests passed in
  a clean source-only fixture with ARMINS inputs unset and no local config.
- Made Henry preset the README's primary launch path and kept `armins.show_gui()`
  as a separate expert editing workflow. Documentation changed; editor and
  viewer runtime behavior and their versions are unchanged.

- Read an ignored explicit `local_atlas_config.json` beside `armins.py` for
  absolute template, ARM6 and hierarchy paths. This removes the need for
  inherited Windows environment settings in a personal checkout; explicit
  function/GUI/CLI paths still override, and environment inputs remain fallback.
- Reject malformed or incomplete local configuration clearly at import.
  Atlas algorithms and the Insula preset selection are unchanged.
- Validation: focused configuration tests and native Slicer checks recorded in
  the project note. No anatomical acceptance is implied.

## 0.7.6 - 2026-10-26 (local/unreleased)

- CLI setup, `doctor` guidance, and synthetic CI use the Conda recipe
  `environment.yml` (`armins-cli`) on Windows and Ubuntu. Atlas, mirror, and
  GUI behavior are unchanged.
- Recorded 0.7.4 and 0.7.5 pip CI results stay historical. The 0.7.5
  `armins.py` sha256 was
  `fa8ac68021aae0614f87aca995f6a825dae870ae3e9e359a158033d7392c62fc`.
- Validation: local `armins-cli` doctor ready (Python 3.12.15, NumPy 2.5.4,
  nibabel 5.4.2) and 52 synthetic tests passed. No new cloud run.

## 0.7.5 - 2026-10-23 (local/unreleased)

- Add an explicit Windows 11 ARM64 cloud target with OS/build/architecture
  evidence and x64 Slicer emulation; reject a substituted Server OS.
- Rename region action to Work on selected regions and use the supplied teal
  #168a91. Preserve dark text and a pale disabled state. Bilateral region
  selection now preserves the independent working hemisphere for L/R aliases.
- Add a visual smoke phase that displays normal Slicer closed surfaces and
  captures two labelled camera views; gate current-context OpenGL and graphics
  errors. Rendering stays in Slicer; no separate renderer or user driver changes.
- Validation: 52 local synthetic, five native design, 12 native hierarchy and
  three local visual checks passed. Fresh Windows11 Enterprise build26200 ARM64
  with x64 Slicer emulation passed design5 and hierarchy12; source hashes agree.
  Fresh pip Windows/Ubuntu and Conda Ubuntu each passed52 checks.
- Fresh Windows11 stock software graphics failed visually (OpenGL3.0/Mesa12,
  GLSL1.50 rejected, blank captures). A pinned app-local Mesa26.2.4 experiment
  exited before Python receipt; removed that unsuccessful runtime option.
  Local Intel UHD770 rendering passed and was visually reviewed. No fresh-VM
  graphics pass or native Intel/AMD Windows11 VM coverage is claimed.

## 0.7.4 - 2026-10-22 (local/unreleased)

- Add read-only `doctor` CLI/GUI dependency reports. GUI startup and NIfTI CLI
  operations preflight their own runtimes; doctor/help/version remain usable
  without NumPy/nibabel. No automatic installs or scene/data writes.
- Add an optional Conda CLI recipe and a fresh Conda CI job. Keep Slicer's
  embedded Python/Qt/VTK separate from Conda; record resolved package versions.
- Add consistent LF source checkout rules after cloud Windows/Linux byte hashes
  differed only by line endings. Use bundled Qt software OpenGL for GPU-less
  Windows cloud load tests; do not alter application/global PC graphics settings.
- Validation: 52 tests passed locally and in each fresh cloud pip/Conda job;
  native Slicer import/preflight and 11 hierarchy/load/mirror/save checks passed
  on each fresh Windows/Ubuntu VM. Actual source hashes agree across OS.
  Windows cloud GLSL 1.50 shader errors remain a rendering limitation; Ubuntu
  logged no graphics errors. See provenance.json for run links and exact scope.

## 0.7.3 - 2026-10-22 (local/unreleased)

- Add a manual fresh-machine Slicer workflow for Windows/Ubuntu: official fixed
  5.12.0 packages, verified checksums, public AFNI inputs, no Slicer pip installs
  or user caches; GUI screenshots and machine-readable native test receipts.
- Extend the native harness to exercise documented import startup from outside
  the checkout. The workflow checks receipt status as well as process exit.
- Keep tool version visible as 0.7.3. Atlas/edit/mirror algorithms unchanged.
- First cloud design run: Windows passed; Ubuntu Slicer failed before Python
  with missing libxcb-shape.so.0. Added its XCB runtime and the documented
  qt5dxcb-plugin dependency; Windows/Ubuntu startup rerun passed
  (run 39738903061). Windows default VM graphics emitted OpenGL warnings;
  startup pass is not a full 3D rendering acceptance.
- Local preflight: 49 synthetic tests, import-based native design checks and
  YAML/PowerShell syntax checks passed. Cloud startup is now verified.

## 0.7.2 - 2026-10-22 (local/unreleased)

- Show the authoritative tool version in the main GUI title/header, setup-help
  title, CLI help and `python armins.py --version`. Keep script headers and
  receipts consistent; retain the separate unchanged hierarchy module version.
- Refresh screenshots and operator instructions. Atlas/edit/mirror algorithms
  are unchanged. Validation: 49 synthetic tests (including CLI help/version
  outside the repository) and five native Slicer 5.12.0 design/help checks.

## 0.7.1 - 2026-10-22 (local/unreleased)

- Added dialog-local VisPa-inspired navy/teal styling, compact section headings,
  darker text (including inactive search fields), and a distinct purple region
  action with a pale disabled state. L/R cues retain explicit text and use
  teal/amber. No scientific algorithm or atlas definition changed.
- Fixed setup-help Close handling for Qt's clicked signal.
- Replaced README images with reviewed native Slicer captures. Validation:
  49 synthetic tests, five native design/help checks and 11 native hierarchy
  checks; screenshots reviewed before behavior testing. See provenance.json.

## 0.7.0 - 2026-10-22 (local/unreleased)

- Added explicit ARM hierarchy search and parent-to-level-6 grouping from an
  external provider CSV. Search results require a specific parent selection;
  names, numeric IDs, level and hemisphere remain explicit. No atlas data,
  ontology or projectome runtime dependency is bundled.
- Added region profiles with explicit bilateral label correspondence, distinct
  group/source bindings and preserved earlier scene groups. The original
  eight-label insula preset remains available unchanged.
- Made either L or R selectable as the working hemisphere and initial editor
  focus; mirroring validates the selected reference and label pairs before
  creating a separate opposite-side candidate.
- Expanded README into the complete symmetry-first GUI guide, including
  download, region selection, local editing masks, subdivision, dry-run,
  mirroring, visibility checks, save/reload and current export limitations.
  Preserved the user's opening description and anatomical attribution.
- Validation for the final tested snapshot is recorded in provenance.json.
  No tagged release or anatomical acceptance is claimed.

## 0.6.0 - 2026-10-22 (local/unreleased)

- Extracted the existing 0.5.0 editor into standalone `armins.py`; replaced
  machine-specific inputs with GUI selection, configuration and ARMINS
  environment variables. Existing seed and mirror behavior is preserved.
- Added optional read-only input checking and bounded ARM level-6 preparation
  for explicit 3-D, 4-D and 5-D inputs; no template duplication or resampling.
- Added user-invoked NMT v2.1 setup help with official AFNI links, a copyable
  version-specific command and the supplied ready-to-use ARM6 fast path.
- Retained exact-grid reflection, source/identity/partition checks, independent
  mirror candidates, source preservation and saved metadata provenance.
- Runtime provenance uses the standalone tool version and UTC. Atlas data and
  earlier project-local outputs are not distributed.
- Validation results and exact tested hashes are recorded in provenance.json.
  No tagged release or anatomical acceptance is claimed.

## Source history - before standalone extraction

The imported editor declares 0.5.0 (local/unreleased), updated 2026-10-22.
Its original SHA-256 and logical source/test mappings are retained in
provenance.json. Earlier source versions added independent side nodes, native
scope-mask read-back, compatible Slicer volume loading, and the input/save GUI.
This repository does not invent earlier releases or import unrelated history.
