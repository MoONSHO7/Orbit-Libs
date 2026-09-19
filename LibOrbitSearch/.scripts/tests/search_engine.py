"""Check LibOrbitSearch's engine: registry, index builds, matching, provider merge, recents and copy upgrades."""

import re
from pathlib import Path

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitSearch-1.0"
MANIFEST = RUNTIME / "LibOrbitSearch-1.0.xml"
HARNESS = r"""
mock = { now = 1700000000, errors = {}, timers = {}, frames = {}, spellNames = {} }
table.freeze = table.freeze or function(value) return value end
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
function time() return mock.now end
function geterrorhandler() return function(message) table.insert(mock.errors, tostring(message)) end end
C_EventUtils = { IsEventValid = function(event) return event ~= "INVALID_EVENT" end }
function CreateFrame()
    local frame = { events = {} }
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:UnregisterAllEvents() wipe(self.events) end
    function frame:SetScript(_, handler) self.handler = handler end
    table.insert(mock.frames, frame)
    return frame
end
function FireEvent(event, ...)
    for _, frame in ipairs(mock.frames) do
        if frame.events[event] and frame.handler then frame.handler(frame, event, ...) end
    end
end
C_Timer = {
    NewTimer = function(_, callback)
        local timer = { callback = callback }
        function timer:Cancel() self.cancelled = true end
        table.insert(mock.timers, timer)
        return timer
    end,
}
function FlushTimers()
    local timers = mock.timers
    mock.timers = {}
    for _, timer in ipairs(timers) do if not timer.cancelled then timer.callback() end end
end
C_Spell = {
    GetSpellName = function(id) return mock.spellNames[id] end,
    GetSpellTexture = function() return 1 end,
    IsSpellDataCached = function(id) return mock.spellNames[id] ~= nil end,
    RequestLoadSpellData = function(id) mock.requestedSpell = id end,
}
mock.itemNames = {}
C_Item = {
    GetItemNameByID = function(id) return mock.itemNames[id] end,
    GetItemIconByID = function() return nil end,
    GetItemQualityByID = function() return nil end,
    IsItemDataCachedByID = function(id) return mock.itemNames[id] ~= nil end,
    RequestLoadItemDataByID = function(id) mock.requestedItem = id end,
}
local libs, minors = {}, {}
LibStub = setmetatable({
    NewLibrary = function(_, major, minor)
        if minors[major] and minors[major] >= minor then return nil end
        libs[major] = libs[major] or {}
        minors[major] = minor
        return libs[major], minors[major]
    end,
}, { __call = function(_, major, silent)
    if not libs[major] and not silent then error("no library " .. major) end
    return libs[major], minors[major]
end })
LoadSource = function(source, name)
    assert(loadstring(source, "@" .. name))()
end
"""
SETUP = r"""
lib = LibStub("LibOrbitSearch-1.0")
KINDS = {
    { kind = "bags", label = "Bags", priority = 11, idSearch = true },
    { kind = "equipped", label = "Equipped", priority = 12, idSearch = true },
    { kind = "spellbook", label = "Spellbook", priority = 9, idSearch = true },
    { kind = "toys", label = "Toys", priority = 7, idSearch = true },
    { kind = "mounts", label = "Mounts", priority = 6, idSearch = true },
    { kind = "pets", label = "Pets", priority = 5, idSearch = true },
    { kind = "professions", label = "Professions", priority = 8, idSearch = true },
    { kind = "currencies", label = "Currencies", priority = 2 },
    { kind = "chattargets", label = "Chat Targets", provider = true, noToken = true },
    { kind = "locations", label = "Locations", aliases = { "location" }, priority = 3, provider = true },
    { kind = "macros", label = "Macros", priority = 13 },
    { kind = "help", label = "Help", aliases = { "orbit" }, priority = 1 },
    { kind = "ids", label = "Spell and Item IDs", noToken = true },
}
mock.disabled = {}
mock.store = nil
search = lib:NewSearch({
    kinds = KINDS,
    IsKindEnabled = function(row) return not mock.disabled[row.kind] end,
    recents = { Load = function() return mock.store end, Save = function(value) mock.store = value end },
    onIndexUpdated = function() mock.indexUpdated = (mock.indexUpdated or 0) + 1 end,
})
search:Enable()

function Entry(kind, name, id)
    return { kind = kind, name = name, lowerName = lib.Fold(name), id = id or name }
end

mock.entries = {}
mock.builds = {}
function IndexSource(kind, events)
    local source = { events = events }
    function source:Build()
        mock.builds[kind] = (mock.builds[kind] or 0) + 1
        if mock.failBuild == kind then error("build boom") end
        return mock.entries[kind] or {}
    end
    lib:RegisterIndexSource(kind, source)
    return source
end
for _, kind in ipairs({ "bags", "toys", "mounts", "pets", "currencies", "help" }) do
    IndexSource(kind, { "EVENT_" .. string.upper(kind) })
end

function Provider(records, overrides)
    local provider = {
        contract = 1,
        kind = "locations",
        IsAvailable = function() return mock.providerAvailable ~= false end,
        BeginSession = function(session) mock.session = session end,
        EndSession = function() mock.sessionEnded = (mock.sessionEnded or 0) + 1 end,
        Query = function(_, query)
            mock.lastQuery = query
            local out = {}
            for _, record in ipairs(records) do
                if string.find(string.lower(record.name), string.lower(query.text), 1, true) then
                    out[#out + 1] = record
                end
            end
            return out, mock.status
        end,
        Present = function(record) return { name = record.name, detail = record.zone, atlas = "poi" } end,
        Activate = function(record) mock.activated = record.id; return record.outcome or {} end,
    }
    for key, value in pairs(overrides or {}) do provider[key] = value end
    return provider
end

function Run(text, scope)
    return search:Query(text, { maxResults = 100, fuzzy = true, hidePassives = false, scope = scope })
end

function Names(list)
    local names = {}
    for index, entry in ipairs(list) do names[index] = entry.name end
    return table.concat(names, "|")
end

function Parse(query)
    local parsed = lib._Matcher.Parse(search, lib.Fold(query))
    return parsed.kindFilter, parsed.nameQuery, parsed.partial
end

function Use(kind, name, times)
    for _ = 1, times or 1 do search:Record(Entry(kind, name)) end
end
"""

