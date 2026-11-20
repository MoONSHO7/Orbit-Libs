-- [ QUESTIE OBJECTIVES ]-----------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitBridge-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local Readable, Number, Text = lib.Readable, lib.Number, lib.Text
local PERCENT = 100
local PREPARE_BUDGET_MS = 0.5
local DRIVER = "QuestiePrepare"
local PROFILER_LABEL = "Questie.Prepare"
local CELLS_PER_EDGE = 40
local MAX_SPOTS = 24
local MAX_TURN_IN_SPOTS = 4
local MAX_SOURCES = 16
local PLAN_FIELDS = { "objectives", "triggerEnd", "finishedBy" }
local NPC_SLOT, OBJECT_SLOT = 1, 2
local GROUP_SLOTS = { creature = 1, object = 2, item = 3, reputation = 4, credit = 5, spell = 6 }
local DEFAULT_ORDER = { "creature", "object", "item", "reputation", "credit", "spell" }
local START_PREFIX = "start:"
local NONE = table.freeze({})

local Questie = lib.Questie
Questie.MAX_SPOTS = MAX_SPOTS
lib._questiePrepare = lib._questiePrepare or { queue = {}, queued = {} }
local state = lib._questiePrepare

local function Source(lib, entity, id)
    id = Number(id)
    if not id then
        return
    end
    local npc = entity == "npc"
    return {
        entity = entity,
        id = id,
        ref = (npc and "n" or "o") .. id,
        name = Text((npc and lib.Npc or lib.Object).name(id)),
    }
end

