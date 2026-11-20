# LibOrbitBridge

## Description
The independently versioned, UI-less bridge between third-party addons' data and Orbit addons: it reads another
addon's database, cleans it and hands consumers verdicts they can draw.

## Purpose
Orbit and its companions should not rebuild databanks such as Questie's, nor clean the same data twice. One library
reads the installed provider, applies Orbit's own availability policy and curated corrections, and serves every
consumer, so Compass and Orbit's own map agree without depending on each other. QuestieDB is the first provider.

## Implementation
`LibOrbitBridge-1.0/` is the authored runtime directory, loaded through `LibOrbitBridge-1.0.xml` after LibStub.
Orbit-Compass embeds it through the `Libs/LibOrbitBridge-1.0` junction; editing that path edits these files. The
runtime contract is in [its README](LibOrbitBridge-1.0/README.md).

`.pkgmeta` defines the runtime package and excludes documentation and development metadata. A path-filtered workflow
releases relevant changes pushed to Orbit-Libs `main` under `LibOrbitBridge-MAJOR.MINOR` tags, starting at 1.0. Its ZIP
contains only the Lua, XML and license under `LibOrbitBridge-1.0/`, with a SHA256 sidecar.

Compass's `.scripts/check-questie.py` loads this runtime for real through its harness and covers the index,
availability, existence, curated list, objective planning, log coalescing and demand release.

## Gotchas
- Consumers pin a full commit from a completed `LibOrbitBridge-*`
  [GitHub release](https://github.com/MoONSHO7/Orbit-Libs/releases) with `path: LibOrbitBridge/LibOrbitBridge-1.0`.
  Verify publication and runtime assets before updating consumers; release numbers are independent of `lib.API`.
- All Rights Reserved; both this project and its runtime directory carry the notice.
- Provider data is never bundled or copied: QuestieDB's licence does not allow it. The bridge reads the installed copy.
  The curated list holds quest IDs with evidence from Wowhead Classic and warcraft.wiki.gg, cross-checked against
  Questie's list; its per-quest evidence lives in the Orbit workspace's `develop/` record, not in the package.
- The library owns no frames beyond its event listener and driver frames, no saved variables and no localized strings;
  presentation, per-character choices and settings belong to each consumer.

## References
[Runtime contract](LibOrbitBridge-1.0/README.md), [release workflow](../.github/workflows/README.md),
[.pkgmeta](.pkgmeta), [license](LICENSE).
