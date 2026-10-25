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
or changing row height. Readouts resolve an effective value without a setting writer. API 1.17's dropdown
`valueWarning = { title, text, visible }` resolves both texts through `ResolveText`; `visible` is a boolean or
`function(value)`. `BindDefinition` passes the table through unguarded: its readers cannot write, and pooled release
drops them. The library owns presentation and input rejection; consumers own dependencies, source meaning and
inheritance actions.
API 1.16's `CreateTaperedDivider` defaults to the shared colour and one physical pixel, re-snapped on show, after
scale/display events and by `RefreshDividerPixels()`; explicit colour or logical height arguments are kept.
`CreateSectionDivider(parent, headerY)` spans `parent` 18 units below a header row. Panels and tab bars use these
defaults; a tab scroll's clip follows its divider when that pixel exceeds one unit.
`LayoutTabs` accepts optional `context.tabScrollHint` text/provider for the overflow glyphs. Their hover targets preserve
wheel scrolling and inherit click propagation from Blizzard's template at creation, including during combat. The
private hint closes on leave, overflow disappearance and pooled release.

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
- A direct `UIParent:SetScale`, including a scale below the `uiScale` CVar floor, fires no scale event; that caller runs
  `RefreshDividerPixels()`. Event refreshes wait one frame so the Pixel service has the new screen scale.
- Orbit supplies class-color policy, media catalogs/validation, checkerboard art, recent-color persistence and tours.
  Art/border/glow previews, group selection and profile caching remain host extensions.
- The default color provider requires LibOrbitColorPicker revision 10's `GetCheckerboardTexture` and session-returning
  `Open`. Without a compatible editor, previews remain visible and independent editing is disabled. LibStub is optional.

## References
[Library contracts](../README.md), [Core contexts](../Core/README.md),
[LibOrbitColorPicker](../../../LibOrbitColorPicker/README.md).
