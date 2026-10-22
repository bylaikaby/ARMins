# ARMins change log

One consolidated history. README.md is the operator guide.

## 0.7.3 - 2026-10-22 (local/unreleased)

- Add a manual fresh-machine Slicer workflow for Windows/Ubuntu: official fixed
  5.12.0 packages, verified checksums, public AFNI inputs, no Slicer pip installs
  or user caches; GUI screenshots and machine-readable native test receipts.
- Extend the native harness to exercise documented import startup from outside
  the checkout. The workflow checks receipt status as well as process exit.
- Keep tool version visible as 0.7.3. Atlas/edit/mirror algorithms unchanged.
- First cloud design run: Windows passed; Ubuntu Slicer failed before Python
  with missing libxcb-shape.so.0. Added its XCB runtime and the documented
  qt5dxcb-plugin dependency; rerun pending.
- Local preflight: 49 synthetic tests, import-based native design checks and
  YAML/PowerShell syntax checks passed. Cloud execution is pending.

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
