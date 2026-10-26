# ARMins project note

Updated 2026-10-26 | Asia/Shanghai.

## Current status and entry points

ARMins supports expert curation of the insula atlas and provides a standalone
candidate editor for ARM level-6 region groups in symmetric NMT v2.1. The
original insula preset remains the default. README.md is the complete GUI and
operator/download guide;
armins.py is the executable editor source; `henry_preset.py` is the current
two-group CL-only Slicer entry point; CHANGELOG.md and provenance.json record
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

- Current source: editor 0.7.8 and Henry viewer 0.1.3, both local/unreleased.
  The one tracked `atlas_config.json` supplies the three shared server UNC
  inputs. The source data stay external. Ordinary Python auto-discovers the
  newest stable installed Slicer; an explicit `--slicer` path overrides it.
  The user-requested config is portable as declared UNC syntax, but loading
  still requires server access or explicit mounted/native inputs. The other
  PC reported WinError 1326 on the exact template, an SMB logon failure;
  manual authentication and a successful rerun there remain pending. Technical
  loading/display is distinct from anatomical acceptance.
  Historical 0.7.5 validation below remains tied to its recorded hashes.
- Review in order: (1) follow README's GUI versus CLI dependency path; `doctor`
  should report ready; (2) inspect Actions receipts/checks for the selected OS;
  (3) open the atlas in a supported desktop graphics environment and judge its
  rendering and anatomy. Windows VM functional passes do not certify rendering.
- Original reported initialization bug remains unidentified without the user's
  first traceback and Slicer version; cloud startup/import/load paths passed.

## Operations journal

### 2026-10-26 | Agent Codex | Cross-PC error identified as SMB logon failure

- The user supplied the other PC's concrete error: `OSError: [WinError 1326]`
  when Python opened the exact UNC template configured in `atlas_config.json`.
  This Windows code is `ERROR_LOGON_FAILURE` (user name or password incorrect).
  The evidence points to SMB authentication for that process/session, not a
  directory spelling defect. File Explorer reaching the share root does not
  establish that Python can read the exact file under the same credentials.
- README now directs the operator to authenticate manually from the same
  ordinary, non-elevated user session with `net use` and a local password
  prompt, then rerun Henry. No credentials were requested, stored or used by
  this agent. The other PC's post-authentication outcome is pending, so its
  scene is not claimed repaired. Henry 0.1.3 already surfaces the exact I/O
  error before opening Slicer; no runtime code changed for this finding.

### 2026-10-26 | Agent Codex | Cross-PC blank startup investigation (Henry 0.1.3)

- User reports Slicer opens with an empty scene on another PC; File Explorer
  can reach the configured UNC atlas root there. No Slicer traceback or version
  from that PC was available at this stage; the later WinError 1326
  observation below resolves the failure category. Source
  review found launcher 0.1.2 opened Slicer before checking its companion
  modules or individual source files; failures in `show()` then appeared only
  in Slicer's Python console/log.
- Added stdlib companion/config/per-file readability preflight before spawn.
  Native loading now waits for the Qt event loop and reports stages; any
  exception shows its traceback in an error dialog and opens the Python
  Console. No source or scene files are written. This improves diagnosis and
  stops known missing-input cases before blank GUI startup; it does not prove
  the cross-PC issue is fixed. Synthetic missing-hierarchy and incomplete-clone
  cases stopped before `Popen`; malformed JSON was rejected. All 57 synthetic
  tests passed.
- Current CI at f63f756: Ubuntu passed all checks, Windows setup v4 succeeded
  but the first doctor command failed because `conda` was absent in Git Bash
  login PATH. Switched the CI step shell to PowerShell. Run
  40306176609 passed on Windows and Ubuntu, including all 57 synthetic tests.

### 2026-10-26 | Agent Codex | Supplied atlas config and installed Slicer discovery (editor 0.7.8, Henry 0.1.2)

- User superseded the ignored personal config with one supplied Git-tracked
  `atlas_config.json`, containing the verified template, ARM6 and hierarchy UNC
  paths only. Updated both entry points, README, AGENTS, tests and provenance;
  no credentials or atlas files were copied. Cross-platform config parsing
  validates UNC syntax without accessing the server and preserves server/share
  identity on POSIX. The previous local-only behavior remains in history below.
