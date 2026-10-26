# Tooltip artwork

## Description
The suite's left, middle and right mouse hint glyphs and its Shift, Control and Alt keycaps.

## Purpose
Ship identical artwork inside each independently installed addon through its embedded LibOrbitUI copy.

## Implementation
`../TooltipClick.lua` captures the embedding's library path at load and creates native texture markup for these TGAs.
The mouse files retain the original Orbit Core bytes. Keycaps share their outline, body and 128-pixel height on a
256-pixel canvas, drawn at 36x18 beside the 18x18 mouse; action text and localization remain caller-owned.

## Gotchas
Asset paths resolve inside the current embedding, never through a separately installed Orbit addon.
Keycap legends (`SHIFT`, `CTRL`, `ALT`, Barlow Condensed Bold) are baked into the art and ignore the client locale.

## References
[Rendering](../README.md), [library packaging](../../../README.md).
