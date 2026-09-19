# LibOrbitGlow-1.0

A drop-in World of Warcraft library for drawing animated **glows** on any frame — action buttons, aura icons, cooldowns, nameplates, anything you can point it at.

It comes with **four icon glows** using Blizzard art and **two status bar glows** with bundled rectangular flipbooks. It can also render **Glow Packs** like [Orbit: Media](https://www.curseforge.com/wow/addons/orbit-pack-glows) — addons that register their own animated glow atlases for the library to play. Developers add this library to their addon to display and customise glows with a single call, and to consume glow atlases (their own or a third party's) for distribution to their users.

> Targets retail **12.1.0**. Requires only **LibStub** — no other addon dependencies.

---

## How it works

LibOrbitGlow is split into an **engine** and a **registry**:

- The **engine** draws the four built-in icon glows and provides pooling, recolouring, throttling, and secret-value safety.
- The **registry** is an open list of glows that **Glow Packs** populate at load. The library owns no pack art itself — a pack calls `RegisterGlow` for each of its glows, and from then on every addon embedding LibOrbitGlow can play them.

The upshot: a host addon writes its glow code **once**, and any Glow Pack the user installs automatically appears in that addon's glow options with **zero extra code** on the host's side.

---

## The built-in glows

Four icon glows, each rendered from native Blizzard assets so they match the game's look:

| Glow | What it looks like |
|---|---|
| `Classic` | The classic spell-activation flash and ant swirl |
| `Thin` | A thin swirling ring of ants |
| `Thick` | A thick proc-loop ring |
| `Medium` | The standard action-bar proc glow |

Icon glows use shared frame/texture pools, or host-owned objects for restricted aura hierarchies. Status bar glows use host-owned textures with native, scriptless flipbook animations. Hosts own visibility and supply accessible configuration; see the restriction contract below.

## Glow Packs

Richer, hand-animated glows come from **packs** — small addons that register their atlases with this library. The flagship is [**Orbit: Media**](https://www.curseforge.com/wow/addons/orbit-pack-glows): a library of animated proc / pandemic glows. Install a pack and it shows up automatically anywhere LibOrbitGlow is used. Developers can ship their own packs too — see [Build a glow pack](#build-a-glow-pack).

---

## Installation

**Players:** install it from CurseForge when an addon requires it. It provides the glow engine and registries to consuming addons through LibStub.

**Developers (embedding):** drop the `LibOrbitGlow-1.0/` folder into your addon and include its manifest from your `.toc` or XML — it loads the icon engine and status bar module:

```xml
<Include file="Libs\LibOrbitGlow-1.0\LibOrbitGlow-1.0.xml"/>
```

Then consume it via LibStub:

```lua
local lib = LibStub("LibOrbitGlow-1.0", true)
if not lib then return end
```

---

## Usage

The library exposes a simplified facade that abstracts away the underlying animation groups, textures, and geometry engines. You only ask for a glow and pass an options table.

### Showing a glow

```lua
local lib = LibStub("LibOrbitGlow-1.0", true)
if not lib then return end

lib.Show(frame, "Medium", {
    key = "myComponentGlow",
    color = { 0.2, 0.8, 1, 1 },
    speed = 1.0
})
```

### Hiding a glow

Hide a glow using the exact same type and key you showed it with, so the library can gracefully stop the animation and recycle the frame back into the pool.

```lua
lib.Hide(frame, "Medium", "myComponentGlow")
```

### One call for any glow (recommended)

`lib.Show` / `lib.Hide` reach the built-in **engine** types directly. But if your addon stores a glow choice as a setting, that value might be an engine type (`"Medium"`) *or* the name of a glow a pack registered (`"pinring"`) — and you shouldn't have to branch on which. `lib.Apply` / `lib.Remove` resolve either:

```lua
local id = mySettings.glow   -- "Thin", "Medium", or any registered pack glow like "pinring"
lib.Apply(frame, id, { key = "proc", color = { 0.3, 0.8, 1, 1 } })
-- ... later:
lib.Remove(frame, id, "proc")

-- A continuous glow that stays until you Remove it (no intro; the outro still plays on Remove) -- add loop = true:
lib.Apply(frame, id, { key = "buff", color = { 1, 0.8, 0.2, 1 }, loop = true })
```

A registered name plays its full proc lifecycle (one-shot start, looping body, one-shot end on `Remove`); `loop = true` plays the loop continuously with no intro (call `Proc:Clear` instead of `Remove` for an instant cut). An engine type shows and hides directly. `Remove` accepts either a bare key or the same options table you passed to `Apply`. Use `Apply` / `Remove` everywhere you drive a glow from user choice.

> **Call style:** the top-level verbs are **dot**-called — `lib.Show`, `lib.Hide`, `lib.Apply`, `lib.Remove`, `lib.PreLoad`. The registry and the `Proc` / engine sub-namespaces are **colon** (method) calls — `lib:RegisterGlow(...)`, `lib.Proc:Start(...)`, `lib.StatusBar:Show(...)`.

### Combat and secret-value safety

A curve result can itself be secret. Pass it directly to a native alpha or colour sink; do not branch or do arithmetic on it. An accessible colour table may contain secret channels, but a secret ColorMixin cannot be indexed to call `GetRGBA`. Classic performs Lua alpha arithmetic and needs plain colour values.

Restricted AuraButtons require creation inside `initializeFrame`, followed by restyling only when aura access is permitted. Being out of combat does **not** prove an AuraButton is accessible. Callers must not invoke any glow method on an access-restricted host. Pass known layout dimensions instead of reading a secret rect. The library does not inspect aura data, infer visibility, or install aura callbacks.

```lua
parent:SetAlphaFromBoolean(secretBool, 1, 0)
```

---

## Status bar glows

`StatusBarGlows.lua` owns a separate registry and renderer for rectangular frame outlines. **Tracer** (`tracer`) and **Pin Neon** (`pinneon`) ship as baselines, with 2.5:1 and 4:1 sheets and square/soft/softer/round/chamfer variants. All textures live inside the library; Orbit is not a dependency. Consumers describe their outline with `contour`, or select an explicit pack `shape`. The library never reads, creates, replaces or removes the consumer's masks.

Chamfer sheets follow straight 45-degree cuts. `chamfer-small`, `chamfer`, and `chamfer-large` cut 6.25%, 12.5%, and 25% of the source content's shorter side. Rounded sheets provide `soft-small` (6.25%), `soft` (12.5%), `soft-large` (17.5%), `softer` (25%), `round` (35%), and `round-large` (50%) radii. Their registered geometry lets the library choose a sheet without consumers knowing these names.

```lua
local surfaces = lib.StatusBar:Show(bar, {
    glow = "tracer", key = "dispel", color = { 0.2, 0.6, 1, 1 },
    width = 160, height = 40,
    contour = { kind = "rounded", radius = 8 },
})
-- ... later, while the host is accessible:
lib.StatusBar:Hide(bar, "dispel")
```

`Show` creates textures directly on `bar`, returns a handle with `body`, optional `core`, and the resolved `shape`, and reuses them for the lifetime of that host/key. Recolouring and resizing do not restart unchanged animation; changing the sheet or duration does. `Hide` stops both animations and hides their textures without changing the host. Reuse a bounded set of keys.

### Contour selection

This API requires `lib.statusBarMinor >= 12`. Corner dimensions use the same logical units as the host width and height; consumers convert physical-pixel settings through their own scale system.

| `contour` | Requested outer outline |
|---|---|
| `{ kind = "square" }` | Square corners |
| `{ kind = "rounded", radius = 8 }` | Circular 8-unit corners |
| `{ kind = "chamfer", cut = 5 }` | Straight cuts extending 5 units along each adjoining edge |

Selection precedence is **explicit `shape` → `contour` → square**. An explicit shape overrides the contour entirely; an unavailable shape falls back to square. Omitting both always selects square, including when updating an existing glow. Zero radius/cut also selects square; oversized values clamp to half the host's shorter side.

The library first chooses the closest aspect ratio proportionally, then compares the rendered horizontal and vertical corner sizes against the request. Only registered geometry of the requested kind and the square fallback participate. Equal corner errors prefer the larger fraction, then the alphabetically first shape; equal aspect errors retain definition order. A pack with no contour metadata remains square unless an explicit shape is supplied.

These are baked outlines, so matches are approximate and aspect stretching can make a rounded corner elliptical. Custom silhouettes use an explicit `shape` and matching pack artwork. A mask file alone cannot describe the glow's path. Invalid or secret contour data returns `nil` before changing an existing glow; an explicit valid shape bypasses contour validation.

The glow follows the host's **whole rectangle**, not its filled percentage. For a health bar under other frame layers, mount on a caller-owned overlay at the desired frame level. `width` and `height` are known logical layout dimensions; when omitted the library measures the host. Secret, zero, or invalid dimensions return `nil` without changing an existing glow. `duration` optionally overrides the definition's loop duration. Unknown names fall back to Tracer. Only the StatusBar API resolves these names; icon `Apply`/`Proc` and `GetGlowList()` stay separate.

### Register your own status bar glow

```lua
lib:RegisterStatusBarGlow("my-pack.ribbon", {
    label = "Ribbon", source = "My Glow Pack",
    variants = {
        { ratio = 4, path = "Interface\\AddOns\\MyPack\\Textures\\ribbon-wide" },
        { ratio = 2.5, path = "Interface\\AddOns\\MyPack\\Textures\\ribbon-compact" },
    },
    shapes = { square = "", soft = "-soft", round = "-round" },
    contours = {
        soft = { kind = "rounded", radiusFraction = 0.125 },
        round = { kind = "rounded", radiusFraction = 0.35 },
    },
    rows = 6, cols = 5, frames = 30, duration = 1,
    overhang = 0.125, core = true, coreAlpha = 0.85,
    bodyBlend = "BLEND", coreBlend = "ADD",
})
```

Each sheet path resolves to `variant.path .. shapes[shape] .. ext`, with `ext = ".tga"` by default. `shapes` defaults to `{ square = "" }`; a square entry is required. A single-variant, single-shape pack works too. Supply `rows`, `cols` and `frames` for a different grid. Use grayscale RGBA sheets: the same art supplies a tinted body plus an additive core; `core = false` makes it one layer. `overhang` extends each edge by that fraction of the host dimension. Values above are the rendering defaults.

`contours` is optional metadata keyed by the pack's own shape names. Use `{ kind = "rounded", radiusFraction = ... }` or `{ kind = "chamfer", cutFraction = ... }`, with a finite fraction from 0 to 0.5 of the **source content's shorter side**, excluding halo overhang. A shape uses the same fraction across its aspect variants. Metadata must reference an existing shape; square geometry is implicit and cannot be redefined as rounded/chamfered. Geometry entries are copied at registration, and malformed entries reject the registration without replacing its previous definition. Unusual shapes can omit metadata and remain explicitly selectable.

Registration validates and copies the definition, returns `false` for malformed data, and replaces an existing name on success. Namespace names by pack to avoid collisions. Register during addon load; hosts can discover new definitions whenever they rebuild their options:

```lua
for _, name in ipairs(lib:GetStatusBarGlowList()) do
    local info = lib:GetStatusBarGlowInfo(name) -- label, source, variants, shapes, contours, rendering options
end
```

`IsStatusBarGlowRegistered(name)` checks availability; `UnregisterStatusBarGlow(name)` removes a definition (Tracer is retained as the fallback). Treat `GetStatusBarGlowInfo` as read-only; use registration to update it. `lib.statusBarRevision` increments on registry changes. `lib.StatusBar:Resolve(name, width, height, shape, contour)` returns the selected texture path, definition and resolved shape for custom previews/debugging. Pass `nil` as `shape` to select from a contour. Existing calls using the first four arguments retain their behavior.

### Injecting surfaces into a native display

The returned textures are real, host-owned regions. An addon can pass them to Blizzard's display sinks in an AuraButton initializer:

```lua
initializeFrame = function(button)
    local surfaces = lib.StatusBar:Show(button, {
        glow = "pinneon", width = 160, height = 40, key = "refresh",
    })
    button:AddPandemicRegion(surfaces.body)
    if surfaces.core then button:AddPandemicRegion(surfaces.core) end
end
```

Once a native sink owns visibility, let it drive those regions. Do not call `Show`/`Hide` to track aura state; any later presentation change must run in an accessible styling window. The native flipbooks use no Lua scripts, pooled objects, reparenting, or per-frame addon work.

---

## Proc lifecycle (registry glows)

Registered glows (the baselines and anything a pack adds) play through `lib.Proc`. You name the glow and the icon's corner shape; the library never decides the shape — your host maps its own border style to a shape the glow's `def.shapes` provides, defaulting to `"square"`.

| Method | Plays |
|---|---|
| `lib.Proc:Start(frame, o)` | one-shot **start**, then the looping **body** (skips straight to the loop if the glow has no start phase) |
| `lib.Proc:Stop(frame, o)` | one-shot **end**, then release (skips straight to release if the glow has no end phase) |
| `lib.Proc:Loop(frame, o)` | the **loop** only, forever — for persistent glows that never "expire" |
| `lib.Proc:Clear(frame, o)` | stop immediately, no end animation |

```lua
lib.Proc:Start(frame, { glow = "pinring", shape = "square", color = {0.3,0.8,1,1}, key = "proc" })
-- ... later, when the proc expires:
lib.Proc:Stop(frame, { glow = "pinring", shape = "square", key = "proc" })
```

`o` accepts `glow`, `shape`, `color`, `key`, `frameLevel`, `scale`, `padding`, `offsetScale` / `offsetX` / `offsetY` (nudge the glow off-centre), and per-phase durations `startDuration` (0.28), `loopDuration` (1.0), `endDuration` (0.20) seconds. Most callers should prefer the higher-level `lib.Apply` / `lib.Remove`, which route engine types **and** registered names.

**Registry API** — `lib:RegisterGlow(name, def)` (returns `false` and warns on a malformed def) · `lib:UnregisterGlow(name)` · `lib:IsGlowRegistered(name)` · `lib:GetGlowInfo(name)` · `lib:GetGlowList()` (sorted names — populate UI dropdowns from this; `GetGlowInfo(name).source` groups them by pack) · `lib:GetResolvedPaths(name [, shape])` (the texture paths a glow will try, for debugging).

A baseline `"blizzard"` glow is always registered, so `Proc` works with no pack installed, and any unknown glow name falls back to it.

---

## Build a glow pack

A pack is just an addon that calls `lib:RegisterGlow` for each of its glows during load — no dependency on any host, only on this library being present. The `def` table describes where the art lives and how to play it. **One** of `path` / `resolve` / `atlas` / `engine` is required; everything else is optional.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `path` | `string` | — | File-prefix for a flipbook sheet; resolves to `"<path>-<phase>[-<shape>]<layer><ext>"` |
| `resolve` | `function(phase, shape, layer)` | — | Full override of path resolution — use any naming you like; return `nil` for a phase/layer you don't ship |
| `atlas` | `string` | — | A Blizzard **atlas name** (single layer, `SetAtlas`) instead of files |
| `engine` | `string` | — | Delegate to a built-in engine (`"Classic"`, `"Thin"`, `"Thick"`, `"Medium"`) |
| `layered` | `boolean` | `false` | Draw a tinted **BLEND body** + a near-white **ADD core** (depth). `false` = one tinted layer |
| `core` | `boolean` | `true` | When `layered`, include the `-core` layer (set `false` for a body-only layered glow) |
| `blendMode` | `string` | `"ADD"` | Blend for a single-layer `path` / `atlas` def |
| `bodyBlend` / `coreBlend` | `string` | `"BLEND"` / `"ADD"` | Per-layer blend overrides for a `layered` def |
| `phases` | `table` | all | Set of phases the art provides, e.g. `{ loop = true }` |
| `loopOnly` | `boolean` | `false` | Shorthand for `phases = { loop = true }` |
| `shaped` | `boolean` | `true` | Include the `-<shape>` segment in the default name (set `false` if your files aren't shape-specific) |
| `ext` | `string` | `".tga"` | File extension for `path` resolution |
| `rows` / `cols` / `frames` | `number` | `6` / `5` / `30` | Flipbook grid (Blizzard's 30-frame, 5-wide × 6-tall layout) |
| `shapes` | `table` | `{ square = true }` | Corner shapes your art ships, e.g. `{ square = true, round = true }` |
| `scale` | `number` | engine default | Default size multiplier (path / atlas defs). For an `engine` def, sizing goes through `options` |
| `desaturated` | `boolean` | `true` | (`atlas` defs) desaturate before tinting |
| `options` | `table` | — | (`engine` defs) extra engine options (`scale`, `frequency`, …) |
| `source` | `string` | `"Unknown"` | Group label for consumer pickers — use your pack name |

```lua
local lib = LibStub("LibOrbitGlow-1.0", true)
if not lib then return end
local ROOT = "Interface\\AddOns\\MyGlowPack\\Textures\\"

-- 1. Full layered glow: start/loop/end x body+core, shape-suffixed.
lib:RegisterGlow("myproc", {
    layered = true, path = ROOT .. "myproc",
    shapes = { square = true }, source = "MyGlowPack",
})   -- expects myproc-loop-square.tga, myproc-loop-square-core.tga, myproc-start-square.tga, ...

-- 2. Single-file loop-only flipbook (one sheet, no start/end, no core, no shape suffix):
lib:RegisterGlow("spark", {
    path = ROOT .. "spark", loopOnly = true, shaped = false,
    rows = 4, cols = 4, frames = 16, blendMode = "ADD", source = "MyGlowPack",
})   -- expects exactly one file: spark-loop.tga

-- 3. Arbitrary naming via a resolver (return nil for phases you don't have):
lib:RegisterGlow("ribbon", {
    source = "MyGlowPack", rows = 5, cols = 6, frames = 30,
    resolve = function(phase, shape, layer)
        if phase ~= "loop" or layer ~= "" then return nil end
        return ROOT .. "fx\\ribbon_sheet.tga"
    end,
})
```

The flipbook grid (`rows` / `cols` / `frames`) describes how the sheet is sliced — one frame per cell over `loopDuration` seconds (`.tga`, any cell size; Orbit: Media uses 128×128 cells on a 640×768 sheet). **Layered / `path` art must be grayscale** — the layers are *tinted* by your `color` at draw time (not desaturated), so coloured source art multiplies muddily; the body takes your colour and the core is auto-brightened toward white for depth.

The host discovers your glows purely through `GetGlowList()` — no host-side code change is needed to surface a new pack. If a glow renders blank, call `lib:GetResolvedPaths(name [, shape])` to get the exact paths the lib is trying (WoW's `SetTexture` fails **silently** on a missing file), or set `lib.DEBUG = true` to print each path as it plays. A loop-only pack must declare `loopOnly = true` (or `phases`), or the lib will try to play `-start` / `-end` art it assumes exists.

### Lower-level flipbook

`lib.Flipbook:Show(frame, opts)` is the raw sink the registry feeds. It accepts `atlas` (a Blizzard atlas name, or a file path with `isTexture = true`), `rows` / `cols` / `frames`, `speed`, `blendMode`, `color`, `key`, plus `once = true` + `onFinished` for a single one-shot. Use it directly only if the registry / `Proc` model doesn't fit.

---

## Reference

### Global options

Passed as the 3rd argument to `lib.Show(frame, glowType, options)`, honoured across almost all engines.

| Field | Type | Description |
|---|---|---|
| `key` | `string` | Unique id used for tracking and hiding. Default: `"Default"` |
| `color` | `table` | `{ r, g, b, a }` array or an accessible `Color` object. Default: white |
| `frameLevel` | `number` | Relative frame level above the parent. Default: `8` |
| `desaturated` | `boolean` | Atlas engines (`Thin` / `Thick` / `Medium`) desaturate before tinting; pass `false` to keep native colours. Default: `true` |
| `force` | `boolean` | On a re-show of a live glow, rebuild even when options are unchanged (defeats the re-tint fast path). Honoured by all engines. Default: `false` |

### Flipbook engines (`Thin`, `Thick`, `Medium`)

- `scale` (number): multiplier applied to width and height. Default: `1.4`.

### Best practices

- Always provide a specific `key`. If you render multiple glows to the same frame (e.g. tracking several auras), omitting the key overwrites the shared `"Default"` bucket.
- Pair a single `lib.Show` with a single `lib.Hide` (same type + key) so frames return to the pool.
- `lib.PreLoad(glowType, count)` warms the shared pool against a hidden dummy frame so the first show in combat doesn't hitch. It amortises object **allocation** (per-size geometry still computes on the first real show). Engine types only — registered pack names are not poolable this way.
- Re-showing a live glow with the **same** options only re-tints (no teardown, no animation restart); changing any geometry / timing / atlas option, or passing `force = true`, rebuilds it. Driving a glow from a per-event handler is therefore cheap even without your own dedup.

---

## Embedding & versioning

Source lives in [Orbit-Libs](https://github.com/MoONSHO7/Orbit-Libs/tree/main/LibOrbitGlow). Relevant `main` changes publish independent `LibOrbitGlow-MAJOR.MINOR` GitHub releases and numeric CurseForge versions, continuing with 1.8 after the previous repository's 1.7. Consumers pin the completed release commit and `path: LibOrbitGlow/LibOrbitGlow-1.0`; runtime API revisions remain independent. Standalone packages include LibStub, while embedding addons supply it themselves. See the [shared release workflow](../.github/workflows/README.md).

Minor 11 removes the Pixel and Autocast engines and their registry entries. Hosts must migrate saved selections to retained styles. Load the XML manifest to include `StatusBarGlows.lua` and retain its adjacent `Textures` folder when embedding.

Minor 12 adds status-bar contour selection and optional pack geometry metadata. Older string-based shape registrations remain valid; unknown metadata-free shapes are never assigned inferred geometry. This does not change the icon `Apply`/`Proc` shape API.

Targets **retail 12.1.0**; the core engine uses `CreateMaskTexture` / `CreateFramePool`. LibStub shares one library table between embedders and upgrades it when a higher minor loads, so feature-probe rather than assume when you rely on a newer method — a co-installed older copy may not have it:

```lua
if lib.StatusBar then lib.StatusBar:Show(bar, opts) end
```

---

## License

MIT. See [LICENSE](LICENSE).

## Development checks

Revision 13 resolves missing native icon atlases to the bundled tracer flipbook. Classic probes its native texture pair and uses a separately keyed flipbook when those textures are unavailable or the host requires owned objects; stopping Classic releases that actual renderer. Public style names and saved choices stay stable. UI/gameplay feature presence is not used as an asset test.

Run `python tests/test_glows.py` with `lupa` (Lua 5.1). Tests cover registry/upgrade behavior, bundled paths, missing/present/late native atlases, Classic fallback ownership, resizing and cleanup. The tracer fallback is reused at icon aspect ratios; verify its real appearance, layering and aura restrictions through consuming displays/previews. Forever native acceptance remains pending.
