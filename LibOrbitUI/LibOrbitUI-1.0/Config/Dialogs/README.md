# Dialogs

## Description
Shared window, settings-panel and prompt composition.

## Purpose
Keep window chrome and settings behavior consistent while consumers supply product tabs, values, actions and labels.

## Implementation
`DialogChrome.lua` retains housing window art when its atlas resolves, falling back to the supplied backdrop color otherwise. The user confirmed housing-basic-container on Forever; this is an asset guard, not a separate client design. `ConfigWindow.lua` creates the movable window and exposes position changes. `ConfigPanel.lua` owns content, controls and sizing from host callbacks/cache policy. `ConfigDialog.lua` composes these owners and registers settings windows with `SettingsCoordinator.lua`.

`UI.SettingsCoordinator:Register(dialog)` opts ordinary custom settings shells into Edit Mode exclusivity. All embeddings share the protocol-1 `LibOrbitUISettingsCoordinator` owner; its weak window registry and current claim contain no settings or consumer services. The newest open closes other registered windows and clears visible native selection through `securecallfunction` out of combat. A single native `Show` post-hook performs the reverse handoff. `EditMode.Enter` reconciles windows opened beforehand; arbitration continues while the active manager is temporarily hidden because its resume can omit Enter. Outside an active Edit Mode session, consumer visibility policy is unchanged.

`DialogLifecycle.lua` owns each shell's open/close lifetime, combat dismissal and EditSession subscription. `UI.DialogLifecycle:Create(context, dialog, options)` accepts `editModePolicy`: `auto` binds openings made during Edit Mode to that session; `required` allows only an active visible session; `manual` leaves Edit Mode exit/suspension to the host. Bound shells close on exit/hidden/locked interruption and never reopen automatically. All policies reject combat opens. `Config.CreateDialog` installs this owner as `dialog.lifecycle`; `spec.editModePolicy` selects policy, while `onClose`/`onRefresh` are callbacks on the lower-level lifecycle factory.

`ConfigDialog` captures a new view generation before every render and invalidates it before close cleanup. `Config.GuardCallback`/`BindDefinition` reject expired writes, actions and nested value/dropdown callbacks without changing caller schemas. `ConfigPanel:Release` invalidates deferred sizing and releases header, content, cached tabs, footer and layout prompts. Context destruction destroys registered lifecycles before shared services; `dialog.lifecycle:Destroy()` releases one shell's subscriptions and prevents reopening it.

`ConfigConfirmPopup.lua` installs lazy confirmation and input prompts through `Config.InstallPrompts(layout, {name, labels})`. `ConfigInputPopup.lua` adds text-transfer dialogs; consumers own validation, import and serialization. Product dialogs accept `spec.prompts`, `spec.color` and `spec.media`; closing releases these child interactions.

## Gotchas
- Prompt names must be unique across layouts; localized labels are `accept`, `cancel`, `import` and `close`, supplied as strings or providers.
- Prompt layout explicitly shows its accept button: `CreateButton` can return a hidden pooled control, and showing its parent does not restore that child's own visibility.
- `HidePrompts` clears fields, callbacks and focus. Closing or recycling invalidates the writer before another consumer can reuse the interaction.
- Tab IDs and localized labels must be unique. Conditional content rebuilds on open/tab refresh; panel sizing callbacks cannot outlive their view.
- Orbit supplies profile/theme bindings and `manual` lifecycle policy, retaining its accepted-session/suspension rules while using shared panel release. Its profile cache policy is not a shared default.
- Register settings shells only, not their prompts/pickers. Closing uses each shell's normal cleanup; a reentrant open supersedes the previous claim. Orbit's native replacement path hides Blizzard's editor before showing its shell to preserve the selected native system; ordinary library dialogs clear native selection so that same system can reopen.
- Feature disable is not context destruction: settings remain available to enable the feature again. A custom context without `UI.CreateContext` must explicitly destroy its lifecycles at shutdown. Reopening the same shell during its close cleanup is rejected.

## References
[Config composition](../README.md), [Addon settings](../../Addon/README.md), [Library contracts](../../README.md), and [Lua 5.1 regressions](../../../.scripts/README.md). Native handoffs were checked against Blizzard `live` 12.1.0.69814; mocks do not verify client taint, focus or rendering.