CASES = {
    "reopening during provider startup retires the earlier session": r"""
        local starts, ends = 0, 0
        local callback = function() end
        lib:RegisterProvider("places", Provider({}, {
            BeginSession = function()
                starts = starts + 1
                if starts == 1 then search:BeginSessions(callback) end
            end,
            EndSession = function() ends = ends + 1 end,
        }))
        search:BeginSessions(callback)
        assert(starts == 2 and ends == 1)
        search:EndSessions()
        assert(ends == 2)
    """,
    "an embedded upgrade retains pending shared refreshes": r"""
        local calls = 0
        local other = lib:NewSearch({ kinds = KINDS, onIndexUpdated = function() calls = calls + 1 end })
        search:EnsureBuilt(); other:EnsureBuilt()
        search:SetOpen(true); other:SetOpen(true)
        FireEvent("EVENT_TOYS")
        LoadAll(2)
        local first, second = mock.indexUpdated, calls
        FlushTimers()
        assert(mock.indexUpdated == first + 1 and calls == second + 1 and mock.builds.toys == 2)
    """,
    "availability notifications reconcile and refresh without waiting for typing": r"""
        mock.providerAvailable = false
        lib:RegisterProvider("places", Provider({ { id = "a", name = "Alpha", tier = 5 } }))
        local refreshes = 0
        search:BeginSessions(function() refreshes = refreshes + 1 end)
        mock.providerAvailable = true
        lib:NotifyProviderChanged("places")
        assert(refreshes == 1 and mock.session.open and Names(Run("alpha")) == "Alpha")
        mock.providerAvailable = false
        lib:NotifyProviderChanged("places")
        assert(refreshes == 2 and mock.sessionEnded == 1)
    """,
    "provider cleanup errors do not retain sessions or repeat on close": r"""
        lib:RegisterProvider("places", Provider({}, { EndSession = function() error("end boom") end }))
        search:BeginSessions(function() end)
        local session = mock.session
        lib:UnregisterProvider("places")
        search:EndSessions()
        assert(not session.open and next(search._sessions) == nil and #mock.errors == 1)
    """,
    "disabled or unavailable providers cannot activate stale displayed entries": r"""
        lib:RegisterProvider("places", Provider({ { id = "a", name = "Alpha", tier = 5 } }))
        search:BeginSessions(function() end)
        local entry = Run("alpha")[1]
        mock.disabled.locations = true
        assert(search:Activate(entry) == nil and mock.activated == nil)
        mock.disabled.locations = nil
        mock.providerAvailable = false
        assert(search:Activate(entry) == nil and mock.activated == nil)
    """,
    "providers removing themselves during query cannot publish stale rows": r"""
        lib:RegisterProvider("places", Provider({}, { Query = function()
            lib:UnregisterProvider("places")
            return { { id = "a", name = "Alpha", tier = 5 } }
        end }))
        search:BeginSessions(function() end)
        assert(#Run("alpha") == 0 and mock.sessionEnded == 1)
    """,
    "legacy active sessions survive a newer embedded copy with their owner intact": r"""
        lib:RegisterProvider("places", Provider({ { id = "a", name = "Alpha", tier = 5 } }))
        local calls = 0
        search:BeginSessions(function() calls = calls + 1 end)
        local session = mock.session
        session.providerOwner, session.providerKey, session.ready = nil, nil, nil
        search._sessionCallback = nil
        LoadAll(2)
        assert(mock.session == session and mock.sessionEnded == nil and session.ready and calls == 1)
        assert(Names(Run("alpha")) == "Alpha")
        lib:UnregisterProvider("places")
        assert(mock.sessionEnded == 1 and not session.open)
    """,
    "global invalidation refreshes open searches while closed searches stay lazy": r"""
        search:EnsureBuilt(); search:SetOpen(true)
        lib:InvalidateAll(); FlushTimers()
        assert(mock.builds.toys == 2 and mock.indexUpdated == 1)
        search:SetOpen(false)
        lib:InvalidateAll()
        assert(#mock.timers == 0 and mock.builds.toys == 2)
        Run("x")
        assert(mock.builds.toys == 3)
    """,
    "removal cleans up the original provider exactly once": r"""
        lib:RegisterProvider("places", Provider({}))
        search:BeginSessions(function() end)
        local session = mock.session
        lib:UnregisterProvider("places")
        assert(mock.sessionEnded == 1 and not session.open)
        search:EndSessions()
        assert(mock.sessionEnded == 1)
    """,
    "replacement retires old sessions and rejects their result rows": r"""
        local old = Provider({ { id = "a", name = "Alpha", tier = 5 } })
        lib:RegisterProvider("places", old)
        search:BeginSessions(function() end)
        local entry = Run("alpha")[1]
        local session = mock.session
        local replacement = Provider({ { id = "b", name = "Beta", tier = 5 } })
        lib:RegisterProvider("places", replacement)
        assert(mock.sessionEnded == 1 and not session.open and mock.session ~= session)
        assert(Names(Run("beta")) == "Beta")
        assert(search:Activate(entry) == nil and mock.activated == nil)
        search:EndSessions()
        assert(mock.sessionEnded == 2)
    """,
    "settings reconcile providers without reopening or restarting unchanged sessions": r"""
        mock.disabled.locations = true
        lib:RegisterProvider("places", Provider({ { id = "a", name = "Alpha", tier = 5 } }))
        search:BeginSessions(function() end)
        assert(#Run("alpha") == 0)
        mock.disabled.locations = nil
        search:NotifySettingsChanged()
        assert(Names(Run("alpha")) == "Alpha")
        local session = mock.session
        search:NotifySettingsChanged()
        assert(mock.session == session and mock.sessionEnded == nil)
        mock.disabled.locations = true
        search:NotifySettingsChanged()
        assert(mock.sessionEnded == 1 and not session.open)
    """,
    "late providers join active searches and availability is reconciled on query": r"""
        search:BeginSessions(function() end)
        lib:RegisterProvider("places", Provider({ { id = "a", name = "Alpha", tier = 5 } }))
        assert(Names(Run("alpha")) == "Alpha")
        mock.providerAvailable = false
        assert(#Run("alpha") == 0 and mock.sessionEnded == 1)
        mock.providerAvailable = true
        assert(Names(Run("alpha")) == "Alpha")
        search:SetOpen(false)
        assert(mock.sessionEnded == 2)
        Run("alpha")
        assert(mock.sessionEnded == 2 and #Run("alpha") == 0)
    """,
    "failed session startup releases partial resources and waits for a new session": r"""
        lib:RegisterProvider("places", Provider({}, { BeginSession = function() error("begin boom") end }))
        search:BeginSessions(function() end)
        assert(mock.sessionEnded == 1 and #mock.errors == 1)
        Run("a"); Run("a")
        assert(mock.sessionEnded == 1 and #mock.errors == 1)
        search:EndSessions()
        assert(mock.sessionEnded == 1)
    """,
    "a provider can close its search while starting without leaking resources": r"""
        local allocated, releases = false, 0
        lib:RegisterProvider("places", Provider({}, {
            BeginSession = function() search:EndSessions(); allocated = true end,
            EndSession = function() assert(allocated); allocated = false; releases = releases + 1 end,
        }))
        search:BeginSessions(function() end)
        assert(not allocated and releases == 1 and next(search._sessions) == nil)
    """,
    "consumer invalidation errors stay inside the callback boundary": r"""
        lib:RegisterProvider("places", Provider({}))
        search:BeginSessions(function() error("consumer boom") end)
        mock.session:Invalidate()
        assert(#mock.errors == 1 and mock.errors[1]:find("consumer boom", 1, true))
    """,
    "every affected open search refreshes after one shared rebuild": r"""
        local otherCalls, unrelatedCalls = 0, 0
        local other = lib:NewSearch({ kinds = KINDS, onIndexUpdated = function() otherCalls = otherCalls + 1 end })
        local unrelated = lib:NewSearch({ kinds = { { kind = "bags" } },
            onIndexUpdated = function() unrelatedCalls = unrelatedCalls + 1 end })
        search:EnsureBuilt(); other:EnsureBuilt(); unrelated:EnsureBuilt()
        search:SetOpen(true); other:SetOpen(true); unrelated:SetOpen(true)
        FireEvent("EVENT_TOYS")
        FlushTimers()
        assert(mock.builds.toys == 2 and mock.indexUpdated == 1 and otherCalls == 1 and unrelatedCalls == 0)
    """,
    "a synchronous query cannot consume another open search's pending refresh": r"""
        search:EnsureBuilt(); search:SetOpen(true)
        FireEvent("EVENT_TOYS")
        Run("x")
        FlushTimers()
        assert(mock.builds.toys == 2 and mock.indexUpdated == 1)
    """,
    "source replacement and settings changes refresh open consumers": r"""
        search:EnsureBuilt(); search:SetOpen(true)
        IndexSource("toys", {})
        assert(mock.indexUpdated == 1)
        search:NotifySettingsChanged()
        assert(mock.indexUpdated == 2)
    """,
    "place names never become partial category filters": r"""
        for _, query in ipairs({ "hellfire peninsula", "helheim", "auric", "toyland", "petrified forest" }) do
            assert(Parse(query) == nil, query)
        end
        local expected = {
            spells = "spellbook", prof = "professions", equip = "equipped", currency = "currencies",
            macro = "macros", bag = "bags", pet = "pets", toy = "toys",
        }
        for query, kind in pairs(expected) do
            assert(Parse(query) == kind, query)
        end
        local kind, rest, partial = Parse("mounts")
        assert(kind == "mounts" and rest == "" and partial == false)
        kind, rest, partial = Parse("mount hyjal")
        assert(kind == "mounts" and rest == "hyjal" and partial == true)
    """,
    "provider kinds are category words only while registered": r"""
        assert(Parse("locations dornogal") == nil)
        assert(lib:RegisterProvider("compass.locations", Provider({})))
        local kind, rest = Parse("locations dornogal")
        assert(kind == "locations" and rest == "dornogal")
        assert(Parse("location dornogal") == "locations")
        lib:UnregisterProvider("compass.locations")
        assert(Parse("locations dornogal") == nil)
    """,
    "provider registration rejects malformed providers": r"""
        local changes = 0
        lib.RegisterCallback("test", "SourcesChanged", function() changes = changes + 1 end)
        assert(select(2, lib:RegisterProvider("a", Provider({}, { contract = 2 }))) == "contract")
        assert(select(2, lib:RegisterProvider("a", Provider({}, { Query = false }))) == "missing:Query")
        assert(select(2, lib:RegisterProvider("a", Provider({}, { kind = "toys" }))) == "kind")
        assert(lib:RegisterProvider("a", Provider({})))
        assert(select(2, lib:RegisterProvider("b", Provider({}))) == "duplicate")
        assert(lib:RegisterProvider("a", Provider({})))
        assert(lib:UnregisterProvider("a") and not lib:IsProviderRegistered("locations"))
        assert(changes == 3, changes)
    """,
    "unavailable or disabled providers are excluded from enabled kinds": r"""
        assert(not search:GetEnabledKinds().locations)
        lib:RegisterProvider("compass.locations", Provider({}))
        assert(search:GetEnabledKinds().locations)
        mock.providerAvailable = false
        assert(not search:GetEnabledKinds().locations)
        mock.providerAvailable = true
        mock.disabled.locations = true
        assert(not search:GetEnabledKinds().locations)
    """,
    "zero-result partial filter falls back to the full query and providers": r"""
        lib:RegisterProvider("compass.locations", Provider({ { id = "map:198", name = "Mount Hyjal", tier = 5 } }))
        mock.entries.mounts = { Entry("mounts", "Swift Gryphon", 1) }
        search:BeginSessions(function() end)
        local results = Run("mount hyjal")
        assert(Names(results) == "Mount Hyjal", Names(results))
        assert(mock.lastQuery.text == "mount hyjal")
        assert(#Run("hellfire") == 0)
    """,
    "a matching partial category keeps its filter": r"""
        lib:RegisterProvider("compass.locations", Provider({ { id = "x", name = "Gryphon Roost", tier = 4 } }))
        mock.entries.mounts = { Entry("mounts", "Swift Gryphon", 1) }
        search:BeginSessions(function() end)
        local results = Run("mount gryphon")
        assert(Names(results) == "Swift Gryphon", Names(results))
    """,
    "explicit provider category passes only the remaining raw words": r"""
        lib:RegisterProvider("compass.locations", Provider({ { id = "d", name = "Dornogal", tier = 5 } }))
        mock.entries.toys = { Entry("toys", "Dornogal Banner", 2) }
        search:BeginSessions(function() end)
        local results = Run("Locations DORNOGAL")
        assert(mock.lastQuery.text == "DORNOGAL", mock.lastQuery.text)
        assert(Names(results) == "Dornogal", Names(results))
    """,
    "merge orders by tier then priority band while keeping local order": r"""
        lib:RegisterProvider("compass.locations", Provider({
            { id = "a", name = "Stormwind City", tier = 4 },
            { id = "b", name = "Storm Peaks", tier = 4 },
        }))
        search:BeginSessions(function() end)
        mock.entries.toys = { Entry("toys", "Storm Totem", 1) }
        mock.entries.currencies = { Entry("currencies", "Storm Sigil", 2) }
        mock.entries.bags = { Entry("bags", "Stormforged Axe", 3) }
        mock.entries.help = { Entry("help", "storm", 4) }
        local results = Run("storm")
        assert(Names(results) == "storm|Storm Totem|Stormforged Axe|Stormwind City|Storm Peaks|Storm Sigil", Names(results))
    """,
    "local-only queries keep the matcher order untouched": r"""
        mock.entries.toys = { Entry("toys", "Storm Totem", 1) }
        mock.entries.bags = { Entry("bags", "Stormforged Axe", 2) }
        local merged = Run("storm")
        local direct = lib._Matcher.Query(search, search:GetMaster(), lib._Matcher.Parse(search, "storm"),
            search:GetEnabledKinds(), { maxResults = 100, fuzzy = true }, {})
        assert(Names(merged) == Names(direct))
    """,
    "digit queries never reach providers and resolve typed spell and item ids as one kind": r"""
        lib:RegisterProvider("compass.locations", Provider({ { id = "n", name = "123 Road", tier = 4 } }))
        search:BeginSessions(function() end)
        mock.spellNames[123] = "Arcane Test"
        mock.itemNames[123] = "Arcane Vial"
        mock.lastQuery = nil
        local results = Run("123")
        assert(mock.lastQuery == nil)
        assert(Names(results) == "Arcane Test|Arcane Vial", Names(results))
        assert(results[1].kind == "ids" and results[1].idType == "spell")
        assert(results[2].kind == "ids" and results[2].idType == "item")
        mock.disabled.ids = true
        assert(#Run("123") == 0)
    """,
    "an indexed row suppresses only the id lookup of its own type": r"""
        mock.spellNames[321] = "Arcane Test"
        mock.itemNames[321] = "Arcane Vial"
        mock.entries.bags = { Entry("bags", "Carried Vial", 321) }
        assert(Names(Run("321")) == "Arcane Test|Carried Vial", Names(Run("321")))
    """,
    "uncached ids request a load and requery open searches when it lands": r"""
        search:SetOpen(true)
        assert(#Run("456") == 0 and mock.requestedSpell == 456)
        mock.spellNames[456] = "Late Spell"
        FireEvent("SPELL_DATA_LOAD_RESULT", 456, true)
        assert(mock.indexUpdated == 1)
        assert(Run("456")[1].name == "Late Spell")
    """,
    "scoped sessions query only the provider and pass scoped raw text": r"""
        lib:RegisterProvider("compass.locations", Provider({ { id = "t", name = "Toy Town", tier = 5 } }))
        search:BeginSessions(function() end)
        mock.entries.toys = { Entry("toys", "Toy Town Balloon", 1) }
        local results = Run("Toy Town", "locations")
        assert(Names(results) == "Toy Town" and mock.lastQuery.scoped == true)
    """,
    "throwing providers are reported and contribute nothing": r"""
        lib:RegisterProvider("compass.locations", Provider({}, { Query = function() error("boom") end }))
        search:BeginSessions(function() end)
        mock.entries.toys = { Entry("toys", "Boom Box", 1) }
        local results = Run("boom")
        assert(Names(results) == "Boom Box")
        assert(mock.errors[#mock.errors]:find("compass.locations.Query", 1, true), mock.errors[#mock.errors])
    """,
    "sessions invalidate while open and end exactly once": r"""
        lib:RegisterProvider("compass.locations", Provider({}))
        local calls = 0
        search:BeginSessions(function() calls = calls + 1 end)
        mock.session:Invalidate()
        search:EndSessions()
        mock.session:Invalidate()
        search:EndSessions()
        assert(calls == 1 and mock.sessionEnded == 1)
    """,
    "provider activation returns the provider's outcome": r"""
        lib:RegisterProvider("compass.locations", Provider({}))
        local outcome = search:Activate({ kind = "locations", record = { id = "b", outcome = { replaceText = "Khaz " } } })
        assert(outcome.replaceText == "Khaz " and mock.activated == "b")
        assert(search:Activate({ kind = "locations", record = { id = "c", outcome = 5 } }) == nil)
    """,
    "frecency ranks by decayed use, not by the last touch alone": r"""
        Use("toys", "Alpha", 6)
        mock.now = mock.now + 86400 * 12
        Use("toys", "Beta", 1)
        local ranked = lib._Recents.GetRankedKeys(search._config.recents, 10)
        assert(ranked[1] == "toys:Beta" and ranked[2] == "toys:Alpha", table.concat(ranked, ","))
        Use("toys", "Alpha", 3)
        ranked = lib._Recents.GetRankedKeys(search._config.recents, 10)
        assert(ranked[1] == "toys:Alpha", table.concat(ranked, ","))
        local boost = lib._Recents.GetBoostIndex(search._config.recents)
        assert(boost["toys:Alpha"] == 1 and boost["toys:Beta"] == 2)
    """,
    "recents stay bounded and migrate the legacy ordered list": r"""
        mock.store = { "toys:Old", "toys:Older", "toys:Oldest" }
        local ranked = lib._Recents.GetRankedKeys(search._config.recents, 10)
        assert(ranked[1] == "toys:Old" and ranked[3] == "toys:Oldest", table.concat(ranked, ","))
        for index = 1, 80 do Use("toys", "Filler" .. index, 1) end
        local count = 0
        for _ in pairs(mock.store) do count = count + 1 end
        assert(count <= 50, count)
    """,
    "an empty query lists recent picks resolved from the index": r"""
        mock.entries.toys = { Entry("toys", "Alpha", 1) }
        mock.entries.mounts = { Entry("mounts", "Beta", 2) }
        mock.entries.pets = { Entry("pets", "Gamma", 3) }
        search:Record(mock.entries.mounts[1])
        mock.now = mock.now + 60
        search:Record(mock.entries.toys[1])
        assert(Names(search:Recents(5)) == "Alpha|Beta", Names(search:Recents(5)))
        mock.disabled.mounts = true
        assert(Names(search:Recents(5)) == "Alpha", Names(search:Recents(5)))
    """,
    "index kinds build lazily and rebuild only when dirty": r"""
        mock.entries.toys = { Entry("toys", "Alpha", 1) }
        Run("alpha")
        assert(mock.builds.toys == 1 and mock.builds.bags == 1)
        Run("alpha")
        assert(mock.builds.toys == 1)
        FireEvent("EVENT_TOYS")
        assert(#mock.timers == 0, "closed searches must not schedule rebuilds")
        mock.entries.toys = { Entry("toys", "Alphabet Toy", 1) }
        assert(Names(Run("alpha")) == "Alphabet Toy" and mock.builds.toys == 2 and mock.builds.bags == 1)
        mock.disabled.pets = true
        mock.entries.pets = { Entry("pets", "Alpha Pup", 3) }
        FireEvent("EVENT_PETS")
        Run("alpha")
        assert(mock.builds.pets == 1, "disabled kinds wait for re-enable")
    """,
    "open searches debounce rebuilds and hear the update": r"""
        Run("x")
        search:SetOpen(true)
        FireEvent("EVENT_TOYS")
        FireEvent("EVENT_TOYS")
        assert(#mock.timers == 2 and mock.timers[1].cancelled)
        FlushTimers()
        assert(mock.builds.toys == 2 and mock.indexUpdated == 1)
        search:Disable()
        FireEvent("EVENT_TOYS")
        assert(#mock.timers == 0, "a disabled search unregisters source events")
    """,
    "a throwing index source retires previous entries and reports once": r"""
        mock.entries.toys = { Entry("toys", "Kept Toy", 1) }
        Run("kept")
        mock.failBuild = "toys"
        lib:InvalidateAll()
        local before = #mock.errors
        assert(#Run("kept") == 0)
        assert(#mock.errors == before + 1 and lib:GetBuildErrors().toys:find("build boom", 1, true))
        Run("kept")
        assert(#mock.errors == before + 1, "a failed kind waits for its next event")
    """,
    "inclusion follows enabled searches and their settings": r"""
        lib:RegisterProvider("compass.locations", Provider({}))
        assert(lib:IsKindIncluded("locations"))
        mock.disabled.locations = true
        assert(not lib:IsKindIncluded("locations"))
        mock.disabled.locations = nil
        search:Disable()
        assert(not lib:IsKindIncluded("locations"))
    """,
    "a duplicate copy stands down and a newer copy upgrades existing searches": r"""
        lib:RegisterProvider("compass.locations", Provider({}))
        local sourcesBefore = lib._indexSources.toys
        LoadAll(1)
        assert(lib._indexSources.toys == sourcesBefore and lib:IsProviderRegistered("locations"))
        assert(lib.__building == false)
        LoadAll(2)
        assert(lib:IsProviderRegistered("locations") and lib._indexSources.toys == sourcesBefore)
        mock.entries.toys = { Entry("toys", "Upgrade Toy", 1) }
        assert(Names(Run("upgrade")) == "Upgrade Toy")
        assert(lib.__building == false)
    """,
}