- Henry launcher now probes PATH, immediate standard Windows per-user/Program
  Files Slicer installation folders, and bounded registered app/install paths, picks the highest numeric stable version,
  and gives `--slicer` explicit precedence. No recursive drive search, download
  or installation. Found installed Slicer 5.12.3 over 5.12.0 on this host. Final
  launcher tests also cover `Slicer5.12.2` folders and reject unrelated
  `PrusaSlicer.exe` candidates; a missing or empty registry InstallLocation
  falls back to DisplayIcon only when its basename is `Slicer.exe`.
- Bounded tests: 55 synthetic tests passed, including shared config and launcher
  missing/override/version/path-with-spaces cases. CLI versions and read-only
  doctor reported 0.7.8/0.1.2 and ready. Ordinary `python henry_preset.py`
  launched a fresh Slicer 5.12.3 process (launcher PID 71688; app child 33608).
  The new Slicer 5.12.3 session log confirms successful UNC volume loads and
  Henry 0.1.2 reporting 8 visible Insula and 133 hidden cortex segments, with
  no logged load or VTK errors. Earlier 0.1.1 exact mask/render checks are
  historical evidence only; new 0.1.2 anatomical review remains pending. Anatomical
  acceptance remains pending.
- Previous CI: Ubuntu passed at commit e29c090; Windows stopped in Miniforge
  setup before tests because shell initialization required elevation. The CI
  action now uses official setup-miniconda v4 with `run-init: false` and explicit
  `conda run` steps. New CI outcome pending publication.

### 2026-10-26 | Agent Codex | Henry-first guide and clean CI test correction

- After publishing ARMins editor 0.7.7 and Henry viewer 0.1.1 at commit `8c3cebecd8f1442a8334fd9f212efb5de540c55a`, the Ubuntu Conda CI job failed one synthetic test: its explicit-template assertion omitted the atlas path and passed locally only because the ignored personal config supplied `ARM_PATH`. The actual runtime input requirement behaved correctly. Changed the test to supply its synthetic atlas explicitly; no runtime module or viewer code changed.
- Reframed README Quick start around `cd D:\ARMins; python henry_preset.py`, the three-key ignored local config and the 8/133 left-group display controls. An alternate Slicer executable can be passed with `--slicer`; the `armins.show_gui()` operator steps remain in a separate manual-editing section and fresh scene. Henry display groups are not automatically editor-bound scope or mirror groups.
- Verification: copied only source modules and five synthetic test files to a temporary clean fixture, with no `local_atlas_config.json` and ARMINS input variables unset. All 53 tests passed; the fixture was removed. Earlier native 141-mask and rendered-view checks remain tied to unchanged editor/viewer source hashes. A new CI run is pending publication of this correction; anatomical acceptance remains open.

### 2026-10-26 | Agent Codex | Henry preset rendering and direct launch (viewer 0.1.1)

- Visual review corrected the earlier 0.1.0 technical-only pass: the GUI listed both groups but emitted repeated VTK lookup-table/scalar-type errors and showed no colored overlays. Mask equality alone did not verify rendering. The earlier 0.1.0 native receipt is retained as a failed rendering candidate, not promoted.
- The 0.1.1 script loads the temporary ARM source labelmap hidden, keeps its import color tables until after removing the source node, and clears Red/Yellow/Green label-volume IDs explicitly. Native Slicer 5.12.0 rerun passed exact source-ID mask equality for all 8+133 segments, initial Insula visibility, cortex visibility switch, no bilateral label layer, unchanged source hashes and absence of the two reported VTK error phrases. Captures `work/cl_level6_views_20261026/henry_insula_011.png` and `henry_cortex_011.png` were independently visually checked: colored left CL overlays appear in all three slice planes on the full NMT background. This is technical display QC, not anatomical acceptance.
- Added ordinary-Python direct launch: `cd D:\ARMins; python henry_preset.py` opens the installed Slicer 5.12.0 with this same file; `--slicer` overrides its location. Help/version and mocked launch argv passed. The actual command opened a new Slicer process (launcher PID 69208, app PID 45096) while earlier scenes remained open. No dependencies or source data were installed/changed. README is the current one-command guide.
- Priority review: (1) open the new Henry preset Slicer window and confirm the eight Insula CL parcels and full NMT extent; (2) in Data hide Insula and show cortex, then select the cortex group in Segment Editor and confirm 133 CL parcels; (3) inspect laterality, identities and boundaries in three planes before any scientific use. Existing user scenes and annotations remain untouched.

