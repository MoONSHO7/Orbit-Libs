# LibOrbitUI checks

## Description
Focused Lua 5.1 regressions for shared UI behavior.

## Purpose
Verify coordination across private library embeddings without requiring an Orbit host.

## Implementation
Run each suite as `python .scripts/tests/<name>.py` from the LibOrbitUI wrapper directory with Lupa installed. Doubles
mirror real client APIs; only library-internal collaborators are stubbed.

`core_services.py` drives Callbacks, Events, Throttle, Runtime, SettingsStore, Controller and Client: results and named
error contexts, empty-name rejection, removal reports, bounded nested dispatch storage, positive finite intervals,
infinite/deep/oversized setting rejection, indexed change reports, increasing lifecycle generations, and
Retail/Forever/unknown classification from version and Legacy-addon signals. `controller_settings.py` verifies always-on
controllers own no Enabled declaration and reject later writes.

`addon_composition.py` runs Addon boot with a real Runtime: nothing applies before login readiness, rejected stores
never become ready, hosted products are ready without a local store, movement follows the controller's active state, and
restoration prefers saved, frame and record defaults while respecting drags, combat and anchor clearing.

`picker_menus.py` loads picker controls, virtualized menu, shared scrollbar, dropdown, font and texture constructors:
detached popup ancestry/scale/owner-hide cleanup, flat styling, bounded rows with one overscan row, idle render counts,
wheel targets, drag cancellation, pinned/explicit search, leading-divider removal, multi-select check insets and
deduplicated selections, invalid-media fallbacks, actions, private tooltips, stale callbacks and closed previews. The
real Escape owner runs through dismissal, combat reopening and first creation in combat; native dropdowns are rejected.

`chrome_assets.py` keeps native settings art when the atlas resolves and the caller's backdrop color otherwise; a user
screenshot confirms housing-basic-container on Forever. `prompt_buttons.py` runs the button factory, layout recycling
and confirmation owner with fresh and recycled buttons: visible actions, callback replacement, single acceptance and
cancellation without a write.

`edit_mode_settings.py` loads coordinator, lifecycle, context, EditSession, schema, dialog and app-shell code through
separate addon namespaces. Mock frames/native selection cover indexed/cross-addon handoffs, reentrant opens, delayed
native availability, exit policies, hidden-session cancellation, combat, context destruction, destroyed-shell reopening,
dialog spec rejection before window allocation, uncached renders, hosted/always-enabled control suppression, the Enabled
default and expired callbacks after refresh/reopen. Real panel release and text-control cleanup verify cached-tab/sizing
invalidation and focus loss without writes.

`movement_input.py` runs the real Movement, Geometry and EditSession owners through consumed nudges, combat entry on
either side of the lockdown query, key arrival before polling, regen and combat destruction, plus nearest-edge
orientation, increasing session generations, encounter blocking for sessions and resets, poll cadence, non-nesting
transitions, zero-size overlays and selection handoff within one context.

`control_states.py` exercises shipped schema, panel, pools and native-widget adapters: dynamic disabled/hidden state,
deferred accessory/option rejection, unavailable pickers, reason/help, mixed values, read-only effective values,
source/scope hover help, guarded inheritance/footer actions and disabled-to-enabled reuse. Inline colour sources keep
row height, clip in narrow rows, refresh in place and restore width policy on hide and reuse. Texture rows cover two
curve swatches with independent editors, guarded writes, non-overlap geometry and reuse that rejects released picker
sessions; checkbox groups and checkbox-row swatches cover ordering, availability, callback expiry, native art,
single-colour curves and pool transitions. Label and overflow hovers construct in combat through native click
propagation templates. The checkbox/slider templates, MinimalSlider enable behavior and input/alpha APIs match Retail
`09b9db7` (12.1.0.69933) and Forever `e3ecc27` (1.60.1.70205); native focus, input and rendering still need both
clients.

`config_widgets.py` reuses that harness for owner contracts: pooled button reparenting and text width, checkbox/edit-box
initial state, line-mode heights, no auto-focus, frozen read-only text, format-input hover, wrapped metadata, stacking,
enabled/unfaded release, guarded `onChange`, empty slider ranges, passive rows without scope hover, empty help,
refreshes without relayout, ordered tabs and signature rebuilds, prompt installation and transfer boxes, stale
colour/curve bindings after reuse, disabled swatches, empty curve results and coincident pins. A fresh runtime checks
frozen defaults, `Config.Install`, the optional LibStub colour picker and window movability/combat hiding.