local function AddSources(lib, sources, entity, ids)
    if type(ids) ~= "table" then
        return
    end
    for _, id in ipairs(ids) do
        if #sources >= MAX_SOURCES then
            return
        end
        sources[#sources + 1] = Source(lib, entity, id)
    end
end

-- A malformed tuple still takes its place in the list, so later objectives keep the client's index.
local function Targets(lib, kind, entity, tuples)
    local objectives = {}
    for _, tuple in ipairs(tuples) do
        local source = type(tuple) == "table" and Source(lib, entity, tuple[1]) or nil
        objectives[#objectives + 1] = {
            kind = source and kind or nil,
            type = entity == "npc" and "monster" or "object",
            name = type(tuple) == "table" and Text(tuple[2]) or source and source.name,
            sources = source and { source } or nil,
        }
    end
    return objectives
end

local function Items(lib, tuples)
    local objectives = {}
    for _, tuple in ipairs(tuples) do
        local itemID = type(tuple) == "table" and Number(tuple[1]) or nil
        local sources = {}
        if itemID then
            AddSources(lib, sources, "npc", lib.Item.npcDrops(itemID))
            AddSources(lib, sources, "object", lib.Item.objectDrops(itemID))
            if #sources == 0 then
                AddSources(lib, sources, "npc", lib.Item.vendors(itemID))
            end
        end
        objectives[#objectives + 1] = {
            kind = #sources > 0 and "item" or nil,
            type = "item",
            itemID = itemID,
            name = itemID and (Text(tuple[2]) or Text(lib.Item.name(itemID))) or nil,
            sources = sources,
        }
    end
    return objectives
end

local function Credits(lib, tuples)
    local objectives = {}
    for _, tuple in ipairs(tuples) do
        local sources, name = {}, nil
        if type(tuple) == "table" then
            AddSources(lib, sources, "npc", tuple[1])
            local base = Number(tuple[2])
            name = Text(tuple[3]) or base and Text(lib.Npc.name(base)) or sources[1] and sources[1].name
        end
        objectives[#objectives + 1] = {
            kind = #sources > 0 and "credit" or nil,
            type = "monster",
            name = name,
            sources = sources,
        }
    end
    return objectives
end

-- Reputation and spell objectives have no place on a map; they only hold their index in the client's list.
local BUILDERS = {
    creature = function(lib, tuples)
        return Targets(lib, "creature", "npc", tuples)
    end,
    object = function(lib, tuples)
        return Targets(lib, "object", "object", tuples)
    end,
    item = Items,
    credit = Credits,
    reputation = function()
        return { { type = "reputation" } }
    end,
    spell = function(_, tuples)
        local objectives = {}
        for index in ipairs(tuples) do
            objectives[index] = {}
        end
        return objectives
    end,
}

local function Hinted(hints, name, questID)
    local set = type(hints) == "table" and hints[name]
    return type(set) == "table" and set[questID] == true
end

-- QuestieDB's groups in the client's objective order: its own order unless a hint names the group a quest lists first.
local function GroupOrder(hints, questID)
    local lead = Hinted(hints, "killCreditObjectiveFirst", questID) and "credit"
        or Hinted(hints, "objectObjectiveFirst", questID) and "object"
        or Hinted(hints, "itemObjectiveFirst", questID) and "item"
        or nil
    local order = {}
    if Hinted(hints, "spellObjectiveFirst", questID) then
        order[1] = "spell"
    end
    if lead then
        order[#order + 1] = lead
    end
    for _, group in ipairs(DEFAULT_ORDER) do
        if group ~= lead and group ~= order[1] then
            order[#order + 1] = group
        end
    end
    return order
end

-- QuestieDB marks an instance spawn as (-1, -1); those and areas without a UI map drop out.
local function Points(index, spawns)
    if type(spawns) ~= "table" then
        return
    end
    local byMap
    for areaID, points in pairs(spawns) do
        local mapID = Number(index.areaMaps[areaID])
        if mapID and mapID > 0 and type(points) == "table" then
            for _, point in ipairs(points) do
                local x = type(point) == "table" and Number(point[1])
                local y = x and Number(point[2])
                if y and x >= 0 and x <= PERCENT and y >= 0 and y <= PERCENT then
                    byMap = byMap or {}
                    local flat = byMap[mapID]
                    if not flat then
                        flat = {}
                        byMap[mapID] = flat
                    end
                    flat[#flat + 1], flat[#flat + 2] = x / PERCENT, y / PERCENT
                end
            end
        end
    end
    return byMap
end

local function AddFinishers(lib, finishers, entity, ids)
    local first = #finishers + 1
    AddSources(lib, finishers, entity, ids)
    for position = first, entity == "npc" and #finishers or 0 do
        finishers[position].faction = Text(lib.Npc.friendlyToFaction(finishers[position].id))
    end
end

local function Plan(objectives, finishers)
    local plan = { objectives = objectives, finishers = finishers, sources = {} }
    local seen = {}
    local function Gather(sources)
        for _, source in ipairs(sources or NONE) do
            if not seen[source.ref] then
                seen[source.ref] = true
                plan.sources[#plan.sources + 1] = source
            end
        end
    end
    for _, objective in ipairs(objectives) do
        Gather(objective.sources)
    end
    Gather(finishers)
    plan.nowhere = { plan = plan, spots = NONE, turnIns = NONE }
    return plan
end

local function BuildPlan(index, questID)
    local lib = index.lib
    local values = lib.Quest.GetAll(questID, PLAN_FIELDS)
    if type(values) ~= "table" then
        return false
    end
    local groups, trigger, finishedBy = values[1], values[2], values[3]
    local hints = Readable(lib.ObjectiveFirst)
    local objectives, finishers = {}, {}
    if type(groups) == "table" then
        for _, group in ipairs(GroupOrder(hints, questID)) do
            local tuples = groups[GROUP_SLOTS[group]]
            if type(tuples) == "table" then
                for _, objective in ipairs(BUILDERS[group](lib, tuples)) do
                    objectives[#objectives + 1] = objective
                end
            end
        end
    end
    if type(trigger) == "table" then
        local points = Points(index, trigger[2])
        local event = { kind = points and "event" or nil, type = "event", name = Text(trigger[1]), points = points }
        table.insert(objectives, Hinted(hints, "eventObjectiveFirst", questID) and 1 or #objectives + 1, event)
    end
    if type(finishedBy) == "table" then
        AddFinishers(lib, finishers, "npc", finishedBy[NPC_SLOT])
        AddFinishers(lib, finishers, "object", finishedBy[OBJECT_SLOT])
    end
    return Plan(objectives, finishers)
end

-- The plan of a quest an item starts: each such item is one "objective", placed where the item drops.
local function BuildStartPlan(index, questID)
    local tuples = {}
    for position, itemID in ipairs(index.startItems[questID] or NONE) do
        tuples[position] = { itemID }
    end
    return #tuples > 0 and Plan(Items(index.lib, tuples), {})
end

local function Denser(first, second)
    if first.count ~= second.count then
        return first.count > second.count
    end
    return first.cell < second.cell
end

local function AddPoints(cells, spots, flat, source)
    for cursor = 1, #flat, 2 do
        local x, y = flat[cursor], flat[cursor + 1]
        local column = math.min(CELLS_PER_EDGE - 1, math.floor(x * CELLS_PER_EDGE))
        local cell = column * CELLS_PER_EDGE + math.min(CELLS_PER_EDGE - 1, math.floor(y * CELLS_PER_EDGE))
        local spot = cells[cell]
        if not spot then
            spot = { cell = cell, x = 0, y = 0, count = 0, sources = {} }
            cells[cell] = spot
            spots[#spots + 1] = spot
        end
        spot.x, spot.y, spot.count = spot.x + x, spot.y + y, spot.count + 1
        if source and spot.sources[#spot.sources] ~= source then
            spot.sources[#spot.sources + 1] = source
        end
    end
end

local function Cluster(index, mapID, sources, points, limit)
    local cells, spots = {}, {}
    for _, source in ipairs(sources or NONE) do
        local spawns = index.spawns[source.ref]
        if spawns and spawns[mapID] then
            AddPoints(cells, spots, spawns[mapID], source)
        end
    end
    if points and points[mapID] then
        AddPoints(cells, spots, points[mapID])
    end
    for _, spot in ipairs(spots) do
        spot.x, spot.y = spot.x / spot.count, spot.y / spot.count
    end
    table.sort(spots, Denser)
    for position = #spots, limit + 1, -1 do
        spots[position] = nil
    end
    return spots
end

local function Place(index, plan, mapID)
    local spots, turnIns, found = {}, {}, false
    for position, objective in ipairs(plan.objectives) do
        if objective.kind then
            local list = Cluster(index, mapID, objective.sources, objective.points, MAX_SPOTS)
            if #list > 0 then
                spots[position], found = list, true
            end
        end
    end
    for _, finisher in ipairs(plan.finishers) do
        for _, spot in ipairs(Cluster(index, mapID, { finisher }, nil, MAX_TURN_IN_SPOTS)) do
            turnIns[#turnIns + 1] = spot
        end
    end
    if not found and #turnIns == 0 then
        return plan.nowhere
    end
    return { plan = plan, spots = spots, turnIns = turnIns }
end

local function Prepare(index, job, deadline)
    local key, mapID = job.planKey, job.mapID
    local plan = index.plans[key]
    if plan == nil then
        plan = (job.start and BuildStartPlan or BuildPlan)(index, job.questID)
        index.plans[key] = plan
        if plan and debugprofilestop() >= deadline then
            return false
        end
    end
    local places = index.places[mapID]
    if not places then
        places = {}
        index.places[mapID] = places
    end
    if not plan then
        places[key] = false
        return true
    end
    for _, source in ipairs(plan.sources) do
        if index.spawns[source.ref] == nil then
            local reader = source.entity == "npc" and index.lib.Npc or index.lib.Object
            index.spawns[source.ref] = Points(index, reader.spawns(source.id)) or false
            if debugprofilestop() >= deadline then
                return false
            end
        end
    end
    places[key] = Place(index, plan, mapID)
    return true
end

local function Step()
    local queue, deadline = state.queue, debugprofilestop() + PREPARE_BUDGET_MS
    while #queue > 0 do
        local job = queue[#queue]
        if not Prepare(job.index, job, deadline) then
            return false
        end
        local places = job.index.places[job.mapID][job.planKey]
        state.found = state.found or places and places ~= places.plan.nowhere
        queue[#queue], state.queued[job.key] = nil, nil
        if debugprofilestop() >= deadline then
            return #queue == 0
        end
    end
    return true
end

-- One protected step per frame: a quest whose data fails is dropped and reported once, not retried each frame.
local function Drive()
    local start, startKB = lib:_ProfileBegin()
    local ok, done = pcall(Step)
    lib:_ProfileEnd(PROFILER_LABEL, start, startKB)
    if not ok then
        local job = table.remove(state.queue)
        state.queued[job.key] = nil
        local places = job.index.places[job.mapID] or {}
        job.index.places[job.mapID], places[job.planKey] = places, false
        if not state.reported then
            state.reported = true
            lib:_Report(done)
        end
        done = #state.queue == 0
    end
    if done and state.found then
        state.found = false
        lib:_Fire("QuestiePlacesFound")
    end
    return done
end

-- The quest's plan: nil until prepared for some map, false for a quest QuestieDB does not know.
function Questie.Plan(index, questID)
    return index.plans[questID]
end

-- Whether the client's live list lines up with the plan, so a position in one is the same objective in the other.
function Questie.Aligned(plan, live)
    if #live ~= #plan.objectives then
        return false
    end
    for position, objective in ipairs(plan.objectives) do
        if objective.type and live[position].type ~= objective.type then
            return false
        end
    end
    return true
end

-- Whether the plan places an objective the quest still needs; a list that does not line up needs them all.
function Questie.Locates(plan, live)
    local aligned = Questie.Aligned(plan, live)
    for position, objective in ipairs(plan.objectives) do
        if objective.kind and not (aligned and live[position].finished) then
            return true
        end
    end
    return false
end

-- A log quest's plan and the plan of where an offered quest's starting item drops are kept apart by this key.
local function PlanKey(questID, start)
    return start and START_PREFIX .. questID or questID
end

-- The quest's cached places on the map: nil until prepared, false for a quest QuestieDB does not know. `start`
-- asks for where the item that starts the quest drops instead of where its objectives are done.
function Questie.Places(index, questID, mapID, start)
    local places = index.places[mapID]
    if places then
        return places[PlanKey(questID, start)]
    end
end

-- Queues the quest's places on the map; `QuestiePlacesFound` fires once a drained queue placed something.
function Questie.Prepare(owner, index, questID, mapID, start)
    lib:_Demand(owner)
    local planKey = PlanKey(questID, start)
    local key = mapID .. ":" .. planKey
    if not state.queued[key] then
        state.queued[key] = true
        state.queue[#state.queue + 1] =
            { key = key, index = index, questID = questID, mapID = mapID, planKey = planKey, start = start }
    end
    lib:_StartDriver(DRIVER, Drive)
end