### 2026-10-26 | Agent Codex | Henry preset consolidation (viewer 0.1.0)

- Latest user request superseded the two separate viewer scripts with one `henry_preset.py` entry point in a fresh Slicer scene. It loads the full NMT template once and creates two independent segmentations from the same immutable ARM6 source: left Insula, eight previous preset labels, visible/selected by default; left cortex, all 133 declared CL L6 labels, hidden but selectable. The full bilateral labelmap is removed from the scene and not overlaid. Manual edits to one group do not synchronize into the other. ARMins editor 0.7.7 and existing user scenes remain untouched.
- The separate-scene native receipt at `work/cl_level6_views_20261026/native_views_receipt.json` records exact per-segment source-ID voxel equality for 8+133 masks, both group visibility states, absence of right/subcortical segments and bilateral label layers, and unchanged template/atlas/hierarchy source hashes. Earlier two-script and exact-subtree trials are preserved in the same receipt as superseded evidence. The disposable native test script was removed after recording the result.
- README is the current operator guide with one startup command, a source table and flowchart. Review the visible Insula group first; in Data use the eye icons to hide Insula and show cortex, then select the cortex segmentation in Segment Editor. No derivative is written automatically. Scientific anatomical acceptance and final human visual inspection remain pending.

### 2026-10-26 | Agent Codex | Correction: previous eight Insula parcels

- User clarified that the second script should show the previous ARMins Insula preset, not the exact two-leaf `CL_Ins` hierarchy subtree. The earlier exact-subtree choice and its two-label native test remain historical evidence below and in the shared receipt, marked superseded. `show_cl_insula_level6.py` now uses immutable `DEFAULT_FULL_INS_IDS["L"]`: 39, 41, 42, 43, 226, 228, 229, 230. The all-CL script remains 133 labels. No editor or atlas source changed.
- The current final entry points are `show_cl_level6.py` (133 left cortical L6 labels) and `show_cl_insula_level6.py` (the previous eight left Insula parcels). See README for the fresh-scene commands and exact-source table. Technical and visual verification are recorded with the combined receipt; scientific anatomical acceptance remains open.

### 2026-10-26 | Agent Codex | Two CL-only level-6 views (viewer 0.1.0)

- User superseded the broader additive-editor request with two simple views: all left cortical CL level-6 labels, and the exact `CL_Ins` hierarchy subtree. The selected hierarchy has 133 cortical left `CL_*` L6 IDs, all present in the configured ARM6 image. Exact `CL_Ins` is the cortical left level-5 index 227 subtree with two L6 descendants, `CL_Ia/Id` 228 and `CL_Ig` 229; the editor's eight-label Insula preset is a different operational group.
- Added `show_cl_level6.py` as the shared Slicer import/view entry point and `show_cl_insula_level6.py` as the exact-subtree selector. Both read the ignored explicit local config, validate source grid and identities, import only selected left-cortical labels into one segmentation, remove the temporary full ARM labelmap node, clear the bilateral label layer, fit the full NMT background and move slice planes through the selected mask. They refuse a populated scene and leave ARMins 0.7.7 editor logic unchanged. Source acquisition dates are not established by these filenames; no data migration, registration, export or scientific acceptance is claimed.
- Bounded read-only selection check: 133/133 declared all-CL IDs and 2/2 exact-subtree IDs were present. Native Slicer 5.12.0 separate-scene verification in `work/cl_level6_views_20261026/native_views_receipt.json` passed for both views: 133 and 2 imported segments respectively; each segment's voxel mask matched its tagged source ARM6 integer ID; no label volume node or label slice layer remained; template, atlas and hierarchy source hashes were unchanged. A current-directory-independent import probe passed. The one disposable native test harness was removed after recording the receipt.
- Opened one additional normal Slicer window for the exact two-label subtree, preserving other user windows and scenes. Technical visual review of the final window remains pending; operator should inspect CL laterality, full template field of view, two parcel names/overlays and boundaries before scientific use. README holds commands, source table and workflow chart; CHANGELOG holds viewer 0.1.0 history.

### 2026-10-26 | Agent Codex | Explicit local atlas config (0.7.7)

