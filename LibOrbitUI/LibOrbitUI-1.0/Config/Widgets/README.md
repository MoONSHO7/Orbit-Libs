# Widgets

## Description
Ordinary configuration inputs, scrolling and value decorations.

## Purpose
Provide reusable controls with consistent layout and callback ownership for every consumer.

## Implementation
The `Config` constructors create or reuse buttons, sliders/range sliders, checkboxes, text inputs and dropdowns.
`ConfigDropdown.lua` supplies labels, option fonts and copied selection values to Pickers' flat Orbit menus; checks
appear only for multiple selections. Mixed selections claim no selected option until an explicit edit; option fonts
also appear on the closed control. `ConfigValueSwatch.lua` decorates
value columns with checkbox, numeric and color interactions. Checkbox rows accept `valueColor` beside their optional
value text; the label reserves the value column and pooled release expires the swatch. `singleColor=true` constrains
the editor independently of `curve=true`, so single-colour settings can retain their existing pin representation.
`ApplyValueColorSwatch` keeps the legacy singular field
unless given its optional fourth `slot` argument; indexed swatches reuse independent picker sessions and render curve
endpoints over a checkerboard through `ConfigPickerWidgets.lua`'s shared preview helper. `LayoutValueControls` anchors
visible accessories at the value column's right edge and grows left, preserving caller order; its return value is the
occupied width including a gap for the adjacent input. API 1.13's
`ApplyValueCheckboxes(frame, configs)` returns visible controls in declared order and reuses indexed `ValueCheckboxes`;
callers pass those controls to the same layout helper. Hidden and removed entries expire their callbacks. The singular
`ApplyValueCheckbox` remains compatible, with an optional fourth slot argument. Checkboxes retain compact native art
without cropping its transparent padding; each owns its tooltip and availability, combined with the parent row's gate.
`ConfigReadout.lua` supplies read-only label/value rows
and owner-action rows; passive sources belong in hover help. Compact consumers use those same constructors directly.
`ScrollBar.lua` owns shared scrolling. The parent layout supplies values and reclaims controls through its pool registry.

## Gotchas
- Recycled controls cannot retain writers or child interactions from their previous owner. Pool cleanup belongs to the
  layout that registered the control. `ReleaseValueControls` closes and invalidates every singular/indexed color session
  and checkbox binding, clears hover handlers and hides the private tooltip only when the released accessory owns it.
- Checkbox and numeric decorations remain usable when no optional color editor is installed.
- Range sliders poll the drag button because native drag start/stop events can fire unreliably during a held
  interaction.
- `ScrollBar:Attach` returns a bar with `SetScrollPosition` for immediate clamped seeks and `StopScrolling` for
  wheel/drag cancellation. Hiding the viewport cancels pending movement; range changes clamp the destination.
  Filtered/recycled content must seek through the bar to discard the previous target.

## References
[Config composition](../README.md), [Pickers](../Pickers/README.md), [Dialogs](../Dialogs/README.md).
