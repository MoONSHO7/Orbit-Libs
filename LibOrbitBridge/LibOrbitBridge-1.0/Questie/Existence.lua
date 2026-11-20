-- [ QUESTIE EXISTENCE ]------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitBridge-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local Readable, Number, Text = lib.Readable, lib.Number, lib.Text
local RESULT_EVENT = "QUEST_DATA_LOAD_RESULT"
local BATCH, REQUEST_SECONDS = 8, 0.1
local COALESCE_SECONDS = 0.25
-- No confirmed quest this long after the first request means the client's answers cannot be trusted either way.
local CALIBRATION_SECONDS = 5

local Questie = lib.Questie
lib._questieExistence = lib._questieExistence or { known = {}, asked = {}, queue = {} }
local state = lib._questieExistence

local function Publish()
    if not state.publishing then
        state.publishing = true
        C_Timer.After(COALESCE_SECONDS, function()
            state.publishing = false
            lib:_Fire("QuestieExistenceChanged")
        end)
    end
end

-- A client that never confirms any quest gives no evidence, so its denials stop hiding quests.
local function Calibrate()
    if not state.trusted then
        state.unsupported = true
        Publish()
    end
end

local function Pump()
    state.pumping = false
    for _ = 1, BATCH do
        local questID = table.remove(state.queue)
        if not questID then
            return
        end
        C_QuestLog.RequestLoadQuestByID(questID)
    end
    if #state.queue > 0 then
        state.pumping = true
        C_Timer.After(REQUEST_SECONDS, Pump)
    end
end

local function OnResult(_, questID, success)
    questID = Number(questID)
    if not (questID and state.asked[questID]) then
        return
    end
    local exists = Readable(success) == true
    if state.known[questID] ~= exists then
        state.known[questID] = exists
        state.trusted = state.trusted or exists
        Publish()
    end
end

local function Ask(questID)
    state.asked[questID] = true
    state.queue[#state.queue + 1] = questID
    if not state.listening then
        state.listening = true
        lib:_On(RESULT_EVENT, OnResult)
        C_Timer.After(CALIBRATION_SECONDS, Calibrate)
    end
    if not state.pumping then
        state.pumping = true
        C_Timer.After(REQUEST_SECONDS, Pump)
    end
end

-- QuestieDB lists quests this game version never had. Only the game can say which, so a quest counts once the
-- client holds its data or the server answers for it; one it denies, or has not answered yet, stays hidden.
function Questie.Exists(questID)
    local known = state.known[questID]
    if known == nil and Text(C_QuestLog.GetTitleForQuestID(questID)) then
        state.known[questID], state.trusted, known = true, true, true
    elseif known == nil and not state.asked[questID] then
        Ask(questID)
    end
    return known == true or (state.unsupported == true and not state.trusted)
end
