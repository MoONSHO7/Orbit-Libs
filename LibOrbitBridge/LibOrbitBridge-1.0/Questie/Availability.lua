-- [ QUESTIE AVAILABILITY ]---------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitBridge-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local Readable, Number = lib.Readable, lib.Number
-- specialFlags bit 1 marks a repeatable quest; bit 2 is how a quest completes (exploration or event), not availability.
local REPEATABLE_FLAG = 1
-- QuestSort categories whose quests exist only during holidays, as negative zoneOrSort values.
local HOLIDAY_SORTS = {
    [-21] = true,
    [-22] = true,
    [-364] = true,
    [-366] = true,
    [-369] = true,
    [-370] = true,
    [-374] = true,
    [-376] = true,
    [-378] = true,
    [-402] = true,
    [-404] = true,
}
local CLASS_KEYS = { DEATHKNIGHT = "DEATH_KNIGHT", DEMONHUNTER = "DEMON_HUNTER" }
-- Blizzard's own markers for quest rows that were never released or were retired, as they appear in a title.
local RETIRED_MARKS = { "UNUSED", "DEPRECATED", "DEPRICATED", "<NYI>", "<TXT>", "zzOLD", "REUSE" }
local FIELDS = {
    "requiredLevel",
    "questLevel",
    "requiredRaces",
    "requiredClasses",
    "preQuestGroup",
    "preQuestSingle",
    "exclusiveTo",
    "zoneOrSort",
    "requiredSkill",
    "requiredMinRep",
    "requiredMaxRep",
    "nextQuestInChain",
    "specialFlags",
    "parentQuest",
    "breadcrumbForQuestId",
    "breadcrumbs",
    "requiredSpell",
    "requiredSpecialization",
    "requiredMaxLevel",
    "availableUntilCompleted",
    "availableStartingWith",
    "requiredRanks",
    "disabledByQuest",
}

local Questie = lib.Questie
local HasBit = Questie.HasBit

local function Completed(questID)
    return Readable(C_QuestLog.IsQuestFlaggedCompleted(questID)) == true
end

local function InLog(questID)
    return Number(C_QuestLog.GetLogIndexForQuestID(questID)) ~= nil
end

local function AnyDone(list)
    for _, questID in ipairs(list) do
        if Completed(questID) then
            return true
        end
    end
    return false
end

local function AnyInLog(list)
    for _, questID in ipairs(list) do
        if InLog(questID) then
            return true
        end
    end
    return false
end

local function AnyTaken(list)
    for _, questID in ipairs(list) do
        if Completed(questID) or InLog(questID) then
            return true
        end
    end
    return false
end

local function Standing(factionID)
    local data = Readable(C_Reputation.GetFactionDataByID(factionID))
    return type(data) == "table" and Number(data.currentStanding) or 0
end

-- A skill the character never learned has no line, and a client without the reader cannot confirm any.
local function HasSkill(pair)
    local reader = C_SkillInfo and C_SkillInfo.GetSkillLineInfoByID
    local skillID = type(pair) == "table" and Number(pair[1])
    local line = reader and skillID and Readable(reader(skillID))
    local rank = type(line) == "table" and Number(line.rank) or nil
    return rank ~= nil and rank >= (Number(pair[2]) or 0)
end

local function AnySkill(pairs)
    for _, pair in ipairs(pairs) do
        if HasSkill(pair) then
            return true
        end
    end
    return false
end

local function Knows(spellID)
    return Readable(C_SpellBook.IsSpellKnown(spellID)) == true
end

-- Character facts for one collection; verdicts cache in it until the next one. `levelRange` is the consumer's
-- Quest Level Range, and `excluded(questID)`, when given, names quests the player removed in that consumer.
function Questie.Context(index, levelRange, excluded)
    local db = index.lib
    local _, classFile = UnitClass("player")
    local _, _, raceID = UnitRace("player")
    local faction = Readable(UnitFactionGroup("player"))
    classFile = Readable(classFile)
    return {
        lib = db,
        quests = index.quests,
        excluded = excluded,
        level = Number(UnitLevel("player")) or 0,
        levelRange = levelRange,
        raceBit = Number(db.Enum.raceMaskById[Number(raceID)]),
        classBit = type(classFile) == "string" and Number(db.Enum.classKeys[CLASS_KEYS[classFile] or classFile]) or nil,
        factionLetter = faction == "Alliance" and "A" or faction == "Horde" and "H" or nil,
        verdicts = {},
        levels = {},
    }
end

-- The Quest Level Range: a levelled quest further above or below the character than the range stays hidden.
function Questie.InRange(context, level)
    return not (level > 0 and math.abs(context.level - level) > context.levelRange)
end