SOURCE_SETUP = r"""
Enum = { SpellBookSpellBank = { Player = 0, Pet = 1 }, ItemQuality = { Heirloom = 7 },
    BagIndex = { Backpack = 0, Keyring = -1 } }
NUM_TOTAL_EQUIPPED_BAG_SLOTS = 5
ITEMS = "Items"
BAG_FILTER_QUEST_ITEMS = "Quest Items"
mock.bags, mock.quest, mock.items = {}, {}, {}
C_Container = {
    GetContainerNumSlots = function(bag) return bag == 0 and #mock.bags or 0 end,
    GetContainerItemInfo = function(bag, slot)
        local item = bag == 0 and mock.bags[slot]
        if not item then return nil end
        return { itemID = item.id, hyperlink = item.link, iconFileID = 1 }
    end,
    GetContainerItemQuestInfo = function(bag, slot)
        local item = bag == 0 and mock.bags[slot]
        return { isQuestItem = item ~= nil and mock.quest[item.id] == true, isActive = false }
    end,
}
function GetItemInfo(link)
    local item = mock.items[link]
    if not item then return nil end
    return item.name, link, 1, 0, 0, "Consumable", "Other", 1, "", 1, 0, 0, 0, 1, nil, nil, false
end
function GetItemCount() return 1 end
function BagSearch()
    local lib = LibStub("LibOrbitSearch-1.0")
    local search = lib:NewSearch({ kinds = { { kind = "bags", label = "Bags" } } })
    search:Enable()
    return search
end
"""

