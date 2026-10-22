# ARMins change log

One consolidated history. README.md is the operator guide.

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
