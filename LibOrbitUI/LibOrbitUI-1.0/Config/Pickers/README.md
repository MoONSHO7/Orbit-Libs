# Pickers

## Description
Color, gradient, font and texture selection controls.

## Purpose
Share previews and selection interactions without embedding consumer catalog, theme or persistence policy.

## Implementation
`ConfigPickerControl.lua` owns Orbit's flat dark control, compact arrow and open/hover border. `MediaMenu.lua` owns the matching flat popup, catalog filtering, selection, positioning and dismissal. Its fixed search header sits above a virtualized scroll child; the shared `ScrollBar.lua` owns wheel and drag movement. Consumers retain the closed control's text, texture and animated swatch and supply pooled menu previews. Color/curve constructors use the installed provider; font/texture constructors consume caller media services.

## Gotchas
- Media services supply `list`, `fetch`, `isValid`, defaults and a localized None label. The library does not discover or persist consumer catalogs.
- Missing color editing support leaves previews visible with editing disabled; provider/session ownership prevents stale writes after a control is recycled.
- Consumers supply editable authored color records and class-color policy, including transparent-color previews.
- Popups parent to `UIParent` to escape settings scroll clipping, anchor to their control and copy its effective scale on open/refresh. Screen clamping is the only outer constraint. `ConfigPickerControl` closes the detached popup on control hide, including inherited panel hides; never rely on popup parent visibility for cleanup.
- Keep menu ownership out of Blizzard's dropdown/description generator: the native menu version showed row reordering with animated previews. Scrolling preserves each overlapping row's identity and animation; only rows entering the viewport are acquired and painted. Catalog/filter changes rebuild offsets once, never on an idle update loop.
- `RefreshItems` preserves query/focus. Generation and item guards reject closed/replaced/recycled selections. Closing releases rows and cancels wheel/drag motion; filtering seeks through the shared scrollbar so an old target cannot move the new results.
- `createRow`/`renderRow` supply content, never menu chrome. MediaMenu owns multi-select checks and forwards private tooltip hover handlers; single selections use only a background highlight. Closed previews belong to `frame.Control` and survive menu dismissal. `/reload` must verify animated art/glows, font/texture previews, search focus, scrolling and panel reuse; source simulations cannot certify native pixels or taint.

## References
[Config providers and schema registration](../README.md), [Widgets](../Widgets/README.md), [Rendering](../../Rendering/README.md).