SOURCE_CASES = {
    "built-in sources register from the manifest, and quest items are not one of them": r"""
        local lib = LibStub("LibOrbitSearch-1.0")
        local expected = { "bags", "equipped", "spellbook", "toys", "mounts", "pets", "heirlooms",
            "professions", "currencies", "macros" }
        for _, kind in ipairs(expected) do assert(lib:IsIndexSourceRegistered(kind), kind) end
        assert(not lib:IsIndexSourceRegistered("questitems"), "quest items are a bag tag, not a kind")
        assert(lib.__building == false)
    """,
    "bag rows carry Blizzard's quest word only while the slot is marked": r"""
        local lib = LibStub("LibOrbitSearch-1.0")
        mock.bags = { { id = 11, link = "item:11" }, { id = 12, link = "item:12" } }
        mock.items = { ["item:11"] = { name = "Flare Gun" }, ["item:12"] = { name = "Flask" } }
        mock.quest = { [11] = true }
        local search = BagSearch()
        local options = { maxResults = 10, fuzzy = false, hidePassives = false }
        local results = search:Query("quest", options)
        assert(#results == 1 and results[1].name == "Flare Gun", #results)
        assert(search:Query("flask", options)[1].name == "Flask")
        mock.quest = {}
        lib:InvalidateAll()
        assert(#search:Query("quest", options) == 0)
        local events = {}
        for _, event in ipairs(lib._indexSources.bags.events) do events[event] = true end
        assert(events.QUEST_ACCEPTED and events.UNIT_QUEST_LOG_CHANGED and events.BAG_UPDATE_DELAYED)
    """,
}


