# Native index sources

## Description
Ten Blizzard-data sources for the shared search index, independent of an Orbit host or UI library.

## Purpose
Translate native ownership and action data into common search entries while keeping unavailable subfeatures local to
their source.

## Implementation
Every source registers at XML load, with optional namespaces/enums resolved later by `GetAvailability`.
`NativeContract.lua` owns native function/event checks and bounded item-load receipts; `IndexManager.lua` owns
readiness, event demand and invalidation. Bags, equipment, toys and heirlooms request only missing names/enrichment and
accept item completions only for IDs their current build awaits. A nil native collection is pending; a valid empty
collection is ready. Product selection stays in each Search instance.

| Source | Native data and identity contract |
|---|---|
| Bags.lua | Native backpack/equipped-bag range plus an enabled keyring; deduplicate item IDs, preserve item-link actions, tolerate missing quest metadata, count quest-log changes only for `player` as Blizzard's ContainerFrame filters, and refresh asynchronous names. This does not create an Orbit Bags visual section. |
| Equipped.lua | Slot 1–19 includes ranged; include native INVSLOT_AMMO when defined. IDs are actual items, never fallback slot numbers. Item-load events recover uncached names. |
| Currencies.lua | CurrencyInfo.currencyID is stable identity. Expand headers forward and restore recorded indices in reverse, including duplicate/nested names. Native TokenFrame opening is offered only while that panel/function exists. |
| Macros.lua | Constants.MacroConsts supplies the account/character boundary. Macro index is session-local action identity; invalidation must retire displayed payloads before indices can refer to another macro. |
| Professions.lua | GetProfessions/GetProfessionInfo enumerate learned primary and secondary professions, including holes. Spellbook offsets supply actual action spells. Entry identity is skillLine:spellID; never cast a professionID as a spell. |
| Spellbook.lua | Player bank is required; pet bank and flyout methods are independent optional branches. Numeric spell IDs preserve rank/action identity. Spell/skill/talent/pet events refresh without requiring player specializations; pet and specialization events count only for `player`, as PetFrame and EditModeManager register them. |
| Mounts.lua | Unfiltered owned IDs and GetMountInfoByID provide favorites independently of displayed journal filters. Summon is optional. MountTypeTags uses explicit non-flying types, native steady-flight evidence and unlocked skyriding data; unknown types stay unclassified. |
| Pets.lua | Companion ownership remains usable without battle features. Only native canBattle entries receive battle-family keywords; summon attributes require the summon method and native PetIsSummonable. Unsummonable owned entries remain passive. |
| Heirlooms.lua | Catalog ownership is separate from carried item ownership. Only carried heirlooms receive item-use attributes; absent quality enums omit enrichment. Item-load receipts recover missing catalog names and keyword data. This source does not manufacture a collection-creation action. |
| Toys.lua | Filtered count and filtered index remain paired. Ownership/use and optional favorite metadata are independent; item-load completion refreshes missing names. |

Item metadata and counts use `C_Item.GetItemInfo` and `C_Item.GetItemCount`; bag readiness requires both, equipment only
metadata. Heirloom catalog ownership stays available without them, but carried-item actions require the count method.
`ItemKeywords.lua` enriches through optional `C_Item.GetItemInfo` and binding enums, retaining caller-localized synonyms.
Its second return marks incomplete native metadata for the caller's load receipt; unavailable enrichment is omitted.

## Gotchas
- API presence establishes the ability to query, not an unlocked gameplay feature. Consumers own conservative client
  policy and keep saved Retail choices; beta content/action verification remains required.
- Currency and profession identity changes intentionally leave old keys unmatched. Consumers must not guess old
  row-number or skill-line history into a new semantic identity.
- Item/spell hyperlinks and secure attributes are immutable snapshots from a build; the consumer checks current index
  generation before hardware action, drag or menu dispatch.
- Retail 12.1.5 and current Forever removed the deprecated item globals; never use them as availability evidence or
  fallback calls. Native item metadata can still be uncached after the namespaced API is available.

## References
[Engine contract](../README.md), library `.scripts/tests/client_contracts.py`; Blizzard live 12.1.0.69933 and forever
1.60.1.69977 generated docs, ContainerFrame, PetFrame, EditModeManager, native ProfessionsBook and Classic
PetCollection. Item contracts were rechecked against Retail 12.1.5.70340 (`7b27d6845`) and Forever 1.60.1.70338
(`943764493`): generated ItemDocumentation and loaded `Blizzard_ObjectAPI/Mainline/Item.lua` use `C_Item` on both.