- User correction: persistent Windows environment alone did not reliably preset the live Slicer GUI; explicit local inputs were required. Added ignored `local_atlas_config.json` beside `armins.py` with the verified IP UNC template, ARM6 and hierarchy paths. It takes precedence over input environment variables; explicit function, CLI and GUI selections remain available. Output directory is unchanged. Malformed/incomplete/nonabsolute config fails clearly. No atlas algorithm or Insula mode behavior changed.
- Verification: `armins.py --version` reports 0.7.7; a read-only `check --dry-run` validated the known template/ARM6 hashes and matching 0.25-mm grids. Focused config precedence/errors test passed, then 53 synthetic tests passed. Native Slicer 5.12.0 behavior smoke in a separate scene with all three input environment variables removed passed 11 checks (`work/explicit_config_native_20261026/behavior_receipt.json`), including the actual Insula GUI Validate/load and mirror controls; source hashes were unchanged.
- A separate normal visible Slicer window was opened for review, preserving the original user process and scene. Its GUI reported `Insula preset` and `Inputs validated and groups loaded`; `work/explicit_config_native_20261026/live_gui_receipt.json` records that status and the three config paths. Visual technical inspection found the preset fields populated, eight CL parcels plus scope in the editor, and MRI/parcel overlays in three planes. No painting, source edits or anatomical acceptance were performed.
- After config-only startup succeeded, cleared only the three User environment values created earlier, after checking that they still exactly matched the known UNC preset. Next review: inspect laterality, parcel identity and boundaries in the visible window before editing; use the ignored config for this checkout and restart/reload ARMins after changing it. The original reported startup error remains separately unidentified.

### 2026-10-26 | Agent Codex | Personal atlas preset

- Request: preset the local symmetric NMT v2.1 template, supplied ARM6 labels and matching hierarchy table for ARMins.
- Before change, the three per-user ARMINS environment values were unset. Verified all three files on the mapped atlas drive were nonempty; set ARMINS_TEMPLATE, ARMINS_ATLAS and ARMINS_HIERARCHY in the Windows User environment only. Kept atlas files, repository code and output-directory setting unchanged.
- Read-only `armins-cli` `check --dry-run` validated the 256 x 312 x 200 matching 0.25-mm template/ARM6 grids, reported expected source hashes and `writes: []`. The three User environment settings were reread successfully. A bounded WM_SETTINGCHANGE/Environment broadcast returned successfully for future Windows-launched processes.
- Existing Slicer/ARMins 0.7.6 process predates this preset. Its GUI initially showed blank input fields and a prior load error; the template intensity field was then filled through the UI, while the ARM6 and hierarchy fields remain blank. No scene loading or editing was performed. Restart Slicer to pick up all three preset defaults; GUI loading and anatomical acceptance remain untested.
- Correction after user report: the mapped-drive preset above was unsuitable for the live Slicer process. Replaced all three User settings with verified direct IP UNC paths to the same immutable template, ARM6 and hierarchy sources, reread the stored values and broadcast WM_SETTINGCHANGE/Environment successfully. The current Slicer process still needs its own in-process configuration or restart to inherit these values.
- Independent Slicer 5.12.0 `behavior` smoke test (`work/unc_insula_native_20261026/behavior_receipt.json`) imported ARMins 0.7.6 in a separate scene with the UNC paths and passed 11 checks, including the actual Insula preset Validate/load button and mirror button; original template/atlas hashes stayed unchanged. The earlier load error text is the expected guard for ARM hierarchy mode with no explicitly chosen hierarchy result, not evidence that the built-in Insula preset fails. The live existing Slicer GUI and anatomical boundaries remain for operator review.


### 2026-10-26 | CLI install path

- Request: use Conda for the CLI install in the repository, rather than a
  one-off pip virtual environment.
- Change: README, `doctor` guidance, `requirements.txt` note, and synthetic CI
  use `environment.yml` / `armins-cli` on Windows and Ubuntu. No atlas, mirror,
  or GUI algorithm change. Tool version 0.7.6.
- Local check: `armins-cli` doctor ready (Python 3.12.15, NumPy 2.5.4,
  nibabel 5.4.2) and 52 synthetic tests passed. The 0.7.5 cloud pip jobs
  remain historical evidence. This entry does not claim a new cloud run.

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