def manifest_files():
    return [RUNTIME / name.replace("\\", "/") for name in re.findall(r'file="([^"]+)"', MANIFEST.read_text())]


def engine_sources(minor):
    for path in manifest_files():
        if "Sources/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        if path.name == "LibOrbitSearch-1.0.lua":
            text = re.sub(r'"LibOrbitSearch-1\.0", \d+', f'"LibOrbitSearch-1.0", {minor}', text, count=1)
        yield text, path.name


def main():
    failures = []
    for name, case in CASES.items():
        lua = LuaRuntime()
        try:
            lua.execute(HARNESS)
            load = lua.eval("LoadSource")
            for text, source_name in engine_sources(1):
                load(text, source_name)

            def load_all(minor):
                for text, source_name in engine_sources(minor):
                    load(text, source_name)

            lua.globals().LoadAll = load_all
            lua.execute(SETUP)
            lua.execute(case)
        except Exception as exc:
            failures.append((name, str(exc)))
    for name, case in SOURCE_CASES.items():
        lua = LuaRuntime()
        try:
            lua.execute(HARNESS)
            lua.execute(SOURCE_SETUP)
            load = lua.eval("LoadSource")
            for path in manifest_files():
                load(path.read_text(encoding="utf-8"), path.name)
            lua.execute(case)
        except Exception as exc:
            failures.append((name, str(exc)))
    total = len(CASES) + len(SOURCE_CASES)
    for name, error in failures:
        print(f"FAIL: {name}\n{error}")
    print(f"LibOrbitSearch engine: {total - len(failures)}/{total} passed (simulated APIs).")
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
