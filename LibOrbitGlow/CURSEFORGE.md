# LibOrbitGlow-1.0

A drop-in library for drawing animated **glows** on any WoW frame — action buttons, aura icons, cooldowns, nameplates, anything you can point it at.

It comes with **four icon glows** using Blizzard art and **two status bar glows** with bundled rectangular flipbooks. It can also render **Glow Packs** like [Orbit: Media](https://www.curseforge.com/wow/addons/orbit-pack-glows) — addons that register their own animated glow atlases for the library to play. Developers add this library to their addon to display and customise glows with a single call, and to consume glow atlases — their own or a third party's — for distribution to their users.

The icon glows are **Classic**, **Thin**, **Thick**, and **Medium**. **Tracer** and **Pin Neon** provide rectangular status bar outlines, with aspect-ratio and corner variants. Developers can register more status bar glows and receive host-owned textures for native display integration.

Requires only **LibStub**. Retail 12.1.0.

---

## Basic usage

Show and hide a built-in glow:

```lua
local lib = LibStub("LibOrbitGlow-1.0", true)
if not lib then return end

lib.Show(frame, "Medium", { key = "myGlow", color = { 0.2, 0.8, 1, 1 } })
-- ... later:
lib.Hide(frame, "Medium", "myGlow")
```

Drive a glow from a saved setting — `Apply` / `Remove` accept an engine type **or** any glow a pack registered, so you never branch on which:

```lua
local id = mySettings.glow   -- "Thin", "Medium", or a pack glow like "pinring"
lib.Apply(frame, id, { key = "proc", color = { 0.3, 0.8, 1, 1 } })
-- ... later:
lib.Remove(frame, id, "proc")
```

Populate a settings dropdown with everything available (built-ins plus installed packs):

```lua
for _, name in ipairs(lib:GetGlowList()) do
    -- name, and lib:GetGlowInfo(name).source for grouping by pack
end
```

---

## Documentation

Full API reference, the glow-pack format, engine options, combat / secret-value safety, and embedding & versioning notes are in the repository README:

**https://github.com/MoONSHO7/Orbit-Libs/tree/main/LibOrbitGlow**
