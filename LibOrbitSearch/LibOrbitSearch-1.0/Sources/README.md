# Native index sources

## Description
Ten Blizzard-data sources for the shared search index, independent of an Orbit host or UI library.

## Purpose
Translate native ownership and action data into common search entries while keeping unavailable subfeatures local to their source.

## Implementation
Every source registers at XML load, with optional namespaces/enums resolved later by `GetAvailability`. `NativeContract.lua` owns native function/event checks and bounded item-load requests; `IndexManager.lua` owns readiness, event demand and invalidation. A nil native collection is pending; a valid empty collection is ready. Product selection stays in each Search instance.

| Source | Native data and identity contract |
|---|---|
| Bags.lua | Native backpack/equipped-bag range plus an enabled keyring; deduplicate item IDs, preserve item-link actions, tolerate missing quest metadata and refresh asynchronous names. This does not create an Orbit Bags visual section. |
| Equipped.lua | Slot 1–19 includes ranged; include native INVSLOT_AMMO when defined. IDs are actual items, never fallback slot numbers. Item-load events recover uncached names. |
| Currencies.lua | CurrencyInfo.currencyID is stable identity. Expand headers forward and restore recorded indices in reverse, including duplicate/nested names. Native TokenFrame opening is offered only while that panel/function exists. |
| Macros.lua | Constants.MacroConsts supplies the account/character boundary. Macro index is session-local action identity; invalidation must retire displayed payloads before indices can refer to another macro. |
| Professions.lua | GetProfessions/GetProfessionInfo enumerate learned primary and secondary professions, including holes. Spellbook offsets supply actual action spells. Entry identity is skillLine:spellID; never cast a professionID as a spell. |
| Spellbook.lua | Player bank is required; pet bank and flyout methods are independent optional branches. Numeric spell IDs preserve rank/action identity. Spell/skill/talent/pet events refresh without requiring player specializations. |
| Mounts.lua | Unfiltered owned IDs and GetMountInfoByID provide favorites independently of displayed journal filters. Summon is optional. MountTypeTags uses explicit non-flying types, native steady-flight evidence and unlocked skyriding data; unknown types stay unclassified. |
| Pets.lua | Companion ownership remains usable without battle features. Only native canBattle entries receive battle-family keywords; summon attributes require the summon method and native PetIsSummonable. Unsummonable owned entries remain passive. |
| Heirlooms.lua | Catalog ownership is separate from carried item ownership. Only carried heirlooms receive item-use attributes; absent quality enums omit enrichment. This source does not manufacture a collection-creation action. |
| Toys.lua | Filtered count and filtered index remain paired. Ownership/use and optional favorite metadata are independent; item-load completion refreshes missing names. |

`ItemKeywords.lua` resolves optional binding enums at use and retains caller-localized synonyms. Unsupported enrichment never becomes a fabricated item or movement property.

## Gotchas
- API presence establishes the ability to query, not an unlocked gameplay feature. Consumers own conservative client policy and keep saved Retail choices; beta content/action verification remains required.
- Currency and profession identity changes intentionally leave old keys unmatched. Consumers must not guess old row-number or skill-line history into a new semantic identity.
- Item/spell hyperlinks and secure attributes are immutable snapshots from a build; the consumer checks current index generation before hardware action, drag or menu dispatch.

## References
[Engine contract](../README.md), library `.scripts/tests/client_contracts.py`; Blizzard live 12.1.0.69814 and forever 1.60.1.69913 generated docs, ContainerFrame, native ProfessionsBook and Classic PetCollection.
