# Tooltip artwork

## Description
The suite's left, middle and right mouse hint glyphs.

## Purpose
Ship identical artwork inside each independently installed addon through its embedded LibOrbitUI copy.

## Implementation
`../TooltipClick.lua` captures the embedding's library path at load and creates native texture markup for these TGAs.
The files retain the original Orbit Core bytes; action text and localization remain caller-owned.

## Gotchas
Asset paths resolve inside the current embedding, never through a separately installed Orbit addon.

## References
[Rendering](../README.md), [library packaging](../../../README.md).
