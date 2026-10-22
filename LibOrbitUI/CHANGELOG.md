# Unreleased

- Equal range-slider endpoints can separate in either drag direction, including 0/0 and 100/100, without changing
  minimum gaps or callback ownership.
- Escape handling uses an isolated input frame that hides during combat, preventing first-use and interrupted-Escape
  keyboard lockups. Callers retain ownership of their window's other keyboard actions.
- Deferred font repair skips inaccessible regions and expires requests without touching them, preventing repeated
  forbidden-object errors after aura restrictions take effect.
- Media menus share the combat-safe Escape owner; movement releases keyboard capture immediately on combat entry.
- Label and tab overflow hover targets inherit click propagation without restricted setters during combat refreshes.

- API 1.15 lets consumers label and search font choices separately from their saved names and place a choice first.

- Fixed uneven portrait and component nudges caused by half-pixel rounding at fractional UI scales.

- API 1.14 adds colour swatches to checkbox value columns, retaining single-colour curve editing and pooled cleanup.

- Multi-select menus reserve the selection circle's full width plus spacing before the option text at every UI scale.

- API 1.13 adds ordered checkbox accessories for compound settings, with independent tooltips and values, shared
  availability guards, stable pooled controls and cleanup that expires previous callbacks.
