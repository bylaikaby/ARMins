# ARMins change log

One consolidated history. README.md is the operator guide.

## 0.7.5 - 2026-10-23 (local/unreleased)

- Add an explicit Windows 11 ARM64 cloud target with OS/build/architecture
  evidence and x64 Slicer emulation; reject a substituted Server OS.
- Rename region action to Work on selected regions and use the supplied teal
  #168a91. Preserve dark text and a pale disabled state. Bilateral region
  selection now preserves the independent working hemisphere for L/R aliases.
- Add a visual smoke phase that displays normal Slicer closed surfaces and
  captures two labelled camera views; gate current-context OpenGL and graphics
  errors. Rendering stays in Slicer; no separate renderer or user driver changes.
- Local preflight: 52 synthetic tests, five native design/help checks and 12
  hierarchy checks passed, including both alias/working-side combinations.
  Visual and fresh Windows 11 results are recorded after execution.

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
