# ARMins project note

Updated 2026-10-22 | Agent Codex | Asia/Shanghai.

## Current status and entry points

ARMins is a standalone candidate editor for ARM level-6 insula parcels in the
symmetric NMT v2.1 reference. README.md is the main operator/download guide;
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

1. Follow README.md's Atlas setup section and open the editor; verify the two
   matching standard-resolution input files and the intended editing side.
2. Edit/save one side, create a separate mirror candidate, and inspect actual
   boundaries. Expect zero partition errors and preserved working nodes.
3. Save to a new `.seg.nrrd`, reload, and inspect parcel identity and extent.
   Judge anatomy independently of the technical checks.
