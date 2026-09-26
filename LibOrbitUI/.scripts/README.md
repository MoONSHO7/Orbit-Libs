# LibOrbitUI checks

## Description
Focused Lua 5.1 regressions for shared UI behavior.

## Purpose
Verify coordination across private library embeddings without requiring an Orbit host.

## Implementation
`python .scripts/tests/picker_menus.py` loads the shipped picker controls, virtualized menu, shared scrollbar, dropdown, font and texture constructors. Frame-boundary simulations cover detached popup ancestry/scale/owner-hide cleanup, flat Orbit styling, stable bounded rows, idle render counts, wheel/drag cancellation, pinned search focus, selection, actions, private tooltips, stale callbacks and closed previews. Native dropdown creation is rejected.

`python .scripts/tests/chrome_assets.py` checks that native settings art is retained when the atlas resolves and that the caller's backdrop color is used when it does not. A user screenshot confirms housing-basic-container on Forever; other asset/runtime contracts remain separate checks.

Run `python .scripts/tests/edit_mode_settings.py` from the LibOrbitUI wrapper directory with Lupa installed. It loads shipped coordinator, lifecycle, context, EditSession, schema, dialog and app-shell code through separate addon namespaces. Mock frames/native selection cover indexed/cross-addon handoffs, reentrant opens, delayed native availability, explicit exit policies, hidden-session cancellation, combat, context destruction, hosted and always-enabled control suppression, absence of enable-setting reads/writes and expired callbacks after refresh/reopen. Separate checks run real panel release and text-control cleanup to verify cached-tab/sizing invalidation and focus loss without writes.

`python .scripts/tests/controller_settings.py` loads the real SettingsStore and Controller in Lua 5.1. It verifies always-on controllers remove the Enabled declaration, report their fixed policy without a store read and reject later writes, while ordinary controllers retain the default setting contract.

`python .scripts/tests/prompt_buttons.py` runs the real button factory, layout recycling and confirmation owner with fresh and recycled buttons. It checks visible accept/cancel actions, callback replacement, single acceptance and cancellation without a write.

## Gotchas
- These simulations do not certify WoW focus, rendering, protected operations or taint. After `/reload`, switch between Compass's two editors, Portal, Status, Orbit and a Blizzard frame; compare direct settings with Edit Mode openings, exit/suspend, enter combat, reopen and check BugSack. Repeat without Orbit, including a picker or focused input during close.
- The runtime XML loads coordination/lifecycle before ConfigDialog. Orbit's `check-library-api.py` rejects packages missing API 1.8 or its required owners; published consumer pins still require a verified library release.

## References
[Dialog contract](../LibOrbitUI-1.0/Config/Dialogs/README.md), [library project](../README.md).
