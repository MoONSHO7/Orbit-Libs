# LibOrbitUI

## Description
The shared UI library for Orbit and independently installed addons, targeting WoW 12.1.0 and Lua 5.1. Its source and release metadata live in the Orbit-Libs repository. API 1.6 additionally identifies Retail and Forever for consumer-owned compatibility policy; Forever rendering and native behavior still require client verification.

## Purpose
Maintain movement, the settings window and renderer, common widgets, pixel rendering and cancellable work once. Consumers supply feature behavior, storage, localization and optional advanced editing services.

## Implementation
`LibOrbitUI-1.0/` is the only authored runtime directory, organized into `Core/`, `Rendering/`, `Movement/`, `Config/` and `Addon/`. Config separates widgets, pickers and dialogs. The stable `LibOrbitUI-1.0.xml` entry point orders these modules and exports the versioned API on each embedding addon's private namespace. A player installs an addon with an embedded library; this project has no separate addon TOC or required player download.

Development addons link directly to that directory:

| Addon path, relative to the workspace | Link target |
|---|---|
| `Orbit/Orbit/Core/Libs/LibOrbitUI-1.0` | `Orbit-Libs/LibOrbitUI/LibOrbitUI-1.0` |
| `Orbit-Portal/Libs/LibOrbitUI-1.0` | `Orbit-Libs/LibOrbitUI/LibOrbitUI-1.0` |
| `Orbit-Compass/Libs/LibOrbitUI-1.0` | `Orbit-Libs/LibOrbitUI/LibOrbitUI-1.0` |
| `Orbit-StatusWidget/Libs/LibOrbitUI-1.0` | `Orbit-Libs/LibOrbitUI/LibOrbitUI-1.0` |

These are Windows directory junctions. Editing an addon library path edits the same physical files; `/reload` reads the changes immediately. Consumer-owned fetch and package tools materialize ordinary files without replacing those development links.

`.pkgmeta` defines the runtime package and excludes module READMEs and development metadata. A path-filtered workflow releases relevant changes pushed to Orbit-Libs `main` under `LibOrbitUI-MAJOR.MINOR` tags. Each release attaches a ZIP containing only `LibOrbitUI-1.0/` runtime files and its license, plus a SHA256 sidecar. Other libraries retain separate release histories.

The addon-owned `Orbit/.scripts/package-orbit-ui.py` verifies development links, generates Portal localization and records content hashes. Packaging materializes ordinary files into an explicit staging directory; it never ships workspace links.

Orbit and standalone Portal use the same window chrome, tabs, scrolling, layout, widgets and basic text primitives. `Config.Defaults` owns their baseline dimensions. Shared prompts, swatches and color/font/texture controls accept consumer-owned labels, values, catalogs and persistence. Orbit retains advanced art/border/glow previews and profile/theme policy.

## Gotchas
- Addon repositories ignore their local library links; this repository tracks the actual source. Keep the library project available during development.
- Consumer `.pkgmeta` externals use `MoONSHO7/Orbit-Libs`, a completed `LibOrbitUI-*` release's full commit SHA and `path: LibOrbitUI/LibOrbitUI-1.0`. API 1.8 is independent of the package version; all four consumers need the coordinator/lifecycle release before distributed delivery is complete.
- Settings and services remain private to each addon. Only the protocol-1 settings-window coordinator is shared across embeddings; it owns visibility claims, not SavedVariables or Blizzard Save/Revert transactions.
- Standalone app composition registers its Blizzard AddOns category and, by default, an Enabled control. Products marked `alwaysEnabled` omit the control; matching controllers declare no Enabled setting. A real-host bridge suppresses duplicate entry points while retaining slash commands and hosted Edit Mode settings.
- Color editing uses optional LibOrbitColorPicker and LibStub; addons without editable swatches need neither. Revision 10 supplies explicit tooltip/class-color context and session-safe editing; the default independent provider disables editing with older revisions.
- [All Rights Reserved](LICENSE). The runtime directory includes the same license notice for embedded distributions; public source availability does not grant a reuse license.
- Packaging checks do not certify rendering, secure actions or taint; verify the consuming addons in WoW.

## References
[Runtime contracts](LibOrbitUI-1.0/README.md), [release workflow](../.github/workflows/README.md), [.pkgmeta](.pkgmeta), [license](LICENSE), and [LibOrbitColorPicker](../LibOrbitColorPicker/README.md).
