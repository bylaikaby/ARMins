# ARMins project note

Updated 2026-10-22 | Agent Codex | Asia/Shanghai.

## Current status and entry points

ARMins supports expert curation of the insula atlas and provides a standalone
candidate editor for ARM level-6 region groups in symmetric NMT v2.1. The
original insula preset remains the default. README.md is the complete GUI and
operator/download guide;
armins.py is the executable source; CHANGELOG.md and provenance.json record
version changes and technical validation. No tagged release or new anatomical
atlas is accepted by this source snapshot.

## Scientific decisions and limits

The selected reference is symmetric, so a reviewed unilateral edit can be
reflected exactly onto the paired voxel lattice. Symmetric construction is an
explicit atlas-design choice, not evidence that biological anatomy is symmetric.
Source region identity, manual annotation and scientific acceptance stay distinct.
Unknown custom labels and invalid partitions are refused rather than inferred.

The default setup uses the provider's supplied 3-D ARM6 image, avoiding an
unnecessary extraction. Hierarchical preparation remains an optional bounded
operation. Template images remain external references; source data are preserved.

## Operations journal

### 2026-10-22 | Agent Codex | GUI colour and contrast refinement

- Objective: add VisPa-like colour elements; follow-up requested darker text
  and a different colour for Use selected region. Starting point was the
  published 0.7.0 hierarchy editor. No VisPa code or dependency was imported.
- Result: dialog-local navy/teal layout, dark active/inactive text, purple
  region action with a pale-purple disabled state, and teal L / amber R cues.
  Iterated compact padding and retained native dropdown arrows after visual
  inspection. Fixed the setup-help Close signal callback.
- Verification: reviewed actual blank-input Slicer 5.12.0 screenshots first;
  then 49 synthetic tests and 11 native hierarchy checks passed. Five design
  checks cover theme isolation, L/R cues, contrast/action state, help and Close.
  AST comparison confirms all existing non-GUI functions are unchanged.
- Review: (1) Open README's editor image and inspect text/purple action;
  (2) choose hierarchy mode and check region selection, then L/R direction;
  (3) review a separate mirror candidate before scientific acceptance.
  Earlier hierarchy/manual/download/publication requests remain delivered;
  anatomical acceptance, arbitrary ontologies, bilateral NIfTI merge/export
  and code-license selection remain open as documented.


### 2026-10-22 | Agent Codex | Hierarchy region selection and symmetry-first guide

- Objective: provide a complete README guide; allow either L or R as the working
  hemisphere; search a particular ARM hierarchy region and group all of its
  descendant level-6 parcels for editing. Preserve the user's scientific
  description and attribution to Henry Evrard.
- Starting point: the public 0.6.0 editor plus the user's opening README text.
  Prior default insula behavior and source hashes are preserved in provenance;
  this update is a local/unreleased candidate until separately released.
- Source review: the earlier region-analysis hierarchy reader supplies explicit
  Level_1..6 name/abbreviation/index semantics. The initial region parser also
  uses exact-node lookup and subtree traversal. Its separate JSON ontology,
  network services and fixed image-index coordinates are not imported. The
  standalone reader uses the provider's external ARM CSV and the standard
  library; First_Level/Last_Level availability metadata are not parent paths.
- Scientific choice: selecting one explicit parent determines its deduplicated
  level-6 leaves. Text search suggests individual nodes rather than silently
  joining all matches. Cortical/subcortical namespace, level, ID and hemisphere
  remain explicit. The eight-label insula preset spans multiple branches and
  is retained unchanged, separately from hierarchy-defined groups.
- Symmetry choice: either hemisphere may be the edit source. The selected
  template, paired labels and integer voxel lattice must pass the same checks
  before reflection. Mirroring is an explicit candidate-generation action,
  avoids independently redrawing a symmetric atlas product, and does not imply
  biological symmetry or anatomical acceptance.
- Validation: 49 distinct synthetic tests and all837 bilateral hierarchy-node
  pair checks passed. Actual Slicer 5.12.0 design was visually reviewed before
  behavior checks. The insula and ACC phases each passed11 native checks. An
  initial ACC test failed because the checker used an unsupported node-ID
  getter; the harness was corrected, with the editor module unchanged, and the
  ACC phase passed on rerun. Final hashes/results are in provenance.json.
  Search/preview, scene mutation, preserved source/editor state, and save/reload
  were checked separately.
- Current limitations: full bilateral integer-label NIfTI export/merge and code
  license selection remain open. A curated atlas release still needs its own
  anatomical review, label table and release record.

### 2026-10-22 | Agent Codex | Standalone extraction and atlas setup

- Objective: publish a small independent ARMins source repository and make the
  NMT v2.1/ARM acquisition path discoverable to new users.
- Starting point: editor 0.5.0 and focused source tests. Logical origin mapping
  and source checksums are retained in provenance.json; local machine paths,
  study data, human edits and previous project receipts are excluded.
- Approach: retain the existing scientific/voxel contracts, expose portable
  settings, use official AFNI download/install resources, and prefer the supplied
  supplemental ARM6 file. The general AFNI overview still shows older examples;
  the installer command and download link select symmetric v2.1 explicitly.
- Validation: see the observed results and exact code hash in provenance.json.
  Array/editor/preparation tests and native Slicer interaction are separate checks.
- Pending: anatomical review of real edited boundaries; explicit integer-label
  bilateral NIfTI export/merge; selection of a project code license. None is
  implied by a passing software test or public source publication.

## Priority review guide

1. Follow README.md's Atlas setup and complete editing guide; verify the two
   matching standard-resolution files, optional hierarchy CSV, selected parent
   and descendant preview, and the L or R working hemisphere.
2. Edit/save one side, create a separate mirror candidate, and inspect actual
   boundaries. Expect zero partition errors and preserved working nodes.
3. Save to a new `.seg.nrrd`, reload, and inspect parcel identity and extent.
   Judge anatomy independently of the technical checks.
