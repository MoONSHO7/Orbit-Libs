# Independent library releases

## Description
Three main-branch workflows publish independently versioned library packages through one reusable workflow.

## Purpose
A change to one library releases that library alone. Shared release-tool changes validate and release all three.

## Implementation
The thin callers watch their runtime directory, `.pkgmeta`, root license and relevant release configuration. Documentation-only changes do not trigger releases. There are no tag-push or feature-branch triggers; a published tag cannot launch a duplicate run. Manual runs on `main` use the same path and support retries.

`release-library.yml` checks out the source and the pinned BigWigs packager, then calls `.scripts/release-library.py`. Each library has its own concurrency group and tag namespace: `LibOrbitUI-X.Y`, `LibOrbitColorPicker-X.Y` and `LibOrbitGlow-X.Y`. Numeric package versions continue from the standalone repositories; the first monorepo versions are 1.1, 1.2 and 1.8.

Only the selected committed subproject enters an isolated packaging checkout. Its local numeric tag supplies the TOC/package version; the public tag resolves to the original monorepo commit. The helper validates the ZIP before creating a GitHub draft and checks the published assets afterward. UI and ColorPicker publish only on GitHub. Glow retains CurseForge project 1586462 and uploads the exact validated ZIP before publishing its GitHub draft.

## Gotchas
- `GITHUB_TOKEN` receives `contents: write` only in release jobs. No PAT is required. Only Glow receives `CURSE_API_KEY`; its caller forwards that secret explicitly.
- A repository-wide `/releases/latest` request cannot select the latest release of a particular library. Filter by the library's tag prefix and published stable state.
- An ambiguous interrupted CurseForge upload requires reconciliation, as documented in `.scripts/README.md`; reruns never blindly duplicate that upload.
- Library publication does not update consumer addons. Consumer pins use the monorepo commit plus `path: LibOrbitUI/LibOrbitUI-1.0` (or the corresponding picker/glow path), followed by their own validation and release.

## References
`../../.scripts/README.md`, subproject package metadata, and the workspace `orbit-libraries` skill.
