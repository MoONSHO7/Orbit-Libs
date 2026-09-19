-- [ PROFESSIONS SOURCE ]-----------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract
local PROFESSION_SLOTS = 6
local Professions = {
    kind = "professions",
    events = { "TRADE_SKILL_LIST_UPDATE", "SKILL_LINES_CHANGED", "SPELLS_CHANGED" },
}

function Professions:GetAvailability()
    local state, reason = Native.Require(_G, "GetProfessions", "GetProfessionInfo")
    if state ~= "ready" then
        return state, reason
    end
    if not Enum or not Enum.SpellBookSpellBank or not Enum.SpellBookSpellBank.Player then
        return "unsupported", "missing:player-spell-bank"
    end
    return Native.Require(C_SpellBook, "GetSpellBookItemInfo")
end

function Professions:Build()
    local entries, seen = {}, {}
    local indices = { GetProfessions() }
    for position = 1, PROFESSION_SLOTS do
        local index = indices[position]
        if index then
            local name, icon, _, _, count, offset, skillLine = GetProfessionInfo(index)
            if name and count and offset and skillLine then
                for slot = 1, count do
                    local spell = C_SpellBook.GetSpellBookItemInfo(offset + slot, Enum.SpellBookSpellBank.Player)
                    if spell and spell.spellID and not spell.isPassive and not seen[spell.spellID] then
                        seen[spell.spellID] = true
                        entries[#entries + 1] = {
                            kind = "professions",
                            id = skillLine .. ":" .. spell.spellID,
                            spellID = spell.spellID,
                            name = spell.name or name,
                            lowerName = lib.Fold(name .. " " .. (spell.name or name)),
                            icon = spell.iconID or icon,
                            secure = { type = "spell", spell = spell.spellID },
                        }
                    end
                end
            end
        end
    end
    return entries
end

lib:RegisterIndexSource("professions", Professions)
