# LibOrbitColorPicker-1.0

## Description
LibStub color picker with a saturation/brightness square, hue and opacity rails, a gradient bar, drag-and-drop pins, class-color and recent-color swatches, and a built-in guided tour. Class pins use the player's class icon; single-color and multi-color (gradient) modes are supported under the MIT license.

## Purpose
Gives every Orbit consumer one picker for both static colors and progress-mapped color curves (health bars, timer text), instead of Blizzard's single-color `ColorPickerFrame`.

## Implementation
A caller passes saved data into `lib:Open(options)`; the picker edits a pin list; the callback returns the result. Data flow: `initialData` (`{ pins = ... }` curve table or plain `{ r, g, b, a }`) → internal pin list → `C_CurveUtil.CreateColorCurve()` rebuilt on every pin change → `callback(result, wasCancelled)` fired once on close (Apply, clear, or cancel) — never during editing.

[Orbit-Libs](https://github.com/MoONSHO7/Orbit-Libs/tree/main/LibOrbitColorPicker) owns this directory. Orbit's embedded path links to this source during development; local staging copies regular files and includes `checkerboard.tga` and the MIT `LICENSE`. LibOrbitUI owns the settings widgets and binds their editing callbacks to this separate editor.

Colour entry is `ColorAreaMixin` (`lib.ui.colorSelect`), an Orbit-drawn replacement for Blizzard's `ColorSelect` — an SV square plus hue and opacity rails, each a mouse-tracking child frame. HSV is the widget's stored truth; RGB is derived. It exposes `SetColorRGBA` / `SetColorRGB` / `SetColorHSV` / `SetColorAlpha` / `GetColorRGB` / `GetColorAlpha`, and every one of them fires `OnColorChanged` — including alpha, which Blizzard's widget never reported.

| API | Does |
|---|---|
| `lib:Open(options)` | open with `initialData`, `forceSingleColor`, `hasDesaturation`, `recentColorsDb` (array ref enabling the 8-slot history row), `callback(result, wasCancelled)`, `onOpen(picker)` (fires after deferred init — consumers hook it for first-open tours), `anchor` (`{ frame, point, relativePoint, x, y }`; default fixed top-left of screen) |
| `lib:IsOpen()` | true while the picker frame is shown |
| `lib:GetCheckerboardTexture()` | bundled alpha-preview texture path |
| `lib:GetColorCurve()` | last built native ColorCurve, or nil |
| `lib:StartTour()` / `EndTour()` / `ToggleTour()` | 6-stop guided tour (also on the top-left info button) |

Callback result: apply with pins → `{ curve = <native ColorCurve>, pins = { { position = 0..1, color = {r,g,b,a}, type = "class"? } }, desaturated = bool? }` (`desaturated` only when `hasDesaturation` was set); clear all pins → `nil`; cancel (escape / close) → the pre-edit snapshot with `wasCancelled = true`.

Modes: `forceSingleColor = true` keeps exactly one pin (swatch drags replace it); multi-color allows unlimited pins — drag swatches onto the bar to add, drag handles to move, right-click to remove, arrow keys nudge (shift = fine).

## Gotchas
- Revision 11 accepts `tooltip`, `tooltipHide` and `classColor` in `Open(options)` and returns a session ID (or false if an old callback opened a replacement session). Without these options it uses a private tooltip and Blizzard's player class color; it never reads Orbit. Borrowed tooltip/context state is released before closing callbacks, and late hover/drag callbacks cannot revive it.
- **Persist `pins` (and `desaturated`), never `curve`** — `curve` is a transient native object rebuilt from pins on each open, a convenience for immediate use only. Reopen by passing the saved `{ pins = ... }` back as `initialData`.
- Branch on `wasCancelled` and discard the cancel payload; the picker has already rolled its own state back, including the recent-colors history (recents commit only on apply).
- Clearing all pins delivers `nil` — every consumer must supply its own default-color fallback.
- `type = "class"` pins resolve to the player's current class color and render the native current-class icon in their handle and drop preview; ordinary pins keep their colour fill. In single-color mode a manual edit (square, hue rail, hex) demotes the pin to a plain color so the picked value is honored verbatim; an opacity-only change does not demote (class pins render at full alpha). The demotion test is an RGB comparison against the pin, not "an event fired" — the opacity rail fires the same event.
- The colour area and the lone single-mode pin are two stores of one value. Anything that mutates the pin from outside the widget — swatch drops, class drops — must call `SyncColorSelectToPin` to push it back, or the two silently diverge and whichever the consumer reads last wins.
- HSV conversion is hand-rolled rather than `C_ColorUtil`: its documented achromatic contract returns hue `-1`, which would make the hue thumb jump to red every time the colour passes through grey or black. The widget retains the last real hue instead.
- `SetGradient` direction: `HORIZONTAL` is min→left, max→right; `VERTICAL` is min→**bottom**, max→top. The hue rail's six segments and the square's two fades both depend on this — flip one and the render inverts.
- Entering combat closes the picker as a cancel (`PLAYER_REGEN_DISABLED`) because `SetPropagateKeyboardInput` is protected in combat; a picker opened during combat runs keyboard-disabled until `PLAYER_REGEN_ENABLED`.
- The tour tooltip frame is lazy-built on first `StartTour()` — non-tour users pay zero cost at file load.
- All UI strings (labels, tooltips, tour) live in the `CP_LOCALE` table at the bottom of `LibOrbitColorPicker-1.0.lua`, resolved once at file load via `GetLocale()` — 9 languages (enUS/enGB, deDE, frFR, esES/esMX, ptBR, ruRU, koKR, zhCN, zhTW). Extend by adding keys to every locale block.
- `checkerboard.tga` (alpha preview) is located via `debugstack` path matching — renaming the library directory breaks it.

## References
- [Project](../README.md), [MIT license](LICENSE), and [LibOrbitUI](../../LibOrbitUI/README.md).
- Depends on `LibStub` only. Load with the silent flag: `LibStub("LibOrbitColorPicker-1.0", true)`.
- Plain pin sampling is shared through `LibOrbitUI.ColorCurve`; Orbit's configured instance is `OrbitEngine.ColorCurve`.
