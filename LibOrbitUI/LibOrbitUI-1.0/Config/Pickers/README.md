# Pickers

## Description
Color, gradient, font and texture selection controls.

## Purpose
Share previews and selection interactions without embedding consumer catalog, theme or persistence policy.

## Implementation
`ConfigPickerControl.lua` supplies common preview helpers. Color and curve constructors pass edits to the provider installed by Config; font and texture constructors consume caller-supplied media services. `MediaMenu.lua` builds searchable catalog menus, accepting an optional preferred-item predicate instead of knowing Orbit's catalog.

## Gotchas
- Media services supply `list`, `fetch`, `isValid`, defaults and a localized None label. The library does not discover or persist consumer catalogs.
- Missing color editing support leaves previews visible with editing disabled; provider/session ownership prevents stale writes after a control is recycled.
- Consumers supply editable authored color records and class-color policy, including transparent-color previews.

## References
[Config providers and schema registration](../README.md), [Widgets](../Widgets/README.md), [Rendering](../../Rendering/README.md).