local function Requirements(context, quest)
    local level = context.level
    if quest.requiredLevel > level or (quest.requiredMaxLevel > 0 and level > quest.requiredMaxLevel) then
        return false
    end
    if quest.requiredRaces > 0 and not HasBit(quest.requiredRaces, context.raceBit) then
        return false
    end
    if quest.requiredClasses > 0 and not HasBit(quest.requiredClasses, context.classBit) then
        return false
    end
    if quest.requiredSkill and not HasSkill(quest.requiredSkill) then
        return false
    end
    if quest.requiredRanks and not AnySkill(quest.requiredRanks) then
        return false
    end
    -- A negative spell is one the character must not know, such as the profession a quest teaches.
    local spell = quest.requiredSpell
    if spell ~= 0 and Knows(math.abs(spell)) ~= (spell > 0) then
        return false
    end
    if quest.requiredSpecialization > 0 and not Knows(quest.requiredSpecialization) then
        return false
    end
    local minRep, maxRep = quest.requiredMinRep, quest.requiredMaxRep
    if minRep and Standing(minRep[1]) < (Number(minRep[2]) or 0) then
        return false
    end
    if maxRep and Standing(maxRep[1]) >= (Number(maxRep[2]) or 0) then
        return false
    end
    return true
end

-- QuestieDB's quest rows never change in a session, so each quest is decoded once; false marks an unknown quest.
local function QuestData(context, questID)
    local quest = context.quests[questID]
    if quest == nil then
        local values = context.lib.Quest.GetAll(questID, FIELDS)
        quest = false
        if type(values) == "table" then
            quest = {}
            for index, field in ipairs(FIELDS) do
                quest[field] = values[index]
            end
        end
        context.quests[questID] = quest
    end
    return quest
end

-- A group prerequisite also counts as done once a quest exclusive to it was done instead; a negative ID is one
-- that has no such alternative.
local function GroupDone(context, list)
    for _, questID in ipairs(list) do
        local required = math.abs(questID)
        if not Completed(required) then
            local alternative = questID > 0 and QuestData(context, required)
            if not (alternative and alternative.exclusiveTo and AnyDone(alternative.exclusiveTo)) then
                return false
            end
        end
    end
    return true
end

local function Chain(context, quest)
    -- A single prerequisite, where a quest has one, stands in for its group.
    if quest.preQuestSingle then
        if not AnyDone(quest.preQuestSingle) then
            return false
        end
    elseif quest.preQuestGroup and not GroupDone(context, quest.preQuestGroup) then
        return false
    end
    -- A breadcrumb in the log leads to this quest, which its giver offers only once that one is handed in.
    if quest.breadcrumbs and AnyInLog(quest.breadcrumbs) then
        return false
    end
    if quest.exclusiveTo and AnyTaken(quest.exclusiveTo) then
        return false
    end
    local next, target = quest.nextQuestInChain, quest.breadcrumbForQuestId
    if (next > 0 and (Completed(next) or InLog(next))) or (target > 0 and (Completed(target) or InLog(target))) then
        return false
    end
    if quest.parentQuest > 0 and not InLog(quest.parentQuest) then
        return false
    end
    if quest.availableUntilCompleted > 0 and Completed(quest.availableUntilCompleted) then
        return false
    end
    local startingWith = quest.availableStartingWith
    if startingWith > 0 and not (InLog(startingWith) or Completed(startingWith)) then
        return false
    end
    return not (quest.disabledByQuest > 0 and InLog(quest.disabledByQuest))
end

local function Marked(name)
    name = Readable(name)
    if type(name) == "string" then
        for _, mark in ipairs(RETIRED_MARKS) do
            if name:find(mark, 1, true) then
                return true
            end
        end
    end
    return false
end

local function Evaluate(context, questID)
    if Questie.IsRetired(questID) or (context.excluded and context.excluded(questID)) then
        return false
    end
    local quest = QuestData(context, questID)
    if not quest then
        return false
    end
    context.levels[questID] = quest.questLevel > 0 and quest.questLevel or nil
    if HOLIDAY_SORTS[quest.zoneOrSort] then
        return false
    end
    if InLog(questID) or (Completed(questID) and not HasBit(quest.specialFlags, REPEATABLE_FLAG)) then
        return false
    end
    if not Requirements(context, quest) or not Chain(context, quest) then
        return false
    end
    if not Questie.InRange(context, quest.questLevel) then
        return false
    end
    return not Marked(context.lib.Quest.name(questID)) and Questie.Exists(questID)
end

function Questie.IsAvailable(context, questID)
    questID = Number(questID)
    if not questID then
        return false
    end
    local verdict = context.verdicts[questID]
    if verdict == nil then
        verdict = Evaluate(context, questID)
        context.verdicts[questID] = verdict
    end
    return verdict
end

-- The quest's own level once IsAvailable has evaluated it; nil for unknown or unlevelled quests.
function Questie.Level(context, questID)
    return context.levels[Number(questID)]
end

-- NPC givers and services serve only the factions QuestieDB marks friendly; objects have no such restriction.
function Questie.Serves(context, record)
    local faction = record.faction
    return faction == nil or (context.factionLetter ~= nil and faction:find(context.factionLetter, 1, true) ~= nil)
end
