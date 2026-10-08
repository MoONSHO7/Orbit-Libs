# Config

## Description
Shared settings presentation and schema composition.

## Purpose
Let Orbit and standalone products render the same controls while supplying their own storage, labels, catalogs and
advanced editing policy.

## Implementation
`Config.lua` owns frozen presentation defaults and installs constructors on an isolated
`Layout:Create(context, constants)` owner. `Layout.lua` owns layout, pooling and callback release; `LayoutControls.lua`
registers ordinary schema types, and `LayoutTabs.lua` owns tab presentation. `ConfigSchema.lua` resolves values, commits
edits and binds callbacks to caller-supplied validity predicates. `CanInteract` combines visibility, `disabled`,
`isEnabled` and widget availability; deferred option/accessory/metadata callbacks inherit the parent gate. Standard
dialogs supply view generations; Orbit supplies its captured editing context. `disabledReason`, `sourceText` and
`scopeText` accept localized text or providers and join existing hover help, never extra passive rows.
Colour rows may explicitly set `inlineSource=true`; `LayoutControls` fits that source beside the label without wrapping
or changing row height. Readouts resolve an effective value without a setting writer. The
library owns presentation and input rejection; consumers own dependencies, source meaning and inheritance actions.
`LayoutTabs` accepts optional `context.tabScrollHint` text/provider for the overflow glyphs. Their hover targets preserve
wheel scrolling and click propagation; the private hint closes on leave, overflow disappearance and pooled release.

`ConfigPickerWidgets.lua` registers picker schemas, shared curve previews and cleanup. Texture schemas accept API
1.12's ordered `valueColors` list; API 1.13 exposes ordered `valueCheckboxes` for consumer-owned compound widgets.
API 1.14 accepts `valueColor` on checkbox rows; its optional `singleColor` restricts editing while `curve` retains pins.
Every nested callback inherits the parent's captured context and interaction gate.
`ConfigColorProvider.lua` binds optional
LibOrbitColorPicker editing to an explicit private tooltip, class resolver, recent-color accessor and tour callback.
Constructors live in [Widgets](Widgets/README.md) and [Pickers](Pickers/README.md); [Dialogs](Dialogs/README.md) compose
them into windows and prompts.

## Gotchas
- `Config.Install` requires a pixel context and private tooltip. Call `InitializeBaseWidgetTypes` before rendering; copy
  frozen defaults before deliberate overrides.
- Closed controls release callbacks and animations before reuse, including their availability/mixed-state decoration.
  Text inputs detach commit handlers before clearing focus; discarding a field never writes on focus loss. Panel release
  invalidates sizing work and clears every cached tab through the same control pools.
- Orbit supplies class-color policy, media catalogs/validation, checkerboard art, recent-color persistence and tours.
  Art/border/glow previews, group selection and profile caching remain host extensions.
- The default color provider requires LibOrbitColorPicker revision 10's `GetCheckerboardTexture` and session-returning
  `Open`. Without a compatible editor, previews remain visible and independent editing is disabled. LibStub is optional.

## References
[Library contracts](../README.md), [Core contexts](../Core/README.md),
[LibOrbitColorPicker](../../../LibOrbitColorPicker/README.md).
