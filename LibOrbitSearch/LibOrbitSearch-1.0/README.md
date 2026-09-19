# LibOrbitSearch-1.0

## Description
LibStub search engine with a shared source registry and per-consumer search instances. It ranks entries and merges live provider rows; it draws nothing.

## Purpose
An addon that needs search creates an instance, lists the kinds its search includes, and renders the results itself. Sources and providers register once per session and serve every instance that lists their kind.

## Implementation
Load order is the XML manifest: `LibOrbitSearch-1.0.lua` claims LibStub revision 3 (API/provider/index contract 1), `NativeContract.lua` defines native function/event checks, the engine files follow, `Sources/` registers the built-in index sources, and `Finalize.lua` adopts existing sessions and reconciles demand after the complete install.

| Registry (shared) | Does |
|---|---|
| `RegisterIndexSource(kind, source)` | `source:Build()` returns entries `{ kind, id, name, lowerName, icon, secure? onClick? passive? favorite? }`; optional `GetAvailability()` returns `ready`, `pending` or `unsupported` plus a reason; `events` dirty the kind |
| `GetIndexSourceState(kind)`, `NotifyIndexSourceChanged(kind)` | read state/reason or signal availability/data changes; a failed build is `failed`, a valid empty list is `ready` |
| `RegisterProvider(key, provider)` | live kind: `contract = lib.PROVIDER_CONTRACT`, `kind`, `IsAvailable`, `BeginSession`, `EndSession`, `Query`, `Present`, `Activate`; returns `ok, reason` |
| `NotifyProviderChanged(key)` | provider signals changed availability/data; active searches reconcile sessions and refresh without waiting for typing |
| `MarkDirty(kind)`, `InvalidateAll()` | consumer signals that a kind's data changed |
| `IsKindIncluded(kind)` | true while an enabled search lists and enables the kind |
| `RegisterCallback(owner, "SourcesChanged" \| "InclusionChanged", fn)` | registry or inclusion changes |
| `SetItemKeywordTerms({ ring, neck, cloak, reagent, warbound })`, `SetProfiler({ Begin, End })` | consumer-supplied localization and instrumentation |

`lib:NewSearch(config)` takes `kinds` rows `{ kind, label?, aliases?, priority?, provider?, noToken?, keywordOnly?, idSearch? }` in listing order, among them the sourceless `ids` kind, plus optional `GetKindLabel(row)`, `IsKindEnabled(row)`, `IsIDTypeEnabled("item"|"spell")`, `recents = { Load, Save }` and `onIndexUpdated()`. The instance offers `Enable`/`Disable`, `SetOpen`, `Query(text, { maxResults, fuzzy, hidePassives, scope })`, `Recents(limit)`, `Record(entry)`, `BeginSessions(onInvalidate)`/`EndSessions`, `Activate(entry)`, `IsEntryCurrent(entry)`, `GetEnabledKinds`, `GetKindLabel`, `EntryID` and `NotifySettingsChanged`. `lib.Fold` owns lowercase-and-diacritic matching. Consumers combine client policy with saved selection through their own predicates; disabling one instance never unregisters a shared source.

`IndexManager.lua` builds on the first query that includes a kind. Availability probes are cheap, side-effect-free source methods; omitted probes preserve external-source compatibility. A builder that discovers unavailable data may return `nil, "pending"|"unsupported", reason`; `{}` means a successful empty list. Missing/failed sources contribute no actionable entries. Dirty marks retire old entries immediately; open searches rebuild their union after a 0.5 s debounce. Per-kind revisions preserve notifications when a synchronous query rebuilds first, and reject results invalidated/replaced during a build. Closed searches rebuild on their next query.

Native events follow the union of enabled consumers' selected kinds and pass `C_EventUtils.IsEventValid`. Unsupported sources keep only valid `wakeEvents` (default ADDON_LOADED/PLAYER_ENTERING_WORLD); pending sources also keep their data events. Settings/source changes refresh demand. `IDLookup.lua` independently gates item/spell APIs and events, keeps valid addon-load/world-entry recovery events while selected, clears pending requests when demand ends, and retries lost requests on a later query after 30 seconds. Built-in item enrichment requests are bounded and deduplicated.

`ProviderSessions.lua` owns provider acquisition/release independently of `Merge.lua`'s query/presentation/ranking. `BeginSessions(callback)` starts a session group; registry changes, `NotifySettingsChanged`, `NotifyProviderChanged` and subsequent queries reconcile its enabled, available providers without restarting unchanged sessions. Each session captures its provider and generation; removal/replacement releases the original owner once. `EndSessions`, `SetOpen(false)` and `Disable` retire the group. `SetOpen(true)` only marks index-refresh interest; callers still start providers with `BeginSessions`.

`Matcher.lua` parses instance labels/aliases and scores exact > prefix > word start > substring > fuzzy, with tiers 6 (id exact) to 1. `Merge.lua` merges live rows by tier and priority band; provider rows retain owner identity so replacement cannot activate an old record through a new provider. `IDLookup.lua` resolves numeric queries into typed `ids` rows and refreshes open searches after asynchronous loads.

`SetProfiler` covers whole `Search/Query` and `Search/Recents` calls, existing `Search/Index` builds and `Search/Provider` queries, plus provider-keyed `.BeginSession`, `.EndSession` and `.Activate` boundaries (including failures). Spans are synchronous and nested; UI/host timing belongs to consumers.

## Gotchas
- One copy runs per session. A duplicate or older embedded copy stands down through `lib.__building`; a newer one replaces functions while keeping registry tables, and instances resolve methods through `lib._SearchMixin`, so existing searches upgrade with it. Keep the registry and instance contracts backward-compatible.
- Providers, sources and invalidation callbacks run under `pcall` and report through `geterrorhandler()`. A throwing source retires previous entries and waits for a data event/explicit invalidation before rebuilding. Failed `BeginSession` receives one `EndSession` to release partial resources and contributes no rows; retry waits for a new group, replacement or availability transition. Providers must tolerate cleanup after partial startup.
- Provider callbacks may close/reopen a search or unregister themselves. Reconciliation defers cleanup requested inside startup until that callback finishes, detaches a session before teardown, and ignores invalidation from closed/unready sessions. Availability changes without a query need `NotifyProviderChanged`; the library does not poll providers.
- A partial category word may differ from its label only in the last byte (`spells` → spellbook), so place names never become filters; a partial filter that finds nothing reruns unfiltered.
- Quest items are a tag on bag rows, not a kind: `Sources/Bags.lua` appends Blizzard's `BAG_FILTER_QUEST_ITEMS` word for slots `C_Container.GetContainerItemQuestInfo` marks, and follows the quest events Blizzard's own bags redraw on. A separate quest kind listed the same bag items twice.
- `Activate` returns the provider's outcome table (`close`, `replaceText`, `message`, `returnText`); applying it is the consumer's job.
- Built-in entries carry secure attributes for Blizzard action buttons. Consumers check `IsEntryCurrent` before dispatch/drag/menu actions and clear stale button attributes through their native action owner. The library cannot revoke attributes already copied into a consumer frame. `Activate` remains the provider action API.
- Recents storage is consumer-owned and should be qualified by client family. `Load` returns the mutable record table: Record updates it in place. Keep unclassified history dormant; currency list indices cannot be migrated to currency IDs without the original mapping. No saved client policy or UI dependency belongs in this shared library.

## References
[Project README](../README.md), [native sources](Sources/README.md), `.scripts/tests/search_engine.py` and `client_contracts.py`; Orbit `Core/Search/README.md` and `QoL/Spotlight/README.md` for the first consumer. Native and release verification remain separate gates.
