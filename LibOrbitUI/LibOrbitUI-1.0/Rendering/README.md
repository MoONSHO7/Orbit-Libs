# Rendering

## Description
Shared pixel, text, grid and authored-color primitives.

## Purpose
Keep basic rendering consistent across consumers while leaving theme, docking and unit-data policy with the caller.

## Implementation
`Pixel.lua` constructs independent pixel services and updates their scale from display events. `Text.lua` applies
resolved fonts and shadows; `TextPosition.lua` composes anchors and places authored physical offsets or already-resolved
logical coordinates. `GridMath.lua` maps authored dimensions to grid positions and extents.

`Tooltip.lua` constructs private native tooltips with Orbit's default flat dark surface and pixel-scaled borders.
`TooltipClick.lua` captures this embedding's runtime path and builds mouse hints from `Assets/` artwork; callers own
localized action and modifier labels. The three original mouse TGAs moved byte-for-byte from Orbit Core.

`ColorCurve.lua` samples ordinary authored color pins through a caller-supplied class resolver. Orbit extends its
sampler instance with native curves, unit data and theme policy.

## Gotchas
- `Text.ApplyFont` preserves text color and justification. `CreateFontSetter` instead preserves Portal's cached
  font-object defaults; these entry points have different ownership contracts.
- A cold client refuses `SetFont` (returns false) until the file loads, then replays the refused request on a later
  frame over newer fonts. `ApplyFont` tracks refused regions and reapplies each one's latest request, keeping shadow,
  color and justification, until accepted on two frames or after ten seconds; `CreateFontSetter` takes ownership back.
  Writing a tracked region with raw `SetFont` can be overwritten during that window.
- Physical offsets and logical coordinates are distinct inputs. Canvas callers use the logical placement sink after
  resolving their geometry. Pixel rounding tolerates conversion noise at half-step boundaries; without it, centered
  odd-pixel components can alternate zero- and two-pixel nudges. Snap/EvenSnap ties round toward positive infinity;
  Multiple/ToCount ties round away from zero. Values outside that tolerance still follow nearest rounding.
- Color sampling requires ordinary editable pins; it does not implement secret unit-value curves.

## Secrets
Tooltip appearance checks native width and effective scale before changing native chrome or calculating borders.
Restricted geometry retains native chrome; no global tooltip setters or positioning methods are replaced.
Pixel helpers preserve opaque values for supported sinks, and font color restoration passes captured values directly
back to the region. Consumers remain responsible for supplying ordinary geometry for grid calculations.

## References
[Library contracts](../README.md), [Core contexts](../Core/README.md), [Movement](../Movement/README.md).
