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
        { event = "PLAYER_SPECIALIZATION_CHANGED", unit = "player" },
        { event = "UNIT_PET", unit = "player" },
        "PET_BAR_UPDATE",
        "PET_UI_UPDATE",
        "UPDATE_VEHICLE_ACTIONBAR",
        "SKILL_LINES_CHANGED",
        "LEARNED_SPELL_IN_TAB",
        "SPELL_TEXT_UPDATE",
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

local function AppendSpellEntry(entries, name, spellID, passive, subName)
    if not name or not spellID then
        return
    end
    local hasSubName = subName and subName ~= ""
    entries[#entries + 1] = {
        kind = "spellbook",
        id = spellID,
        spellID = spellID,
        name = hasSubName and name .. " (" .. subName .. ")" or name,
        lowerName = lib.Fold(hasSubName and name .. " " .. subName or name),
        subName = subName,
        icon = C_Spell.GetSpellTexture(spellID),
        passive = passive or false,
        secure = { type = "spell", spell = spellID },
    }
end

local function OpenPetSpellbook()
    if
        PlayerSpellsUtil
        and PlayerSpellsUtil.OpenToSpellBookTabAtCategory
        and PlayerSpellsUtil.SpellBookCategories
        and PlayerSpellsUtil.SpellBookCategories.Pet
    then
        PlayerSpellsUtil:OpenToSpellBookTabAtCategory(PlayerSpellsUtil.SpellBookCategories.Pet)
    end
end

local function GetPetBarSlot(actionID)
    if not C_ActionBar or not C_ActionBar.GetPetActionPetBarIndices or not CastPetAction then
        return nil
    end
    local slots
    -- Forever's default also searches gamepad possess slots; secure pet actions use the ordinary pet bar.
    if Enum.ActionBarSet and Enum.ActionBarSet.Mkb then
        slots = C_ActionBar.GetPetActionPetBarIndices(actionID, Enum.ActionBarSet.Mkb)
    else
        slots = C_ActionBar.GetPetActionPetBarIndices(actionID)
    end
    return slots and slots[1]
end

local function AppendPetAction(entries, info, slot)
    if not info.actionID then
        return
    end
    local actionSlot = GetPetBarSlot(info.actionID)
    entries[#entries + 1] = {
        kind = "spellbook",
        id = "petaction:" .. info.actionID,
        petActionID = info.actionID,
        spellBookSlot = slot,
        spellBookBank = Enum.SpellBookSpellBank.Pet,
        name = info.name,
        lowerName = lib.Fold(info.name),
        icon = info.iconID,
        secure = actionSlot and { type = "pet", action = actionSlot } or nil,
        onClick = not actionSlot and OpenPetSpellbook or nil,
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
        if info and info.name then
            if info.itemType == Enum.SpellBookItemType.Spell and info.spellID then
                AppendSpellEntry(entries, info.name, info.spellID, info.isPassive, info.subName)
            elseif info.itemType == Enum.SpellBookItemType.PetAction then
                AppendPetAction(entries, info, slot)
            end
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
                        AppendSpellEntry(entries, info.name, info.spellID, info.isPassive, info.subName)
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
                                    local subName = C_Spell.GetSpellSubtext and C_Spell.GetSpellSubtext(slotSpellID)
                                    AppendSpellEntry(entries, slotName, slotSpellID, false, subName)
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
