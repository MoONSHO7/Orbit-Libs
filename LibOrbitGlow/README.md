# LibOrbitGlow

## Description
A LibStub glow library for WoW frames: four built-in icon glows from Blizzard art, two bundled status-bar outline glows
and an open registry that glow packs such as [Orbit: Media](https://www.curseforge.com/wow/addons/orbit-pack-glows)
fill with their own animated atlases. MIT licensed; requires only LibStub.

## Purpose
Let a host addon write its glow code once: whatever pack the player installs appears in that addon's glow options with
no host change, and pooling, recolouring, restricted aura hosts and secret values are handled in one place.

## Implementation
- **Modules.** `LibOrbitGlow-1.0/LibOrbitGlow-1.0.lua` (revision 14) owns the engine, the `lib.glows` registry, the
  `Proc` lifecycle, the raw `Flipbook` sink and the `Button` (Classic) renderer; `StatusBarGlows.lua` (status-bar
  revision 14) owns the separate status-bar registry and renderer and its `Textures/` sheets. `LibOrbitGlow-1.0.xml`
  loads both; the TOC adds the packager-fetched LibStub for the standalone CurseForge install.
- **Install.** Embed by copying `LibOrbitGlow-1.0/` and including `LibOrbitGlow-1.0.xml` from your TOC or XML, then
  `local lib = LibStub("LibOrbitGlow-1.0", true)`. Players install the standalone package only when an addon asks.
- **Call style.** `lib.Show(frame, type, options)` and `lib.Hide(frame, type, key)` reach the engine types `Classic`
  (the spell-activation flash and ant swirl), `Thin` (a thin swirling ant ring), `Thick` (a thick proc-loop ring) and
  `Medium` (the standard action-bar proc glow); `lib.Apply(frame, id, options)` and
  `lib.Remove(frame, id, keyOrOptions)` also resolve registered pack names, so a valid saved glow choice needs no
  branching; `lib.PreLoad(type, count)` warms engine pools. Registry, `Proc`, `StatusBar` and `Flipbook` are colon
  calls. The [runtime README](LibOrbitGlow-1.0/README.md) is the API reference: options, `Proc` phases, pack definition
  fields, status-bar contours and registration.
- **Packs.** A pack is an addon that calls `lib:RegisterGlow(name, def)` (and `lib:RegisterStatusBarGlow`) at load;
  hosts discover names through `lib:GetGlowList()` and `lib:GetStatusBarGlowList()` and group them by `source`. A
  baseline `blizzard` glow registers at load, so `Proc` works with no pack installed and resolves unknown `glow` names
  to it; `Apply`/`Show` and `Remove`/`Hide` raise for a name that is neither registered nor an engine type, so validate
  saved choices with `lib:IsGlowRegistered` or the engine list first.
- **Releases.** Source lives in Orbit-Libs; `release-glow.yml` publishes relevant `main` changes as
  `LibOrbitGlow-MAJOR.MINOR` GitHub releases and CurseForge project 1586462 uploads (versions continue from 1.8). The
  TOC lists Interface `120100, 120105, 16001` and game versions derive from it. Consumers pin the release commit with
  `path: LibOrbitGlow/LibOrbitGlow-1.0`; Orbit loads the two Lua files from its own `Libs.xml`.

## Gotchas
- LibStub shares one table between embedders and upgrades it when a higher revision loads: feature-probe
  (`if lib.StatusBar then`) rather than assume, and bump both module revisions together, because the status-bar module
  captures its embedding's asset path and an older copy can otherwise win.
- Always pass a specific `key` and pair every show with a hide using the same type and key. A live flipbook glow
  (`Thin`, `Thick`, `Medium`, non-engine packs and Classic's flipbook fallback) re-shown with unchanged options only
  re-tints and re-anchors; changing its art, grid, speed, blend, size, offsets, desaturation or `frameLevel` rebuilds
  it, as does `force = true` on a direct `Show` (`Proc` does not forward `force`). Native Classic re-shows, including
  one during the `Hide` fade-out, only re-tint and ignore `force`, `frameLevel` and `frequency`; those apply only when a
  new frame is built, and `Hide` releases the old one at once on a hidden host or during the fade-in, otherwise after
  its fade-out.
- Restricted AuraButtons: icon glows use shared frame/texture pools, and a pooled object reparented into a secure aura
  hierarchy becomes forbidden for every later consumer, so pass `owned = true` there to build from host-created objects,
  plus known `hostWidth`/`hostHeight` instead of reading the secret rect. `Proc` forwards all three to `path`, `resolve`
  and `atlas` packs but not to `engine` packs such as the built-in `classic`. Create glows inside `initializeFrame` and
  restyle only when aura access is permitted; being out of combat does not prove access. The library never inspects aura
  data, infers visibility or installs aura callbacks.
- Revision 13 resolves missing native icon atlases to the bundled tracer sheet, and Classic probes its native texture
  pair, using a separately keyed flipbook when they are missing or the host requires owned objects; `Hide`/`Remove` on
  Classic also releases that keyed fallback. Keep both fallbacks; Forever native acceptance is still pending. Public
  style names and saved choices stay stable, and feature presence is never used as an asset test.
- Layered, `path` and status-bar sheet art must be grayscale: it is tinted, not desaturated, and one status-bar sheet
  supplies both the tinted body and the additive core (`core = false` makes it one layer). A loop-only pack must declare
  `loopOnly` or `phases`, or the library tries `-start`/`-end` art. `SetTexture` fails silently on a missing file: use
  `lib:GetResolvedPaths(name, shape)` or `lib.DEBUG = true` for icon packs and `lib.StatusBar:Resolve` for status bars.
- Status-bar glows follow the host's whole rectangle, never its fill; contour matches are approximate baked outlines,
  and aspect stretching can make a rounded corner elliptical. Custom silhouettes need an explicit `shape` with matching
  pack art, because a mask file cannot describe the glow's path. Revision 11 removed the Pixel and Autocast engines:
  migrate saved selections to retained styles.
- `python tests/test_glows.py` (Lupa, Lua 5.1) covers registry/upgrade, bundled paths, atlas fallbacks, Classic
  ownership, resizing and cleanup; appearance, layering and aura restrictions need consuming displays in-game.

## Secrets
A curve result can itself be secret: pass it straight to a native alpha or colour sink. An accessible colour table may
hold secret channels, but a secret `ColorMixin` cannot be indexed; Classic does Lua alpha arithmetic and needs plain
colour values. Status-bar `Show` returns `nil` for secret or invalid dimensions or contours without touching an
existing glow.

## References
[LICENSE](LICENSE) (MIT), [runtime API reference](LibOrbitGlow-1.0/README.md), [CurseForge listing](CURSEFORGE.md),
[release workflow](../.github/workflows/README.md), [release tooling](../.scripts/README.md),
[repository](../README.md) and the workspace `orbit-libraries` skill.
