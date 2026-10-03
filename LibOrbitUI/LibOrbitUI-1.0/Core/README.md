# Core

## Description
Consumer-local services and the versioned library namespace.

## Purpose
Give embedded products explicit ownership of callbacks, scheduled work, settings and lifecycle without depending on an
Orbit global or database.

## Implementation
`Bootstrap.lua` establishes the API. `Client.lua` exports an immutable `UI.Client` record before consumer code: family,
version, build, Interface and classifier evidence. The resolver recognizes Retail 12.x and Forever 1.60.x; the installed
Legacy addon corroborates Forever and conflicts with a Retail signature. Its absence at early load does not veto the
version signature. Unknown versions remain unknown; consumers own support policy and native readiness. `Callbacks.lua`
owns error boundaries; `Events.lua` and `Throttle.lua` provide consumer-local dispatch and update scheduling.
`Runtime.lua` owns cancellable work and deferred reconciliation. `EscapeClose.lua` gives addon-owned windows local
Escape handling without enrolling global names in Blizzard's taint-sensitive close registries.

`SettingsStore.lua` wraps an explicitly supplied plain data table, copying table settings and resolving named
collections. `Controller.lua` connects that store to one-time construction, repeatable activation, subscriptions and
teardown; an `alwaysEnabled` controller owns no `Enabled` setting and reports active policy directly. `Context.lua`
composes a consumer owner with pixel/runtime services, shared mouse hints and an owned or explicitly borrowed private
tooltip. Owned tooltips use Rendering's default Orbit appearance; borrowed tooltips keep the host's styling. Its
idempotent `Destroy` marks the context unavailable, destroys registered dialog lifecycles, then releases owned services;
borrowed pixel/tooltip objects retain their original owner.

## Gotchas
- Storage supports explicit false values and type unions. Malformed or newer-version stores are rejected without being
  overwritten; the consumer owns persistence.
- Failed controller construction requires reload. Teardown can be retried; consumers must release native/secure
  ownership before destroying their context.
- The optional `shouldApplyVisibility(controller)` predicate restricts visibility-event applies to product-owned state
  transitions. Without it, every subscribed visibility event applies.
- Context creation consumes Rendering's pixel API. The entry XML loads those declarations before consumers construct
  contexts; alphabetical folder loading is not supported.
- `EscapeClose` enables keyboard input once during frame construction. Its Escape path rejects combat, consumes only
  that key for one frame and restores propagation asynchronously; every other close path remains owned by the window's
  lifecycle.

## Secrets
Storage accepts ordinary editable data and rejects secret values. A context's private tooltip and rendering services
remain the supported sinks for opaque display data.

## References
[Library contracts](../README.md), [Rendering](../Rendering/README.md), [Addon composition](../Addon/README.md).
