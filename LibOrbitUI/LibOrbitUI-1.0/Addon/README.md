# Addon

## Description
Product boot and settings/movement composition for independently installed addons.

## Purpose
Connect consumer-owned persistence and feature frames to shared controllers and UI, optionally delegating lifecycle to a real Orbit host.

## Implementation
`Addon.lua` composes boot from SavedVariable reader/writer callbacks and an optional host bridge. `AddonMovement.lua` attaches declared surfaces to shared Edit Mode overlays. `AddonSettings.lua` opens the common tabbed dialog from product descriptors, using `settingsTitles[index]` when supplied and the product title otherwise. Its optional `registerWidgets(layout)` callback runs once per dialog after base widget registration; the consumer owns custom control behavior and registers it on that dialog's isolated layout.

## Gotchas
- Hosted products delegate lifecycle and persistence to the real Orbit owner. This layer does not create an imitation global host.
- A surface with its own redraw callback can set `applyOnEditChanged = false` to avoid a full settings apply.
- Settings refresh on native Edit Mode entry/exit; the entry shortcut is visible only outside Edit Mode.
- Consumers own frame restoration and persistence semantics, including position changes and interrupted editing.

## References
[Core controllers](../Core/README.md), [Movement](../Movement/README.md), [Config dialogs](../Config/Dialogs/README.md), [Library contracts](../README.md).
