# LibOrbitUI

## Description
An embedded UI library for Orbit and independently installed products. Each embedding exports `LibOrbitUI` on its addon's private namespace; it never creates or imitates the global Orbit object.

## Purpose
Maintain shared movement, configuration controls and rendering utilities once, while consumers own feature behavior, settings, localization and advanced editing services.

## Implementation
`LibOrbitUI-1.0.xml` is the public load entry point. It orders declarations across responsibility folders; folder order is not load order. Loading the XML does not construct a consumer or hydrate its settings.

| Module | Responsibility |
|---|---|
| [Core](Core/README.md) | Versioned namespace, callbacks, events, scheduling, storage, controllers and contexts. |
| [Rendering](Rendering/README.md) | Pixel units, text placement, grid math and authored color sampling. |
| [Movement](Movement/README.md) | Edit sessions, position geometry, selection overlays, dragging and nudging. |
| [Config](Config/README.md) | Presentation defaults, pooled layout, schema bindings and picker integration. |
| [Config/Widgets](Config/Widgets/README.md) | Ordinary inputs, scrolling and value-column decorations. |
| [Config/Pickers](Config/Pickers/README.md) | Color, gradient, font and texture selection. |
| [Config/Dialogs](Config/Dialogs/README.md) | Window chrome, panels, tabbed settings and prompts. |
| [Addon](Addon/README.md) | Product boot, movement and settings composition, plus an optional real-host bridge. |

Consumers enter through `CreateContext`, `Controller` or `Addon`, then call the same exported API regardless of source folder. Runtime state belongs to each consumer; differently pinned embeddings cannot replace another consumer's state. API 1.5 adds `Addon`'s optional `registerWidgets(layout)` hook for consumer-owned settings controls.

Orbit, Portal, Compass and Status Widget consume this source through development directory links. Packaging materializes regular files, preserves nested paths and includes `LICENSE`; module READMEs are development documentation.

## Gotchas
- Keep the XML entry point stable and preserve dependency order when moving files. Consumer tools must follow XML paths or scan recursively rather than assuming root-level Lua files.
- The library owns neither SavedVariables nor profile selection. Every edit commits through consumer callbacks; hosted products delegate lifecycle and persistence to the real Orbit owner.
- An ordinary Edit Mode overlay does not join Blizzard layout Save/Revert automatically. Consumers own persistence and interruption semantics.
- Advanced Canvas, anchor graphs and host profile transactions remain in Orbit. Portal's original host integration preserves legacy storage; it is not the completed standalone migration/export contract.
- Destroy a context only after its feature releases secure/native ownership. Cancelling work is not a substitute for restoration.

## Secrets
Pixel math and font color restoration pass opaque secret values through supported sinks. Consumers supply ordinary authored geometry and editable color records; these modules do not turn restricted frame queries into saved settings.

## References
[Project](../README.md), [license](LICENSE), [release checks](../../.scripts/README.md), and [LibOrbitColorPicker](../../LibOrbitColorPicker/README.md).
