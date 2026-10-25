# Pickers

## Description
Color, gradient, font and texture selection controls.

## Purpose
Share previews and selection interactions without embedding consumer catalog, theme or persistence policy.

## Implementation
`ConfigPickerControl.lua` owns Orbit's flat dark control, compact arrow and open/hover border. API 1.17's
`Config.ApplyPickerValueWarning(layout, control, warning, value)` adds its value badge: one lazily created frame per
pooled control, left of the arrow, with the value text ending before it only while shown. It caches `visible(value)`;
`Config.RefreshPickerValueWarning(control)` reapplies that result after enable or mixed changes.
`MediaMenu.lua` owns the matching flat popup, catalog filtering, selection, positioning and dismissal. Its fixed search
header sits above a virtualized scroll child; the shared `ScrollBar.lua` owns wheel and drag movement. Consumers retain
the closed control's text, texture and animated swatch and supply pooled menu previews. Color/curve constructors use the
installed provider; font/texture constructors consume caller media services. `ConfigTexturePicker.lua` accepts API
1.12's `valueColors` schema list (the constructor's final optional argument), laid out in declared order after the
optional checkbox. Picker fields reserve the same value-column width; accessories anchor to its right edge and grow
left. `ConfigValueSwatch.lua` owns group spacing and accessory sizes; hosts use its `LayoutValueControls` for their own
compound rows and after changing accessory visibility.

## Gotchas
- Media services supply `list`, `fetch`, `isValid`, defaults and a localized None label. A consumer `isPreferredItem`
  predicate keeps matching choices alphabetized above a non-selectable divider; the library does not discover or persist
  consumer catalogs.
- API 1.15 accepts optional `media.fontLabel(name)` for closed font previews, menu labels and search; selection and
  callbacks retain the catalog name. Optional `media.firstFont` places that name before the ordinary font groups when
  it matches the search. Consumers without these fields retain raw names and the existing ordering.
- The value badge only takes mouse motion: clicks fall through to the picker, while hover shows the private tooltip
  (title, then wrapped text, `ANCHOR_RIGHT`) and keeps the picker's hover border. It hides while the picker is disabled
  or its row is mixed, and that tooltip closes only when the badge owns it. `Layout:ReleaseControl` clears the badge
  before re-enabling or unparenting, so reuse cannot show it or snap its inset at another scale.
- The badge uses `transmog-icon-warning-small`, which `Blizzard_TransmogTemplates` loads on Retail 12.1.5.70575 and
  Forever 1.60.1.70205. Do not substitute art without an observed Forever failure; native rendering is unverified.
- Missing color editing support leaves previews visible with editing disabled; provider/session ownership prevents stale
  writes after a control is recycled.
- Consumers supply editable authored color records and class-color policy, including transparent-color previews.
- `valueColors` replaces `valueColor` when supplied. Each entry uses the existing `initialValue`, `callback`, `curve`,
  `enabled`, `allowNone` and localized `tooltip` contract; curve entries retain gradient/checkerboard previews. Rebinding
  a texture row clears every former accessory before installing the current entries.
- Popups parent to `UIParent` to escape settings scroll clipping, anchor to their control and copy its effective scale
  on open/refresh. Screen clamping is the only outer constraint. `ConfigPickerControl` closes the detached popup on
  control hide, including inherited panel hides; never rely on popup parent visibility for cleanup.
- Keep menu ownership out of Blizzard's dropdown/description generator: the native menu version showed row reordering
  with animated previews. Scrolling preserves each overlapping row's identity and animation; only rows entering the
  viewport are acquired and painted. Catalog/filter changes rebuild offsets once, never on an idle update loop.
- `RefreshItems` preserves query/focus. Generation and item guards reject closed/replaced/recycled selections. Closing
  releases rows and cancels wheel/drag motion; filtering seeks through the shared scrollbar so an old target cannot move
  the new results.
- Escape uses Core's `EscapeClose` owner; combat opening or reopening cannot retain a consumed keyboard state. The
  search box keeps its own focused Escape dismissal and releases focus with the popup.
- `createRow`/`renderRow` supply content, never menu chrome. MediaMenu reserves the scaled check width plus a gap and forwards private
  tooltip hover handlers; single selections use only a background highlight. Closed previews belong to `frame.Control`
  and survive menu dismissal. `/reload` must verify animated art/glows, font/texture previews, search focus, scrolling
  and panel reuse; source simulations cannot certify native pixels or taint.

## References
[Config providers and schema registration](../README.md), [Widgets](../Widgets/README.md),
[Rendering](../../Rendering/README.md).
