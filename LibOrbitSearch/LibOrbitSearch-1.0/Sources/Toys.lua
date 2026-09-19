-- [ TOYS SOURCE ]------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end
local Native = lib._NativeContract

local Toys = {
    kind = "toys",
    events = { "TOYS_UPDATED", "GET_ITEM_INFO_RECEIVED" },
}

function Toys:GetAvailability()
    local state, reason = Native.Require(_G, "PlayerHasToy")
    if state ~= "ready" then
        return state, reason
    end
    return Native.Require(C_ToyBox, "GetNumFilteredToys", "GetToyFromIndex", "GetToyInfo")
end

function Toys:Build()
    local entries = {}
    -- GetToyFromIndex uses the filtered list, so pair it with GetNumFilteredToys.
    local count = C_ToyBox.GetNumFilteredToys()
    if count == nil then
        return nil, "pending", "toy-list"
    end
    for i = 1, count do
        local itemID = C_ToyBox.GetToyFromIndex(i)
        if itemID and itemID > 0 and PlayerHasToy(itemID) then
            local _, toyName, iconID = C_ToyBox.GetToyInfo(itemID)
            if toyName then
                entries[#entries + 1] = {
                    kind = "toys",
                    id = itemID,
                    name = toyName,
                    lowerName = lib.Fold(toyName),
                    icon = iconID,
                    favorite = C_ToyBox.GetIsFavorite and C_ToyBox.GetIsFavorite(itemID) or false,
                    secure = { type = "macro", macrotext = "/use item:" .. itemID },
                }
            else
                Native.RequestItem(itemID)
            end
        end
    end
    return entries
end

lib:RegisterIndexSource("toys", Toys)
