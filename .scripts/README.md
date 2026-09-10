# Library release tooling

## Description
Independent release versions and validated packages for the three libraries in this repository.

## Purpose
Publish one library from a monorepo commit without shipping sibling projects or letting another library's tags change its package version.

## Implementation
`release-library.py` prepares an isolated Git snapshot of one committed subproject, with a numeric local packaging tag. BigWigs reads that snapshot's `.pkgmeta`; the public `LibOrbitUI-X.Y`, `LibOrbitColorPicker-X.Y` or `LibOrbitGlow-X.Y` tag points to the real monorepo commit. Initial monorepo versions continue at 1.1, 1.2 and 1.8 respectively.

The helper verifies the complete runtime file set, Lua 5.1/XML/TOC load closure, licenses, artwork and the pinned LibStub external before any upload, then normalizes ZIP ordering, timestamps and modes for reproducible retries. SHA256 sidecars accompany every ZIP. Glow also supplies `release.json` for addon clients. `source.json` identifies the source commit and runtime subdirectory.

The reusable workflow runs the helper's `prepare`, `verify`, `reserve` and `finish` commands. Glow inserts `curse-upload`, which sends the validated ZIP once through the CurseForge upload API and records its confirmed file ID. Work directories must be outside the checkout. Preparation never reads working-tree library files or a workspace `.env`; `prepare --commit <SHA>` supports local checks of an explicit source snapshot.

## Gotchas
- Only the selected library's tags influence its next version. Retries reuse a tag on the same commit; stale or divergent runs cannot create a newer release.
- Published releases are verified and preserved. Drafts can resume only for their original source commit.
- A Glow draft with `curse-upload-started.json` but no completion receipt is ambiguous: inspect CurseForge before retrying. After confirming upload success, a maintainer can copy the matching started receipt, add the confirmed positive integer `curseFileID`, and upload it as `curse-upload-complete.json` on that draft; if no upload occurred, remove the started receipt before retrying. Receipts must match the source, version and ZIP checksum before any assets can be replaced or an upload skipped.
- Release versions differ from Lua API revisions. New APIs still require compatibility checks and consumer delivery.
- There is one GitHub-wide latest release across this monorepo. Consumers must resolve the intended library's tag/release, or retain an exact verified commit and runtime path; automatic per-library latest resolution is not implemented here.

## References
`../.github/workflows/README.md`, each subproject's `.pkgmeta`, and the workspace `orbit-libraries` skill.
