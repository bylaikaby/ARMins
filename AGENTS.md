# ARMins working contract

- Read README.md, CHANGELOG.md, provenance.json and docs/project_note.md before
  substantial changes. Keep the single-module operator discoverable.
- Keep atlas/template data, edits, generated receipts, environments, credentials
  and personal machine configuration out of Git. The user-approved tracked
  `atlas_config.json` declares only the shared server paths for the template,
  ARM6 atlas and hierarchy; keep credentials and source data out of it. Explicit
  user inputs and documented ARMINS environment variables remain supported.
- Preserve original data and existing scene nodes. Validate inputs and the full
  native voxel lattice before mutation; do not silently resample, crop labels,
  drop unknown segments or alter scientific definitions.
- Test synthetic geometry, identity and failure cases first. Native Slicer
  validation needs a separate scene and explicitly supplied data; distinguish
  array tests, GUI behavior and anatomical acceptance.
- Every materially changed script/module carries version status, updated date
  and the CHANGELOG.md reference. Update the consolidated changelog and dated
  project note with observed evidence and unresolved limits.
- Keep dry runs non-mutating and saves explicit. Retain source hashes, geometry,
  parameters, software versions and processing time in generated receipts.
- Review the exact staged publication payload for private paths and data. Keep
  documentation, tested code hashes and provenance consistent before delivery.
