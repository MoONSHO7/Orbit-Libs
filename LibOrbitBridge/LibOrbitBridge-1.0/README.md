# LibOrbitBridge-1.0

## Description
LibStub library `LibOrbitBridge-1.0` (`lib.API` 1): third-party addon data, cleaned for Orbit consumers. Today it
bridges QuestieDB on Forever through `lib.Questie`.

## Purpose
Each consumer draws its own points, but every consumer must agree on which quests exist, which are available to this
character and where their objectives are done. The shared LibStub instance builds that once per session, whichever
addon asks first.

## Implementation
`LibOrbitBridge-1.0.lua` installs the instance: callbacks, consumer demand, per-frame drivers, the profiler hook, the
secret-safe readers (`Readable`, `Number`, `Text`) and the event frame. `Finalize.lua` ends the build.

Questie data flows through `Questie/`:
- `Retired.lua` is the curated list of quests no Forever giver offers (holiday, Season of Discovery-only, removed
  before 1.12, never released, ended Ahn'Qiraj War Effort, battleground turn-ins, event clutter, Forever rewards,
  duplicates); `Questie.IsRetired(questID)`.
- `Index.lua` admits the provider (`Questie.Provider()`: `LibQuestieDB.RequireContract(4)` and every read used) and
  builds one per-UiMap index on its own driver within 0.5 ms per frame: givers from each quest's `startedBy` (retired
  quests never enter), service NPCs, mailboxes and instance entrances; item-started quests are listed apart with their
  level. `Questie.Request(owner, db)` returns the index, or nil plus whether it is still building, and fires
  `QuestieIndexReady` once. `Questie.TrackingArt()` reads the client's minimap tracking names and icons.
- `Existence.lua` asks the game whether a quest exists (`C_QuestLog.RequestLoadQuestByID`, eight per tenth of a second,
  each once a session) and fires `QuestieExistenceChanged`, coalesced, as answers change a verdict.
- `Availability.lua` decides availability per collection: `Questie.Context(index, levelRange, excluded)` then
  `IsAvailable`, `Level`, `InRange` and `Serves` (faction). `excluded(questID)` carries a consumer's removed quests.
- `Objectives.lua` turns a quest's row into a plan in the client's objective order and clusters where each part is
  done on a map. `Questie.Prepare(owner, index, questID, mapID, start)` queues it on its own driver;
  `Places`, `Plan`, `Aligned` and `Locates` read the cache; `QuestiePlacesFound` fires once a drained queue placed one.
- `Log.lua` snapshots the quest log (`Questie.ReadLog(db)`) and coalesces its bursts, firing `QuestieLogChanged` only
  when the log or a pin changed.

Consumers register callbacks with `lib.RegisterCallback(owner, event, fn)` and give up background work with
`lib.Release(owner)`; any `Request` or `Prepare` registers demand again.

## Gotchas
- Availability is ours, not QuestieDB's: completion, log, level, race and class masks, prerequisites (a single
  prerequisite stands in for a group; a group member also counts once a quest exclusive to it was done), exclusive and
  breadcrumb links, parent and chain quests, skills, spells, reputation and the consumer's Quest Level Range. Holiday
  sort categories and Blizzard's retired title markers stay hidden, and a quest shows only once the game confirms it.
  Denials count only once some quest was confirmed: a client that confirms nothing within five seconds hides none.
- The curated list is evidence-only: add a quest with its source in the `develop/` record, never by guess. Questie's
  own blacklist is GPL and is never copied; it serves only as a cross-check.
- Race masks exceed 32 bits; `Questie.HasBit` uses arithmetic, never the `bit` library.
- QuestieDB's area-to-UiMap table is Lua source run under an empty environment in one protected call. A failing build
  step stops the driver for the session and reports once; a quest whose plan fails is dropped for that map.
- Accept, turn-in, abandon, level-up and world entry only mark the log stale: consumers that redraw on them hear those
  events themselves. After 90 s without a read, bursts stop reading the log.
- A driver runs only while some owner demands it; `Release` from every owner pauses unfinished builds, which resume
  on the next request. The profiler hook is one per instance; the last consumer to set it wins.
- Reading every NPC's flags and object's name fills QuestieDB's per-entity cache for the session.

## Secrets
Quest-log, map, reputation, skill and unit reads pass `Readable`, `Number` or `Text` (`issecretvalue`) before any
comparison or arithmetic. QuestieDB's tables are addon data and are only shape-checked.

## References
`../README.md`; Orbit-Compass `Core/Integrations/QuestieDB/README.md` (its consumer); QuestieDB `docs/api.md` (contract
4) and `Types/*.t.lua`; Blizzard generated `QuestLogDocumentation.lua` on Forever and Retail.
