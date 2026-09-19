# Widgets

## Description
Ordinary configuration inputs, scrolling and value decorations.

## Purpose
Provide reusable controls with consistent layout and callback ownership for every consumer.

## Implementation
The `Config` constructors create or reuse buttons, sliders/range sliders, checkboxes, text inputs and dropdowns. `ConfigDropdown.lua` supplies labels, option fonts and copied selection values to Pickers' flat Orbit menus; checks appear only for multiple selections. Option fonts also appear on the closed control. `ConfigValueSwatch.lua` decorates value columns with checkbox, numeric and color interactions; `ScrollBar.lua` owns shared scrolling. The parent layout supplies resolved options and reclaims controls through its pool registry.

## Gotchas
- Recycled controls cannot retain writers or child interactions from their previous owner. Pool cleanup belongs to the layout that registered the control.
- Checkbox and numeric decorations remain usable when no optional color editor is installed.
- Range sliders poll the drag button because native drag start/stop events can fire unreliably during a held interaction.
- `ScrollBar:Attach` returns a bar with `SetScrollPosition` for immediate clamped seeks and `StopScrolling` for wheel/drag cancellation. Hiding the viewport cancels pending movement; range changes clamp the destination. Filtered/recycled content must seek through the bar to discard the previous target.

## References
[Config composition](../README.md), [Pickers](../Pickers/README.md), [Dialogs](../Dialogs/README.md).
