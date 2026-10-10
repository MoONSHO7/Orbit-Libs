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

Orbit, Portal, Compass, Status and Talents manually pin each verified library release commit and nested runtime path
in `.pkgmeta`. BigWigs fetches and embeds those externals normally; automatic latest-release selection is deferred.
After publication, verify the assets, update affected consumer pins and validate their packages. Players receive the
library update through a subsequent consumer addon release.

## Gotchas
- LibOrbitUI exports a private API per embedding addon, sharing only its Edit Mode settings-window coordinator.
  ColorPicker, Glow and Search use LibStub's shared versioned instances; product settings and services retain their own
  runtime owners.
- Each project and runtime directory retains its own license. There is no repository-wide MIT grant for LibOrbitUI.
- GitHub's repository-wide latest release and BigWigs' `tag: latest` can belong to another library. Verify the
  requested library's completed namespaced release before updating its full commit pin.
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
