# Rendering

## Description
Shared pixel, text, grid and authored-color primitives.

## Purpose
Keep basic rendering consistent across consumers while leaving theme, docking and unit-data policy with the caller.

## Implementation
`Pixel.lua` constructs independent pixel services and updates their scale from display events. `Text.lua` applies resolved fonts and shadows; `TextPosition.lua` composes anchors and places authored physical offsets or already-resolved logical coordinates. `GridMath.lua` maps authored dimensions to grid positions and extents.

`ColorCurve.lua` samples ordinary authored color pins through a caller-supplied class resolver. Orbit extends its sampler instance with native curves, unit data and theme policy.

## Gotchas
- `Text.ApplyFont` preserves text color and justification. `CreateFontSetter` instead preserves Portal's cached font-object defaults; these entry points have different ownership contracts.
- Physical offsets and logical coordinates are distinct inputs. Canvas callers use the logical placement sink after resolving their geometry.
- Color sampling requires ordinary editable pins; it does not implement secret unit-value curves.

## Secrets
Pixel helpers preserve opaque values for supported sinks, and font color restoration passes captured values directly back to the region. Consumers remain responsible for supplying ordinary geometry for grid calculations.

## References
[Library contracts](../README.md), [Core contexts](../Core/README.md), [Movement](../Movement/README.md).
