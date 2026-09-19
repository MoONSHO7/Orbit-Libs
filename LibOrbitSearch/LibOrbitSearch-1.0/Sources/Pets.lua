-- [ PETS SOURCE ]------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end
local Native = lib._NativeContract

local Pets = {
    kind = "pets",
    events = { "PET_JOURNAL_LIST_UPDATE", "NEW_PET_ADDED", "COMPANION_UPDATE" },
}

function Pets:GetAvailability()
    return Native.Require(C_PetJournal, "GetOwnedPetIDs", "GetPetInfoByPetID")
end

function Pets:Build()
    local entries = {}
    local petIDs = C_PetJournal.GetOwnedPetIDs()
    if not petIDs then
        return nil, "pending", "pet-list"
    end
    local seenSpecies = {}
    for i = 1, #petIDs do
        local petID = petIDs[i]
        local speciesID, customName, _, _, _, _, isFavorite, name, icon, petType, _, _, _, _, canBattle =
            C_PetJournal.GetPetInfoByPetID(petID)
        if speciesID and name and not seenSpecies[speciesID] then
            seenSpecies[speciesID] = true
            local displayName = customName or name
            local folded = lib.Fold(displayName)
            local familyName = canBattle and petType and _G["BATTLE_PET_NAME_" .. petType]
            if familyName then
                folded = folded .. " " .. lib.Fold(familyName)
            end
            local summonable = C_PetJournal.SummonPetByGUID
                and C_PetJournal.PetIsSummonable
                and C_PetJournal.PetIsSummonable(petID)
            entries[#entries + 1] = {
                kind = "pets",
                id = speciesID,
                petGUID = petID,
                name = displayName,
                lowerName = folded,
                icon = icon,
                favorite = isFavorite or false,
                passive = not summonable,
                secure = summonable
                        and { type = "macro", macrotext = '/run C_PetJournal.SummonPetByGUID("' .. petID .. '")' }
                    or nil,
            }
        end
    end
    return entries
end

lib:RegisterIndexSource("pets", Pets)