`escape_close.py` verifies isolated input, first attachment in combat, consumed Escape across combat entry, inherited
hide/reopen, bounded restoration, custom close ownership, returned windows and non-frame rejection without a proxy.
Restricted setters reject combat, and no runtime joins Blizzard's global close registries.

`font_refusal.py` loads the Text owner against a client that refuses cold `SetFont` calls and replays them once the file
loads. The latest request wins, shadow/color/justification survive, and font-object setters own one shadowed object per
request. Both fixtures model post-initialization conditional access, forbiddance and secret access: blocked regions make
no native reads/writes, other repairs continue, recovery restarts settling and the original deadline removes requests
untouched. Native font loading and encounter access need a cold start and combat `/reload` verification.

`pixel_rounding.py` checks Pixel across display/frame scales, centered odd/even sizes, both signs, half-step ties,
subpixel offsets and the inclusive minimum frame scale: even reversible nudges, signed counts, secret passthrough and
display notification only on a new screen scale. `rendering_contracts.py` checks TextPosition anchors and authored
offsets, and that TextPosition, GridMath, Geometry and the ColorCurve sampler mixin are frozen.

`range_slider.py` drives overlapping endpoints, drag direction, stationary ticks, minimum gaps, release/hide, reuse and
the unconfigured two-endpoint default at multiple scales. Retail `b9be937` (12.1.5.70448) and Forever `e3ecc27`
(1.60.1.70205) agree on generated Input APIs, `InputUtil` scale conversion and `HybridScrollFrame` mouse polling; native
hit delivery needs WoW.

`slider_lifecycle.py` runs the slider and layout pool against a template double that keeps Blizzard's mouse/stepper
scripts: drag stop before release commit, disabled input, per-button press ownership, ancestor hide, public
cancellation, silent reinitialization, rebinding mid-press or from drag callbacks, stop-handler cancellation and pooled
release/reuse without stale callbacks or stacked hooks. The loaded MinimalSlider and EditMode slider templates match on
Retail `b9be937` (12.1.5.70448) and Forever `e3ecc27` (1.60.1.70205).

`section_dividers.py` loads the real Pixel service with the divider, tab and panel owners at three screen heights and
four frame scales. Default dividers stay one physical pixel in the shared colour after reparenting, public refreshes and
deferred display events; explicit arguments keep their logical height, section offsets hold, and tab scrolls reserve the
pixel they clip while omitted dividers reserve nothing.

`tooltips.py` checks private and borrowed tooltip ownership, name collisions that keep existing globals, contexts that
need a name and destroy owned services once, secret geometry, pixel borders, consumer-local asset paths, localized mouse
hints, ordered modifier keycaps and the original mouse TGAs' bytes.

`value_warning.py` renders dropdown schemas through the panel, pool and picker-control owners with the real Pixel
service, in both client fixtures at three frame scales: value-driven badge visibility, snapped placement right of an
unchanged box, grouping beside a value checkbox or swatch, the title/wrapped-body tooltip and owner-scoped cleanup,
clicks that never reach the menu, mixed/multi-select/disabled states without rerunning the predicate, combat creation,
pooled reuse and allocation-free refreshes. Retail `15881d5` (12.1.5.70575) and Forever `e3ecc27` (1.60.1.70205) share
the generated motion/click setters, load `transmog-icon-warning-small` and use the same motion-only
`EncounterTimelineEventFrameTemplate` tooltip pattern; native hit testing and art still require WoW.

## Gotchas
- These simulations do not certify WoW focus, rendering, protected operations or taint. After `/reload`, switch between
  Compass's two editors, Portal, Events, Orbit and a Blizzard frame; compare direct settings with Edit Mode openings,
  exit/suspend, enter combat, reopen and check BugSack. Repeat without Orbit, including a picker or focused input during
  close.
- The runtime XML loads coordination/lifecycle before ConfigDialog. Orbit's `check-library-api.py` rejects packages
  missing its required API and owners; published consumer pins still require a verified library release.
- `config_widgets.py` imports `control_states.py`'s harness; harness changes there affect both suites.

## References
[Dialog contract](../LibOrbitUI-1.0/Config/Dialogs/README.md), [library project](../README.md).
