-- [ HEIRLOOMS SOURCE ]-------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end
local ItemKeywords = lib._ItemKeywords
local Native = lib._NativeContract

local Heirlooms = {
    kind = "heirlooms",
    events = { "HEIRLOOMS_UPDATED", { event = "GET_ITEM_INFO_RECEIVED", items = true }, "BAG_UPDATE_DELAYED" },
}

function Heirlooms:GetAvailability()
    return Native.Require(C_Heirloom, "GetHeirloomItemIDs", "PlayerHasHeirloom", "GetHeirloomInfo")
end

function Heirlooms:Build()
    local entries = {}
    local ids = C_Heirloom.GetHeirloomItemIDs()
    if not ids then
        return nil, "pending", "heirloom-list"
    end
    for _, itemID in ipairs(ids) do
        if C_Heirloom.PlayerHasHeirloom(itemID) then
            local name, icon = C_Heirloom.GetHeirloomInfo(itemID)
            if name then
                local keywords, pending = ItemKeywords.Build(itemID)
                if pending then
                    Native.RequestItem(self, itemID)
                end
                local carried = GetItemCount and GetItemCount(itemID) > 0
                entries[#entries + 1] = {
                    kind = "heirlooms",
                    id = itemID,
                    name = name,
                    lowerName = lib.Fold(name .. " " .. keywords),
                    icon = icon,
                    quality = Enum and Enum.ItemQuality and Enum.ItemQuality.Heirloom,
                    passive = not carried,
                    secure = carried and { type = "item", item = tostring(itemID) } or nil,
                }
            else
                Native.RequestItem(self, itemID)
            end
        end
    end
    return entries
end

lib:RegisterIndexSource("heirlooms", Heirlooms)
