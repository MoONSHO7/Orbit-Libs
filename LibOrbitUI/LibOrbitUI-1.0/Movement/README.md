# Movement

## Description
Edit sessions and movement overlays for consumer-owned frames.

## Purpose
Share dragging and keyboard nudging while products retain position storage, edit eligibility and native-frame ownership.

## Implementation
`Geometry.lua` resolves positions and selection bounds. `EditSession.lua` owns activation, interruption and generation state. `Movement.lua` attaches overlays to declared surfaces, applies drag/nudge geometry through the consumer's pixel context, and commits positions through supplied callbacks.

## Gotchas
- Painted selection insets describe the overlay, while saved positions describe the target frame. Keep those coordinate spaces distinct across scales.
- Native Edit Mode does not grant automatic Save/Revert participation; the consumer owns persistence and interruption semantics.
- Releasing an overlay or cancelling its work does not restore protected/native ownership held by the product.

## References
[Library contracts](../README.md), [Rendering](../Rendering/README.md), [Addon movement composition](../Addon/README.md).
