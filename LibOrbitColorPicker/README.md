# LibOrbitColorPicker

## Description
The independently versioned color and gradient picker embedded by Orbit addons. Its runtime source, XML and checkerboard asset live in the Orbit-Libs repository.

## Purpose
Keep one editable source for the optional color editor. LibOrbitUI owns settings swatches and picker controls; this project owns the editor they open.

## Implementation
`LibOrbitColorPicker-1.0/` is the authored runtime directory. Orbit's `Orbit/Core/Libs/LibOrbitColorPicker-1.0` is a Windows directory junction to it; editing either path edits the same physical files. Consumer-owned `.scripts/fetch-libs.py` tools materialize pinned runtime files for clean-checkout validation and packaging while preserving development links.

Orbit and Status Widget embed the editor through development junctions to this source. Portal and Compass have no editable color settings and need neither this library nor LibStub. Addons adding color controls embed LibStub before the picker and supply the editor through LibOrbitUI's color provider. The picker is not a separate addon download and has no addon TOC.

`.pkgmeta` defines the runtime package and excludes documentation and development metadata. A path-filtered workflow releases relevant changes pushed to Orbit-Libs `main` under `LibOrbitColorPicker-MAJOR.MINOR` tags. Its ZIP contains only the Lua, XML, checkerboard and MIT license under `LibOrbitColorPicker-1.0/`; a SHA256 sidecar accompanies it. Other libraries retain separate release histories.

`.scripts/tests/embedded_assets.py` executes revision 11 from materialized Orbit, Status and renamed-host paths, both path separators and Latin/CJK locales. It checks checkerboard/license closure, duplicate-copy asset ownership, and the class-icon/plain-colour pin visual switch. This supports retaining the existing path contract; native rendering and editor-session verification remain in-game gates.

## Gotchas
- Orbit and Status Widget pin a full commit from a completed `LibOrbitColorPicker-*` [GitHub release](https://github.com/MoONSHO7/Orbit-Libs/releases) and select `path: LibOrbitColorPicker/LibOrbitColorPicker-1.0`. Verify publication and runtime assets before updating consumers. Release numbers are independent of the runtime API revision; the monorepo's first picker release is 1.2.
- API revision 11 accepts explicit tooltip, hide and class-color callbacks, returns a session ID from `Open`, and exposes its checkerboard texture. Class pins use Blizzard's native current-class atlas while ordinary pins retain their colour fill. It has no Orbit global dependency; callers without a tooltip receive a private picker tooltip.
- The main Lua file remains excluded from StyLua to preserve its existing formatting.
- [MIT licensed](LICENSE). Both the project and runtime directory carry the copyright and permission notice; retain that notice when redistributing the library or substantial portions of it.
- Preserve the runtime directory's exact `LibOrbitColorPicker-1.0` name; its asset lookup derives the checkerboard location from that path.
- A LibStub library is shared in one WoW session. Replacing an open editor cancels its old session, releases borrowed state before callbacks, and preserves any new session opened by a callback. Callbacks, persistence and integration policy remain caller-owned.

## References
[Runtime contract](LibOrbitColorPicker-1.0/README.md), [release workflow](../.github/workflows/README.md), [.pkgmeta](.pkgmeta), [license](LICENSE), and [LibOrbitUI](../LibOrbitUI/README.md).
