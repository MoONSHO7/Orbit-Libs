-- [ QUESTIE INDEX ]----------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitBridge-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local Readable, Number = lib.Readable, lib.Number
local REQUIRED_CONTRACT = 4
local PERCENT = 100
local BUILD_BUDGET_MS = 0.5
local DRIVER = "QuestieIndex"
local PROFILER_LABEL = "Questie.Index"
local NPC_SLOT, OBJECT_SLOT, ITEM_SLOT = 1, 2, 3
-- QuestieDB service flag name and the Enum.MinimapTrackingFilter field whose icon and label present it.
local SERVICES = {
    { flag = "INNKEEPER", filter = "Innkeeper" },
    { flag = "REPAIR", filter = "Repair" },
    { flag = "BANKER", filter = "Banker" },
    { flag = "AUCTIONEER", filter = "Auctioneer" },
    { flag = "STABLEMASTER", filter = "Stablemaster" },
}
-- QuestieDB's untranslated mailbox object name; the tracking list's Mailbox name matches translated ones.
local MAILBOX_NAME = "Mailbox"
local MAILBOX_SERVICES = table.freeze({ "Mailbox" })
local NPC_GETTERS = { "GetAllIds", "npcFlags", "spawns", "friendlyToFaction", "name" }
local OBJECT_GETTERS = { "GetAllIds", "spawns", "name" }
local QUEST_GETTERS = { "GetAllIds", "GetAll", "startedBy", "name" }
local ITEM_GETTERS = { "npcDrops", "objectDrops", "vendors", "name" }
local LEVEL_FIELDS = { "questLevel" }

local Questie = lib.Questie
lib._questie = lib._questie or {}
local state = lib._questie

-- QuestieDB masks can exceed 32 bits, so single-bit membership uses arithmetic rather than the 32-bit bit library.
function Questie.HasBit(mask, value)
    return value ~= nil and value > 0 and math.floor(mask / value) % 2 == 1
end

local function HasFunctions(entity, names)
    if type(entity) ~= "table" then
        return false
    end
    for _, name in ipairs(names) do
        if type(entity[name]) ~= "function" then
            return false
        end
    end
    return true
end

-- The installed QuestieDB when it meets contract 4 (NPC flags and class keys) and exposes every read used here.
function Questie.Provider()
    local db = Readable(_G.LibQuestieDB)
    if
        type(db) ~= "table"
        or type(db.RequireContract) ~= "function"
        or db.RequireContract(REQUIRED_CONTRACT) ~= true
    then
        return
    end
    local enum, support = db.Enum, db.Support
    if
        not HasFunctions(db.Npc, NPC_GETTERS)
        or not HasFunctions(db.Object, OBJECT_GETTERS)
        or not HasFunctions(db.Quest, QUEST_GETTERS)
        or not HasFunctions(db.Item, ITEM_GETTERS)
        or type(support) ~= "table"
        or type(support.Get) ~= "function"
        or type(enum) ~= "table"
        or type(enum.npcFlags) ~= "table"
        or type(enum.classKeys) ~= "table"
        or type(enum.raceMaskById) ~= "table"
    then
        return
    end
    return db
end

-- Each service's localized name and icon from the client's own minimap tracking list; empty until that list loads.
function Questie.TrackingArt()
    local art = state.tracking
    if art then
        return art
    end
    local minimap = C_Minimap
    if
        type(minimap.GetNumTrackingTypes) ~= "function"
        or type(minimap.GetTrackingInfo) ~= "function"
        or type(minimap.GetTrackingFilter) ~= "function"
    then
        return {}
    end
    local count = Number(minimap.GetNumTrackingTypes())
    if not count or count <= 0 then
        return {}
    end
    art = {}
    for index = 1, count do
        local info, filter = Readable(minimap.GetTrackingInfo(index)), Readable(minimap.GetTrackingFilter(index))
        local filterID = type(filter) == "table" and Number(filter.filterID)
        if filterID and type(info) == "table" and not art[filterID] then
            local name = Readable(info.name)
            art[filterID] = { texture = Number(info.texture), name = type(name) == "string" and name or nil }
        end
    end
    state.tracking = art
    return art
end

-- QuestieDB publishes its area-to-UiMap table as Lua source for consumers to load; it runs without any environment.
local function AreaMaps(zoneDB)
    local private = type(zoneDB) == "table" and zoneDB.private
    local source = type(private) == "table" and private.areaIdToUiMapId
    if type(source) ~= "string" then
        return
    end
    local chunk = loadstring(source)
    if not chunk then
        return
    end
    setfenv(chunk, {})
    local ok, maps = pcall(chunk)
    return ok and type(maps) == "table" and maps or nil
