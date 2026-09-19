-- [ RECENTS ]----------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local MAX_ENTRIES = 50
local MAX_BOOSTED = 8
local HALF_LIFE_DAYS = 3
local SECONDS_PER_DAY = 86400
local LEGACY_SPACING_SECONDS = 3600

local Recents = {}
lib._Recents = Recents

-- [ STORE ]------------------------------------------------------------------------------------------------------------
local function MakeKey(kind, id)
    return kind .. ":" .. tostring(id)
end

local function MigrateLegacyList(list, now)
    local records = {}
    for index = #list, 1, -1 do
        local key = list[index]
        if type(key) == "string" then
            records[key] = { count = 1, last = now - (index - 1) * LEGACY_SPACING_SECONDS }
        end
    end
    return records
end

local function GetRecords(store)
    local stored = store.Load()
    if type(stored) ~= "table" then
        stored = {}
        store.Save(stored)
        return stored
    end
    if stored[1] ~= nil then
        stored = MigrateLegacyList(stored, time())
        store.Save(stored)
    end
    return stored
end

-- [ FRECENCY ]---------------------------------------------------------------------------------------------------------
local function Frecency(record, now)
    local age = math.max(0, now - (record.last or now))
    return (record.count or 1) * 0.5 ^ (age / (HALF_LIFE_DAYS * SECONDS_PER_DAY))
end

local function Ranked(records, now)
    local keys = {}
    for key in pairs(records) do
        keys[#keys + 1] = key
    end
    table.sort(keys, function(a, b)
        local scoreA, scoreB = Frecency(records[a], now), Frecency(records[b], now)
        if scoreA ~= scoreB then
            return scoreA > scoreB
        end
        return a < b
    end)
    return keys
end

local function Prune(records, now)
    local keys = Ranked(records, now)
    for index = MAX_ENTRIES + 1, #keys do
        records[keys[index]] = nil
    end
end

-- [ PUBLIC ]-----------------------------------------------------------------------------------------------------------
function Recents.Record(store, entry)
    if not entry or not entry.kind or entry.id == nil then
        return
    end
    local records = GetRecords(store)
    local key = MakeKey(entry.kind, entry.id)
    local record = records[key]
    local now = time()
    if record then
        -- Counting in decayed units keeps a long-idle favourite from outranking what the player uses today.
        record.count = Frecency(record, now) + 1
        record.last = now
    else
        records[key] = { count = 1, last = now }
        Prune(records, now)
    end
end

function Recents.GetBoostIndex(store)
    local keys = Ranked(GetRecords(store), time())
    local boost = {}
    for index = 1, math.min(MAX_BOOSTED, #keys) do
        boost[keys[index]] = index
    end
    return boost
end

function Recents.GetRankedKeys(store, limit)
    local keys = Ranked(GetRecords(store), time())
    for index = #keys, (limit or MAX_ENTRIES) + 1, -1 do
        keys[index] = nil
    end
    return keys
end

function Recents.MakeKey(kind, id)
    return MakeKey(kind, id)
end
