# LibOrbitUI checks

## Description
Focused Lua 5.1 regressions for shared UI behavior.

## Purpose
Verify coordination across private library embeddings without requiring an Orbit host.

## Implementation
`python .scripts/tests/picker_menus.py` loads the shipped picker controls, virtualized menu, shared scrollbar, dropdown,
font and texture constructors. Frame-boundary simulations cover detached popup ancestry/scale/owner-hide cleanup, flat
Orbit styling, stable bounded rows, idle render counts, wheel/drag cancellation, pinned search focus, selection,
actions, private tooltips, stale callbacks and closed previews. Native dropdown creation is rejected.

`python .scripts/tests/chrome_assets.py` checks that native settings art is retained when the atlas resolves and that
the caller's backdrop color is used when it does not. A user screenshot confirms housing-basic-container on Forever;
other asset/runtime contracts remain separate checks.

Run `python .scripts/tests/edit_mode_settings.py` from the LibOrbitUI wrapper directory with Lupa installed. It loads
shipped coordinator, lifecycle, context, EditSession, schema, dialog and app-shell code through separate addon
namespaces. Mock frames/native selection cover indexed/cross-addon handoffs, reentrant opens, delayed native
availability, explicit exit policies, hidden-session cancellation, combat, context destruction, hosted and
always-enabled control suppression, absence of enable-setting reads/writes and expired callbacks after refresh/reopen.
Separate checks run real panel release and text-control cleanup to verify cached-tab/sizing invalidation and focus loss
without writes.

`python .scripts/tests/controller_settings.py` loads the real SettingsStore and Controller in Lua 5.1. It verifies
always-on controllers remove the Enabled declaration, report their fixed policy without a store read and reject later
writes, while ordinary controllers retain the default setting contract.

`python .scripts/tests/prompt_buttons.py` runs the real button factory, layout recycling and confirmation owner with
fresh and recycled buttons. It checks visible accept/cancel actions, callback replacement, single acceptance and
cancellation without a write.

`python .scripts/tests/control_states.py` exercises shipped schema, panel, pools and native-widget adapters. It covers
dynamic disabled/hidden state, deferred accessory/option rejection, unavailable pickers, readable reason/help, mixed
checkbox/slider/dropdown values, read-only effective values, source/scope hover help, multiple guarded inheritance actions,
footer actions and disabled-to-enabled reuse. Inline colour sources retain row height, clip long localized labels/source
within narrow rows, refresh without recreating inputs, and restore half-width/wrapping on hide and pooled reuse.
Texture-row cases cover two curve swatches with independent labels/editors, guarded writes, simulated non-overlap
geometry and dual-to-single-to-none pooled reuse, including rejection of callbacks from released picker sessions.
Checkbox groups cover independent values/tooltips, ordered spacing, parent/child availability, captured callback
expiry, native art retention and indexed/singular/empty/sparse pool transitions.
Checkbox-row swatches cover single-colour curve transport, value-text spacing, separate input, guarded writes and reuse.
The checkbox/slider templates, loaded MinimalSlider enable behavior and
affected native input/alpha APIs match Retail `09b9db7` (12.1.0.69933) and Forever
`e3ecc27` (1.60.1.70205); native focus, input and rendering still require both clients.

`python .scripts/tests/escape_close.py` loads the shipped API 1.9 owner. It verifies local Escape consumption, custom
close ownership, combat rejection, asynchronous propagation restore and the absence of taint-sensitive global close
registration anywhere in the runtime.

`python .scripts/tests/font_refusal.py` loads the shipped Text owner against a client that refuses cold `SetFont`
calls and replays them once the file loads. It checks the latest request wins, shadow/color/justification survive,
repairs settle or time out and font-object setters take ownership; native font loading still needs a cold game start.

`python .scripts/tests/pixel_rounding.py` checks the shipped Pixel owner across display/frame scales, centered odd/even
sizes, both coordinate signs, half-step ties and genuine subpixel offsets. Nudges must advance evenly and reverse
without drift; signed-count conventions and secret passthrough stay intact.

`python .scripts/tests/tooltips.py` checks private and borrowed tooltip ownership, secret geometry, pixel borders,
consumer-local asset paths, localized mouse hints and byte-identical relocation of the original mouse TGAs.

## Gotchas
- These simulations do not certify WoW focus, rendering, protected operations or taint. After `/reload`, switch between
  Compass's two editors, Portal, Status, Orbit and a Blizzard frame; compare direct settings with Edit Mode openings,
  exit/suspend, enter combat, reopen and check BugSack. Repeat without Orbit, including a picker or focused input during
  close.
- The runtime XML loads coordination/lifecycle before ConfigDialog. Orbit's `check-library-api.py` rejects packages
  missing its required API and owners; published consumer pins still require a verified library release.

## References
[Dialog contract](../LibOrbitUI-1.0/Config/Dialogs/README.md), [library project](../README.md).