end

local function Bucket(build, mapID, kind)
    local entry = build.byMap[mapID]
    if not entry then
        entry = { givers = {}, services = {}, entrances = {} }
        build.byMap[mapID] = entry
    end
    return entry[kind]
end

-- `ordinals` numbers one record's points per map, so a marker key never depends on other records' spawns.
local function AddPoint(build, areaID, x, y, kind, record, ordinals)
    local mapID = Number(build.areaMaps[areaID])
    x, y = Number(x), Number(y)
    if mapID and mapID > 0 and x and y and x >= 0 and x <= PERCENT and y >= 0 and y <= PERCENT then
        local list = Bucket(build, mapID, kind)
        ordinals[mapID] = (ordinals[mapID] or 0) + 1
        list[#list + 1] = { record = record, x = x / PERCENT, y = y / PERCENT, ordinal = ordinals[mapID] }
    end
end

local function AddSpawns(build, spawns, kind, record)
    local ordinals = {}
    for areaID, points in pairs(spawns) do
        if type(points) == "table" then
            for _, point in ipairs(points) do
                if type(point) == "table" then
                    AddPoint(build, areaID, point[1], point[2], kind, record, ordinals)
                end
            end
        end
    end
end

local function AddStarters(starters, owners, questID)
    if type(owners) ~= "table" then
        return
    end
    for _, owner in ipairs(owners) do
        owner = Number(owner)
        if owner then
            local quests = starters[owner]
            if not quests then
                quests = {}
                starters[owner] = quests
            end
            quests[#quests + 1] = questID
        end
    end
end

-- Givers come from each quest's starters, so only the mailbox pass reads the 6.6k-row object table, names only.
-- A retired quest never enters the index, so no consumer can offer it.
local function IndexQuest(build, quest, id)
    if Questie.IsRetired(id) then
        return
    end
    local startedBy = quest.startedBy(id)
    if type(startedBy) == "table" then
        AddStarters(build.npcQuests, startedBy[NPC_SLOT], id)
        AddStarters(build.objectQuests, startedBy[OBJECT_SLOT], id)
        -- A quest an item starts has no giver to stand at. Its level is kept so that only a quest in the
        -- character's range is ever decoded, and its droppers are read only once it is offered.
        local items = {}
        for _, itemID in ipairs(type(startedBy[ITEM_SLOT]) == "table" and startedBy[ITEM_SLOT] or items) do
            items[#items + 1] = Number(itemID)
        end
        if #items > 0 then
            local values = quest.GetAll(id, LEVEL_FIELDS)
            local level = type(values) == "table" and Number(values[1]) or 0
            build.startQuests[#build.startQuests + 1], build.startItems[id] = { id = id, level = level }, items
        end
    end
end

local function ServiceFilters(build, flags)
    local found
    for _, service in ipairs(build.services) do
        if Questie.HasBit(flags, service.bit) then
            found = found or {}
            found[#found + 1] = service.filter
        end
    end
    return found
end

local function IndexNpc(build, npc, id)
    local quests = build.npcQuests[id]
    local flags = Number(npc.npcFlags(id)) or 0
    local services = flags ~= 0 and ServiceFilters(build, flags) or nil
    if not quests and not services then
        return
    end
    local spawns = npc.spawns(id)
    local faction = npc.friendlyToFaction(id)
    if type(spawns) ~= "table" or type(faction) ~= "string" then
        return
    end
    local record = { entity = "npc", id = id, quests = quests, services = services, faction = faction }
    if quests then
        AddSpawns(build, spawns, "givers", record)
    end
    if services then
        AddSpawns(build, spawns, "services", record)
    end
end

local function IndexObject(build, object, id)
    local spawns = object.spawns(id)
    if type(spawns) == "table" then
        AddSpawns(build, spawns, "givers", { entity = "object", id = id, quests = build.objectQuests[id] })
    end
end

-- QuestieDB has no object type, so a mailbox is known by its name alone.
local function IndexMailbox(build, object, id)
    if not build.mailboxNames[Readable(object.name(id))] then
        return
    end
    local spawns = object.spawns(id)
    if type(spawns) == "table" then
        AddSpawns(build, spawns, "services", { entity = "object", id = id, services = MAILBOX_SERVICES })
    end
end

-- An instance counts only when this client names its map; QuestieDB's table also carries later expansions' entrances.
local function IndexEntrances(build, zoneDB)
    local private = zoneDB.private
    local dungeons = type(private) == "table" and private.dungeons
    local instances = zoneDB.instanceIdToAreaId
    if type(dungeons) ~= "table" or type(instances) ~= "table" then
        return
    end
    for instanceID, areaID in pairs(instances) do
        instanceID = Number(instanceID)
        local name = instanceID and Readable(GetRealZoneText(instanceID))
        local entry = dungeons[areaID]
        local locations = type(entry) == "table" and entry[4]
        if type(name) == "string" and name ~= "" and type(locations) == "table" then
            local record, ordinals = { entity = "instance", id = instanceID, name = name }, {}
            for _, location in ipairs(locations) do
                if type(location) == "table" then
                    AddPoint(build, location[1], location[2], location[3], "entrances", record, ordinals)
                end
            end
        end
    end
end

local function StartBuild(db)
    local zoneDB = db.Support.Get("ZoneDB")
    local areaMaps = AreaMaps(zoneDB)
    if not areaMaps then
        return
    end
    local services = {}
    for _, service in ipairs(SERVICES) do
        local value = Number(db.Enum.npcFlags[service.flag])
        if value and value > 0 then
            services[#services + 1] = { bit = value, filter = service.filter }
        end
    end
    local mailboxNames = { [MAILBOX_NAME] = true }
    local mailbox = Questie.TrackingArt()[Enum.MinimapTrackingFilter[MAILBOX_SERVICES[1]]]
    if mailbox and mailbox.name then
        mailboxNames[mailbox.name] = true
    end
    return {
        lib = db,
        zoneDB = zoneDB,
        areaMaps = areaMaps,
        services = services,
        mailboxNames = mailboxNames,
        byMap = {},
        npcQuests = {},
        objectQuests = {},
        startQuests = {},
        startItems = {},
        questIDs = db.Quest.GetAllIds(),
        npcIDs = db.Npc.GetAllIds(),
        objectIDs = db.Object.GetAllIds(),
        questCursor = 0,
        npcCursor = 0,
        objectCursor = 0,
    }
end

-- Advances the build within this frame's budget; true once the index is published.
local function Step()
    local build = state.build
    local db, deadline = build.lib, debugprofilestop() + BUILD_BUDGET_MS
    while build.questCursor < #build.questIDs do
        build.questCursor = build.questCursor + 1
        IndexQuest(build, db.Quest, build.questIDs[build.questCursor])
        if debugprofilestop() >= deadline then
            return false
        end
    end
    while build.npcCursor < #build.npcIDs do
        build.npcCursor = build.npcCursor + 1
        IndexNpc(build, db.Npc, build.npcIDs[build.npcCursor])
        if debugprofilestop() >= deadline then
            return false
        end
    end
    while build.objectCursor < #build.objectIDs do
        build.objectCursor = build.objectCursor + 1
        IndexMailbox(build, db.Object, build.objectIDs[build.objectCursor])
        if debugprofilestop() >= deadline then
            return false
        end
    end
    for objectID in pairs(build.objectQuests) do
        IndexObject(build, db.Object, objectID)
    end
    IndexEntrances(build, build.zoneDB)
    -- `plans`, `spawns` and `places` are the objective planner's session caches; `quests` the decoded quest rows.
    state.index = {
        lib = db,
        byMap = build.byMap,
        areaMaps = build.areaMaps,
        startQuests = build.startQuests,
        startItems = build.startItems,
        quests = {},
        plans = {},
        spawns = {},
        places = {},
    }
    state.build = nil
    return true
end

-- One protected step per frame: a failing build stops for the session instead of erroring every frame.
local function Drive()
    local start, startKB = lib:_ProfileBegin()
    local ok, done = pcall(Step)
    lib:_ProfileEnd(PROFILER_LABEL, start, startKB)
    if ok and not done then
        return false
    end
    if not ok then
        local build = state.build
        state.failed, state.build = build and build.lib, nil
        lib:_Report(done)
        return true
    end
    lib:_Fire("QuestieIndexReady", state.index)
    return true
end

-- The published index; otherwise nil plus whether one is still building in its own per-frame budget. Asking
-- registers `owner`'s demand, which `lib.Release(owner)` gives up.
function Questie.Request(owner, db)
    lib:_Demand(owner)
    local index = state.index
    if index and index.lib == db then
        return index
    end
    if state.failed == db then
        return nil, false
    end
    local build = state.build
    if not build or build.lib ~= db then
        build = StartBuild(db)
        if not build then
            return nil, false
        end
        state.build = build
        lib:_StartDriver(DRIVER, Drive)
    end
    return nil, true
end
