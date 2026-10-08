# Orbit Libraries

## Description
The shared source repository for LibOrbitUI, LibOrbitColorPicker, LibOrbitGlow and LibOrbitSearch. Each library retains
its own runtime API, license and independently versioned release.

## Purpose
Maintain reusable addon services once, develop consumers through directory junctions, and distribute ordinary runtime
files from verified releases.

## Implementation
Each project directory contains its README, license, `.pkgmeta` and stable runtime folder. Addons embed only that
runtime folder through XML or Lua load manifests; the repository itself is not a player-installable addon.

| Project | Runtime path | License | Release destinations |
|---|---|---|---|
| [LibOrbitUI](LibOrbitUI/README.md) | `LibOrbitUI/LibOrbitUI-1.0` | All Rights Reserved | GitHub |
| [LibOrbitColorPicker](LibOrbitColorPicker/README.md) | `LibOrbitColorPicker/LibOrbitColorPicker-1.0` | MIT | GitHub |
| [LibOrbitGlow](LibOrbitGlow/README.md) | `LibOrbitGlow/LibOrbitGlow-1.0` | MIT | GitHub and CurseForge project 1586462 |
| [LibOrbitSearch](LibOrbitSearch/README.md) | `LibOrbitSearch/LibOrbitSearch-1.0` | All Rights Reserved | GitHub |

The path-filtered workflows run on relevant changes pushed to `main` and share release tooling. Tags use
`<Library>-<MAJOR.MINOR>`; versions continue from the previous repositories. The first monorepo releases are LibOrbitUI
1.1, LibOrbitColorPicker 1.2 and LibOrbitGlow 1.8; LibOrbitSearch starts at 1.0. Package versions are independent of
runtime API revisions.

Orbit's build resolves the latest published stable release separately for each owned library declared in its
`.scripts/library-releases.json`. It verifies the runtime ZIP, checksum, source metadata and tag commit, then shares
one exact lock across validation and packaging. Companion consumers retain full commit SHA and runtime-path pins in
`.pkgmeta`. After a library release, verify its assets and complete each affected consumer's delivery strategy; a
source push alone does not deliver a new library to installed addons. Players receive it in the next consumer release.

## Gotchas
- LibOrbitUI exports a private API per embedding addon, sharing only its Edit Mode settings-window coordinator.
  ColorPicker, Glow and Search use LibStub's shared versioned instances; product settings and services retain their own
  runtime owners.
- Each project and runtime directory retains its own license. There is no repository-wide MIT grant for LibOrbitUI.
- GitHub's repository-wide latest release can belong to any library. Orbit selects completed stable releases by exact
  library-prefixed numeric versions. Its annotated addon release tag retains the build lock so packaging cannot select
  a newer library after validation; companions do not use this resolver.
- Addon development paths are junctions into this repository. Packages contain ordinary files, never workspace links.
  Existing addon folder and runtime library names remain stable.
- The migration preserved the old local Git metadata under this checkout's `.git/legacy-repositories/`; it is not
  distributed. Historical remote repositories remain available. The imported source snapshots are UI `382c6e3`,
  ColorPicker `faf2dc7` and Glow `c3e8fcb`, including pending local documentation.
- Source and package checks do not certify WoW rendering, combat protection or taint. Runtime changes require
  verification in consuming addons.

## References
[Release workflows](.github/workflows/README.md), [release tooling](.scripts/README.md), and the workspace
`orbit-libraries` skill.
