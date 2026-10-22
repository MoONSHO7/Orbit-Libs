-- [ PETS SOURCE ]------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end
local Native = lib._NativeContract

local Pets = {
    kind = "pets",
    events = {
        "PET_JOURNAL_LIST_UPDATE",
        "PET_JOURNAL_PET_DELETED",
        "NEW_PET_ADDED",
        { event = "COMPANION_UPDATE", unit = "CRITTER" },
    },
}

function Pets:GetAvailability()
    return Native.Require(C_PetJournal, "GetOwnedPetIDs", "GetPetInfoByPetID")
end

local function AddAlias(group, name)
    if name and name ~= "" and not group.aliases[name] then
        group.aliases[name] = true
        group.terms[#group.terms + 1] = name
    end
end

local function PreferPet(group, petID, summonable, favorite)
    if not group.petGUID then
        return true
    end
    if group.summonable ~= summonable then
        return summonable
    end
    if group.petFavorite ~= favorite then
        return favorite
    end
    return petID < group.petGUID
end

function Pets:Build()
    local entries, groups, bySpecies = {}, {}, {}
    local petIDs = C_PetJournal.GetOwnedPetIDs()
    if not petIDs then
        return nil, "pending", "pet-list"
    end
    for i = 1, #petIDs do
        local petID = petIDs[i]
        local speciesID, customName, _, _, _, _, isFavorite, name, icon, petType, _, _, _, _, canBattle =
            C_PetJournal.GetPetInfoByPetID(petID)
        if speciesID and name then
            local group = bySpecies[speciesID]
            if not group then
                group = { speciesID = speciesID, aliases = {}, terms = {} }
                bySpecies[speciesID] = group
                groups[#groups + 1] = group
            end
            AddAlias(group, name)
            AddAlias(group, customName)
            local familyName = canBattle and petType and _G["BATTLE_PET_NAME_" .. petType]
            AddAlias(group, familyName)
            local summonable = C_PetJournal.SummonPetByGUID
                    and C_PetJournal.PetIsSummonable
                    and C_PetJournal.PetIsSummonable(petID)
                or false
            local favorite = isFavorite or false
            if PreferPet(group, petID, summonable, favorite) then
                group.petGUID = petID
                group.name = customName and customName ~= "" and customName or name
                group.icon = icon
                group.summonable = summonable
                group.petFavorite = favorite
            end
        end
    end
    for _, group in ipairs(groups) do
        entries[#entries + 1] = {
            kind = "pets",
            id = group.speciesID,
            petGUID = group.petGUID,
            name = group.name,
            lowerName = lib.Fold(table.concat(group.terms, " ")),
            icon = group.icon,
            favorite = group.petFavorite,
            passive = not group.summonable,
            secure = group.summonable
                    and { type = "macro", macrotext = '/run C_PetJournal.SummonPetByGUID("' .. group.petGUID .. '")' }
                or nil,
        }
    end
    return entries
end

lib:RegisterIndexSource("pets", Pets)
