-- [ QUESTIE LOG ]------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitBridge-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local Readable, Number, Text = lib.Readable, lib.Number, lib.Text
local COALESCE_SECONDS = 0.25
-- Half a consumer's 60-second refresh, so each backstop collection reads the log again.
local MAX_AGE_SECONDS = 30
-- Without a read for this long no consumer shows the log, so bursts stop reading it.
local IDLE_SECONDS = 90
local FIELD_SEPARATOR, QUEST_SEPARATOR = "\1", "\2"
local PROFILER_LABEL = "Questie.Log"
local CHANGED_COUNT, UNCHANGED_COUNT = "Questie/Log/Changed", "Questie/Log/Unchanged"
-- `true` events arrive in bursts and are coalesced; the rest only make the next read take a fresh snapshot, as
-- consumers that redraw on accept or turn-in hear those events themselves.
local LOG_EVENTS = {
    QUEST_LOG_UPDATE = true,
    QUEST_POI_UPDATE = true,
    QUEST_ACCEPTED = false,
    QUEST_TURNED_IN = false,
    QUEST_REMOVED = false,
    PLAYER_LEVEL_UP = false,
    PLAYER_ENTERING_WORLD = false,
}
local NONE = table.freeze({})

local Questie = lib.Questie
lib._questieLog = lib._questieLog or { stale = true, pending = false, pins = false, usedAt = 0 }
local state = lib._questieLog

local function ByID(first, second)
    return first.id < second.id
end

local function Objectives(questID, parts)
    local rows = Readable(C_QuestLog.GetQuestObjectives(questID))
    local objectives = {}
    for position, row in ipairs(type(rows) == "table" and rows or NONE) do
        row = Readable(row)
        local known = type(row) == "table"
        local objective = {
            text = known and Text(row.text) or nil,
            type = known and Text(row.type) or nil,
            finished = known and Readable(row.finished) == true,
        }
        objectives[position] = objective
        parts[#parts + 1] = (objective.finished and "+" or "-") .. (objective.type or "") .. (objective.text or "")
    end
    return objectives
end

local function Take()
    local quests, byID, parts = {}, {}, {}
    for position = 1, Number(C_QuestLog.GetNumQuestLogEntries()) or 0 do
        local info = Readable(C_QuestLog.GetInfo(position))
        local questID = type(info) == "table" and Number(info.questID)
        if questID and questID > 0 and Readable(info.isHeader) ~= true and Readable(info.isHidden) ~= true then
            local title = Text(info.title) or Text(state.db.Quest.name(questID))
            local level = Number(info.level)
            level = level and level > 0 and level or nil
            local complete = Readable(C_QuestLog.IsComplete(questID)) == true
                or Readable(C_QuestLog.ReadyForTurnIn(questID)) == true
            local failed = Readable(C_QuestLog.IsFailed(questID)) == true
            parts[#parts + 1] = QUEST_SEPARATOR
                .. questID
                .. (failed and "f" or complete and "c" or "-")
                .. (level or 0)
                .. (title or "")
            local quest = {
                id = questID,
                title = title,
                level = level,
                complete = complete,
                failed = failed,
                objectives = Objectives(questID, parts),
            }
            quests[#quests + 1], byID[questID] = quest, quest
        end
    end
    table.sort(quests, ByID)
    local faction = Readable(UnitFactionGroup("player"))
    local snapshot = {
        quests = quests,
        byID = byID,
        signature = table.concat(parts, FIELD_SEPARATOR),
        factionLetter = faction == "Alliance" and "A" or faction == "Horde" and "H" or nil,
        readAt = GetTime(),
    }
    state.snapshot, state.stale = snapshot, false
    return snapshot
end

-- A burst only changes consumers' rows when the log itself did, or the client moved a pin: a turn-in is matched
-- to its quest's pin, so any quest in the log can depend on one.
local function Refresh()
    local before, pins = state.snapshot, state.pins
    state.pending, state.pins = false, false
    local start, startKB = lib:_ProfileBegin()
    local snapshot = Take()
    local changed = not before or before.signature ~= snapshot.signature or pins and #snapshot.quests > 0
    lib:_ProfileEnd(PROFILER_LABEL, start, startKB)
    lib:_Count(changed and CHANGED_COUNT or UNCHANGED_COUNT)
    if changed then
        lib:_Fire("QuestieLogChanged")
    end
end

local function OnLogEvent(event)
    local burst = LOG_EVENTS[event]
    if not burst or GetTime() - state.usedAt >= IDLE_SECONDS then
        state.stale = true
        return
    end
    state.pins = state.pins or event == "QUEST_POI_UPDATE"
    if not state.pending then
        state.pending = true
        C_Timer.After(COALESCE_SECONDS, Refresh)
    end
end

-- The quest log as one snapshot, read again when an event made it stale or it aged; reading keeps bursts coalesced.
function Questie.ReadLog(db)
    if not state.listening then
        state.listening = true
        for event in pairs(LOG_EVENTS) do
            lib:_On(event, OnLogEvent)
        end
    end
    local now = GetTime()
    state.db, state.usedAt = db, now
    local snapshot = state.snapshot
    if state.stale or not snapshot or now - snapshot.readAt >= MAX_AGE_SECONDS then
        snapshot = Take()
    end
    return snapshot
end
