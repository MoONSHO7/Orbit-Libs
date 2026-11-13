# LibOrbitUI-1.15 (API 1.18, 2026-10-26)

- API 1.18 lets font rows carry ordered value checkboxes and colour-swatch lists; a wider accessory group narrows the
  picker instead of covering it.
- API 1.18 click hints take trailing Shift, Control and Alt modifier names and draw them as keycaps before the mouse
  glyph (`Hold` draws the keys alone), replacing `ControlScroll`/`ShiftRight`.

# LibOrbitUI-1.14 (API 1.17, 2026-10-25)

- API 1.17 dropdowns can show a small warning sign to the right of their box, where colour swatches sit, with a hover
  tooltip. Disabled, mixed and multiple-choice values never show it, and reused controls never keep it.

# LibOrbitUI-1.13 (API 1.16, 2026-10-24)

- API 1.16 gives sliders drag start/stop callbacks, silent reinitialization and cancellation of pending commits. A
  hidden, released or rebound slider no longer commits a drag or stepper edit later, and releasing a disabled slider
  or a different mouse button no longer commits.
- API 1.16 dividers default to the shared colour and one physical pixel, re-snapped when shown, on UI-scale or display
  changes and through `RefreshDividerPixels`; `CreateSectionDivider` places one below a section header.

# LibOrbitUI-1.12 (API 1.15, 2026-10-22)

- Equal range-slider endpoints can separate in either drag direction, including 0/0 and 100/100, without changing
  minimum gaps or callback ownership.
- Escape handling uses an isolated input frame that hides during combat, preventing first-use and interrupted-Escape
  keyboard lockups. Callers retain ownership of their window's other keyboard actions.
- Deferred font repair skips inaccessible regions and expires requests without touching them, preventing repeated
  forbidden-object errors after aura restrictions take effect.
- Media menus share the combat-safe Escape owner; movement releases keyboard capture immediately on combat entry.
- Label and tab overflow hover targets inherit click propagation without restricted setters during combat refreshes.

# LibOrbitUI-1.11 (API 1.15, 2026-10-14)

- API 1.15 lets consumers label and search font choices separately from their saved names and place a choice first.

# LibOrbitUI-1.10 (API 1.14, 2026-10-08)

- Fixed uneven portrait and component nudges caused by half-pixel rounding at fractional UI scales.
- API 1.14 adds colour swatches to checkbox value columns, retaining single-colour curve editing and pooled cleanup.
- Multi-select menus reserve the selection circle's full width plus spacing before the option text at every UI scale.
- API 1.13 adds ordered checkbox accessories for compound settings, with independent tooltips and values, shared
  availability guards, stable pooled controls and cleanup that expires previous callbacks.
