-- [ SPELLBOOK SOURCE ]-------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract

local Spellbook = {
    kind = "spellbook",
    events = {
        "SPELLS_CHANGED",
        "PLAYER_SPECIALIZATION_CHANGED",
        "UNIT_PET",
        "SKILL_LINES_CHANGED",
        "LEARNED_SPELL_IN_TAB",
    },
}

function Spellbook:GetAvailability()
    if
        not Enum
        or not Enum.SpellBookSpellBank
        or not Enum.SpellBookSpellBank.Player
        or not Enum.SpellBookItemType
        or not Enum.SpellBookItemType.Spell
    then
        return "unsupported", "missing:spellbook-enums"
    end
    local state, reason = Native.Require(C_Spell, "GetSpellTexture")
    if state ~= "ready" then
        return state, reason
    end
    return Native.Require(C_SpellBook, "GetNumSpellBookSkillLines", "GetSpellBookSkillLineInfo", "GetSpellBookItemInfo")
end

local function AppendSpellEntry(entries, name, spellID, passive)
    if not name or not spellID then
        return
    end
    entries[#entries + 1] = {
        kind = "spellbook",
        id = spellID,
        name = name,
        lowerName = lib.Fold(name),
        icon = C_Spell.GetSpellTexture(spellID),
        passive = passive or false,
        secure = { type = "spell", spell = spellID },
    }
end

local function AppendPetSpells(entries)
    if not C_SpellBook.HasPetSpells or not Enum.SpellBookSpellBank.Pet then
        return
    end
    local numPetSpells = C_SpellBook.HasPetSpells()
    if not numPetSpells or numPetSpells <= 0 then
        return
    end
    for slot = 1, numPetSpells do
        local info = C_SpellBook.GetSpellBookItemInfo(slot, Enum.SpellBookSpellBank.Pet)
        if info and info.name and info.itemType == Enum.SpellBookItemType.Spell and info.spellID then
            AppendSpellEntry(entries, info.name, info.spellID, info.isPassive)
        end
    end
end

function Spellbook:Build()
    local entries = {}
    local numLines = C_SpellBook.GetNumSpellBookSkillLines()
    if numLines == nil then
        return nil, "pending", "spellbook-lines"
    end

    for lineIdx = 1, numLines do
        local lineInfo = C_SpellBook.GetSpellBookSkillLineInfo(lineIdx)
        -- shouldHide fences off other specs' trees — never expose non-active-spec abilities.
        if lineInfo and not lineInfo.shouldHide then
            local offset = lineInfo.itemIndexOffset or 0
            local count = lineInfo.numSpellBookItems or 0
            for i = 1, count do
                local slotIndex = offset + i
                local info = C_SpellBook.GetSpellBookItemInfo(slotIndex, Enum.SpellBookSpellBank.Player)
                -- isOffSpec: individual entries within a visible line that belong to a non-active spec.
                if info and info.name and not info.isOffSpec then
                    if info.itemType == Enum.SpellBookItemType.Spell and info.spellID then
                        AppendSpellEntry(entries, info.name, info.spellID, info.isPassive)
                    elseif
                        info.itemType == Enum.SpellBookItemType.Flyout
                        and info.actionID
                        and GetFlyoutInfo
                        and GetFlyoutSlotInfo
                    then
                        local _, _, numSlots, isKnown = GetFlyoutInfo(info.actionID)
                        if isKnown and numSlots then
                            for slot = 1, numSlots do
                                local slotSpellID, _, slotKnown, slotName = GetFlyoutSlotInfo(info.actionID, slot)
                                if slotKnown then
                                    AppendSpellEntry(entries, slotName, slotSpellID, false)
                                end
                            end
                        end
                    end
                end
            end
        end
    end

    AppendPetSpells(entries)
    return entries
end

lib:RegisterIndexSource("spellbook", Spellbook)
