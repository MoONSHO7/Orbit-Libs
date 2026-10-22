# Native index sources

## Description
Blizzard-data sources for the shared search index, independent of an Orbit host or UI library.

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
| Professions.lua | Capture the entire GetProfessions tuple, including holes and Forever's seventh position. Spellbook offsets supply actual action spells. Entry identity is skillLine:spellID; never cast a professionID as a spell. |
| Spellbook.lua | Native subnames distinguish ranks while spell IDs retain action identity; SPELL_TEXT_UPDATE refreshes late text. Pet commands use petaction:actionID plus book-slot/bank identity, with secure pet actions only for native pet-bar slots (Forever's Mkb set). Pet-bar changes retire copied slots. Off-bar commands open the pet book; they never become spell links or tracked spells. |
| Mounts.lua | Unfiltered owned IDs and GetMountInfoByID provide favorites independently of displayed journal filters. Summon is optional. MountTypeTags uses explicit non-flying types, native steady-flight evidence and unlocked skyriding data; unknown types stay unclassified. |
| Pets.lua | Species and every owned nickname remain aliases. One stable representative per species prefers summonability, then favorite, then GUID; its action/favorite fields describe that instance. Battle-family terms require native canBattle; unsummonable entries remain passive. Deletion retires rows; only CRITTER companion events invalidate pets. |
| Heirlooms.lua | Catalog ownership is separate from carried item ownership. Only carried heirlooms receive item-use attributes; absent quality enums omit enrichment. Item-load receipts recover missing catalog names and keyword data. This source does not manufacture a collection-creation action. |
| Toys.lua | Filtered count and index remain paired; search preserves native journal filters. Neither verified client offers an unfiltered toy enumerator, so hidden toys remain outside this source. Item-load completion refreshes missing names. |
| Skills.lua | Forever's native C_SkillInfo list supplies stable skill IDs, names, descriptions and ranks. Builds restore expanded headers and selection; explicit navigation resolves the current row and reveals it. Retail has no matching native enumeration contract. |
| EquipmentSets.lua | Native set IDs identify records; secure equipmentset actions require the native set name. Equipment events retire stale names/counts, and consumers can pick up the stable set ID. |
| Outfits.lua | Native unlock and owned records supply stable outfit IDs. Secure actions use playerFacingOutfitIndex, never outfitID; disabled outfits have no action. The gamepad-only spellbook tab does not gate native outfit enumeration. |
| Reputation.lua | Native faction IDs identify records and resolve navigation after header changes. Builds restore headers/selection; native standing and description supply terms without changing At War, watched or inactive state. |
| Talents.lua | The active combat config supplies visible tree:node:entry identities, spell text, native tree/group labels, ranks and passive terms. Tiered nodes distribute purchased ranks across entries in order; an explicit empty description override is complete. Caller-localized learned/unlearned terms describe each entry. Results open the native talent search; they neither allocate points nor cast spells. |
| Recipes.lua | Only the accessible current profession's native filtered list is indexed, with profession/category/state topics and optional schematic output/reagent/currency names. Data-source changes retire entries; activation rechecks profession/source identity and opens the recipe without crafting. Search never changes native recipe filters. |

Item metadata and counts use `C_Item.GetItemInfo` and `C_Item.GetItemCount`; bag readiness requires both, equipment only
metadata. Heirloom catalog ownership stays available without them, but carried-item actions require the count method.
`ItemKeywords.lua` enriches through optional `C_Item.GetItemInfo` and binding enums, retaining caller-localized synonyms.
Its second return marks incomplete native metadata for the caller's load receipt; unavailable enrichment is omitted.
Skills and reputation suppress only their own synchronous header-change invalidations during exact restoration;
other sources still receive those events. Failed enumeration restores native state before surfacing the error.
Item sources and Talents allow one full missing-data request sweep per source every 30 seconds; cold sweeps scale
linearly with the native catalogue, while later invalidations attach receipts without repeating requests in that window.
Request/receipt caches retain at most 256 IDs, so request deduplication across sources is best-effort after eviction.
New missing IDs discovered during the window wait for its next query-triggered sweep; no retry timer is created.
Item sources accept both native load-result and item-info completions; Talents accepts relevant successful load or
text-update events. Completed builds stop retrying, and disable/re-enable preserves the source request interval.
Missing names omit those entries; usable partial results stay ready, while an entirely unnamed collection stays
pending. Missing descriptions omit enrichment without hiding the entry. Recipe item names use the shared native
item-load receipts; missing schematics or optional name APIs omit enrichment. Recipe context is not an all-profession
catalog and may remain accessible after the native profession window closes.

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

Search expansion was compared with Retail 12.1.5.70448 (`b9be937`) and Forever 1.60.1.70450 (`172a387`), including
generated SpellBook, SkillInfo, Trait, TradeSkillUI, EquipmentManager, TransmogOutfitInfo and ReputationInfo contracts
and loaded PlayerSpells, Professions, Collections, UIPanels and SecureTemplates behavior. Source availability does not
certify in-game unlocks, actions or rendering.
