# Core

## Description
Consumer-local services and the versioned library namespace.

## Purpose
Give embedded products explicit ownership of callbacks, scheduled work, settings and lifecycle without depending on an Orbit global or database.

## Implementation
`Bootstrap.lua` establishes the API. `Callbacks.lua` owns error boundaries; `Events.lua` and `Throttle.lua` provide consumer-local dispatch and update scheduling. `Runtime.lua` owns cancellable work and deferred reconciliation.

`SettingsStore.lua` wraps an explicitly supplied plain data table, copying table settings and resolving named collections. `Controller.lua` connects that store to one-time construction, repeatable activation, subscriptions and teardown. `Context.lua` composes a consumer owner with pixel/runtime services and an owned or explicitly borrowed private tooltip.

## Gotchas
- Storage supports explicit false values and type unions. Malformed or newer-version stores are rejected without being overwritten; the consumer owns persistence.
- Failed controller construction requires reload. Teardown can be retried; consumers must release native/secure ownership before destroying their context.
- The optional `shouldApplyVisibility(controller)` predicate restricts visibility-event applies to product-owned state transitions. Without it, every subscribed visibility event applies.
- Context creation consumes Rendering's pixel API. The entry XML loads those declarations before consumers construct contexts; alphabetical folder loading is not supported.

## Secrets
Storage accepts ordinary editable data and rejects secret values. A context's private tooltip and rendering services remain the supported sinks for opaque display data.

## References
[Library contracts](../README.md), [Rendering](../Rendering/README.md), [Addon composition](../Addon/README.md).
