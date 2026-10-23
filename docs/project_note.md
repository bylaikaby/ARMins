# ARMins project note

Updated 2026-10-23 | Agent Codex | Asia/Shanghai.

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

## Current verification and review

- Current source: 0.7.5; current and historical validation runs below are
  tied to the exact armins.py hash in provenance.json. No local config/cache or
  atlas data was copied to cloud VMs; only public provider downloads were used.
- Review in order: (1) follow README's GUI versus CLI dependency path; `doctor`
  should report ready; (2) inspect Actions receipts/checks for the selected OS;
  (3) open the atlas in a supported desktop graphics environment and judge its
  rendering and anatomy. Windows VM functional passes do not certify rendering.
- Original reported initialization bug remains unidentified without the user's
  first traceback and Slicer version; cloud startup/import/load paths passed.

## Operations journal

### 2026-10-23 | Agent Codex | Fresh Windows 11 command/API validation

- Request: test a genuine fresh Windows 11 VM. The subsequent clarification
  questioned separate 3D rendering because ARMins supplies Slicer commands;
  focus is now import, dependency readiness, GUI load/edit/mirror/save/reload.
  A staged dedicated-renderer check was removed before publication. The latest
  explicit request reinstated a visual check of Slicer's own display: labelled
  two-camera images, with graphics errors recorded separately. No ARMins engine
  or user system-driver change is included.
- Available hosted target is Windows 11 ARM64 with x64 Slicer emulation. Actual
  caption/build/ProductType and native/process architecture are recorded, with
  a gate against substituting Server. This does not certify native x64 Windows11.
- Local preflight: 52 synthetic and five GUI/help checks passed. An initial
  desktop sandbox temp-directory denial was resolved by using workspace-local
  test temp files outside that restricted execution context; no code fix needed.
- UI follow-up: exact supplied teal #168a91 and Work on selected regions label.
  Region profiles remain bilateral; choosing an L/R search alias now preserves
  the independently chosen working hemisphere. Native regression covers both
  L-alias/R-working and R-alias/L-working choices with identical group identity.
- Current version0.7.5 leaves numeric/atlas functions unchanged; GUI selection
  behavior and test workflow change. Local52 synthetic/design5/hierarchy12 checks
  passed. The later completion entry below records Windows11 outcomes.

- Fresh Windows11 design run39899939662 passed five checks; actual GUI reviewed.
  Windows11 Enterprise build26200 ARM64/x64 Slicer emulation confirmed. Stock
  visual run39900188928 failed: Mesa12/OpenGL3.0, GLSL1.50 rejected and identical
  blank camera images. This is a genuine failed graphics test, retained as such.
  Added a separate optional pinned Mesa26.2.4 app-local compatibility experiment
  in the disposable VM, following its provider per-app deployment layout. No
  application math, user PC drivers, global registry or Slicer dependencies change.
- Final results/correction: hierarchy run39900184868 passed12. Mesa experiment
  run39900638123 exited before producing a test receipt, so its optional workflow
  runtime was removed. Stock graphics failure remains explicit. Local Intel
  UHD770 OpenGL3.2 rendered16 parcels and two views (three checks), visually
  reviewed; this does not substitute for fresh-VM rendering acceptance.
- Delivery/review: (1) README editor screenshot: dark text and teal Work on
  selected regions. (2) Windows11 Actions receipts: GUI5 and hierarchy12 pass,
  stock visual fail. (3) Review actual atlas/mirror boundaries in Slicer on a
  supported graphics setup. Native x64 Windows11 VM and original startup
  traceback remain unavailable; prior guide/download/hierarchy/symmetry/version
  requests remain satisfied. No biological/anatomical acceptance is asserted.


### 2026-10-22 | Agent Codex | Dependency checks and isolated CLI environment

- Follow-up: ensure dependencies are installed; offer Conda or an equivalent.
  GUI runtime belongs to the official Slicer application; optional CLI gets a
  separate Conda recipe. No Conda Qt, pip slicer, secrets or local configs added.
- Added `doctor`, usable even without site packages, and automatic GUI/NIfTI CLI
  preflight. Added a fresh Conda creation/test job, explicit version bounds and
  setup/update commands. Reports are read-only; missing GUI runtime points to
  Slicer repair/system prerequisites. Current tool version 0.7.4.
- Fresh cloud startup 0.7.3: Windows and Ubuntu passed in run 39738903061 after
  fixing Ubuntu's missing libxcb-shape.so.0 before Python. Reviewed both actual
  cloud screenshots before load tests. Windows default VM graphics warnings
  limit rendering claims; cloud load tests select bundled Qt software OpenGL.
- Cloud checkouts also exposed CRLF/LF source-byte differences. Added attributes
  to stabilize new source hashes; retain earlier recorded hashes as historical.
- Local dependency tests cover installed CLI, missing site packages, wrong GUI
  interpreter, native Slicer preflight and preserved existing behavior. Fresh
  Conda solved Python3.12.15/NumPy2.5.4/nibabel5.4.2; 52 tests passed in each
  cloud pip/Conda job (run39740223161). Current cloud hierarchy tests passed
  11/11 on each OS with identical source hash (run39740224459). Windows
  software OpenGL still logged unsupported GLSL1.50; 3D rendering is unverified.
  Ubuntu logged no graphics errors. User traceback remains unknown. No scientific atlas-boundary or GPU acceptance is inferred.


### 2026-10-22 | Agent Codex | Fresh cloud-machine initialization investigation

- Trigger: reported initialization bugs without a traceback; asked whether
  dependencies were responsible and requested a fresh cloud-computer test.
  Prior evidence covered local native Slicer plus fresh cloud Python tests,
  not a cloud Slicer installation. The exact reported failure remains unknown.
- Added a bounded manual workflow using new GitHub-hosted Windows/Ubuntu VMs,
  official fixed/checksummed Slicer 5.12.0 and separately fetched public AFNI
  inputs. No local package/config/cache or personal data is transferred.
- Test stages: design/import first, visual review of actual cloud screenshots,
  then public-input hierarchy/load behavior. Local preflight passed 49 synthetic
  tests and import-based design checks. Cloud GUI startup passed on both operating systems in run 39738903061.
  Native public-input loading and the dependency follow-up are tracked above.
- Current entry: Actions / Fresh-machine Slicer. Receipts, logs and screenshots
  identify the tested commit/runtime; volumes and segmentations stay ephemeral.
  Actual user startup error, older Slicer versions, consumer-PC GPU/driver
  differences and anatomical acceptance remain separate unresolved questions.


### 2026-10-22 | Agent Codex | Visible tool version and changelog

- Request: maintain the changelog, show a version in GUI and CLI, and push.
  Starting public commit: 5b9f0f2 (0.7.1). Current candidate tool: 0.7.2.
- One existing VERSION value now supplies the main title/header, setup-help
  title, CLI help/--version and generated receipts. The unchanged hierarchy
  resolver retains its distinct module version and earlier validation hashes.
- Verified 49 synthetic tests, including CLI help/--version from another working
  directory, and five native Slicer 5.12.0 design/help checks. Visually reviewed
  refreshed screenshots. AST changes are confined to GUI/help/parser functions.
  Prior atlas and mirroring evidence remains labelled with its tested version.
- Review (1) README screenshot: header reads 0.7.2; (2) `python armins.py --version`:
  output matches the header and this changelog; (3) inspect earlier scientific
  limits before accepting edited anatomy. Earlier requested colour/contrast,
  hierarchy, hemisphere, manual and download features remain delivered.


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
