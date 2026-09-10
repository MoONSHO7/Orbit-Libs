# Dialogs

## Description
Shared window, settings-panel and prompt composition.

## Purpose
Keep window chrome and settings behavior consistent while consumers supply product tabs, values, actions and labels.

## Implementation
`DialogChrome.lua` supplies housing window art. `ConfigWindow.lua` creates the common movable window and exposes position changes. `ConfigPanel.lua` owns the pinned header, content/footer, control rendering and sizing from host callbacks and an explicit cache policy. `ConfigDialog.lua` composes these owners from product tab descriptors, a setting reader/writer and optional footer actions.

`ConfigConfirmPopup.lua` installs lazy confirmation and input prompts through `Config.InstallPrompts(layout, {name, labels})`. `ConfigInputPopup.lua` adds text-transfer dialogs; consumers own validation, import and serialization. Product dialogs accept `spec.prompts`, `spec.color` and `spec.media`; closing releases these child interactions.

## Gotchas
- Prompt names must be unique across layouts; localized labels are `accept`, `cancel`, `import` and `close`, supplied as strings or providers.
- `HidePrompts` clears fields, callbacks and focus. Closing or recycling invalidates the writer before another consumer can reuse the interaction.
- Tab IDs and localized labels must be unique. Conditional content rebuilds on open/tab refresh; panel sizing callbacks cannot outlive their view.
- Orbit supplies profile/theme bindings to the same panel owner; its profile cache policy is not a shared default.

## References
[Config composition](../README.md), [Addon settings](../../Addon/README.md), [Library contracts](../../README.md).
