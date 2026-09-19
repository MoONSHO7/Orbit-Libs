-- [ EQUIPPED SOURCE ]--------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end
local ItemKeywords = lib._ItemKeywords
local Native = lib._NativeContract

local FIRST_SLOT = 1
local LAST_SLOT = 19

local Equipped = {
    kind = "equipped",
    events = { "PLAYER_EQUIPMENT_CHANGED", "GET_ITEM_INFO_RECEIVED" },
}

function Equipped:GetAvailability()
    return Native.Require(_G, "GetInventoryItemLink", "GetInventoryItemID", "GetItemInfo", "GetInventoryItemTexture")
end

function Equipped:Build()
    local entries = {}
    local firstSlot = type(INVSLOT_AMMO) == "number" and math.min(INVSLOT_AMMO, FIRST_SLOT) or FIRST_SLOT
    for slot = firstSlot, LAST_SLOT do
        local link = GetInventoryItemLink("player", slot)
        if link then
            local name, _, quality, _, _, _, _, _, _, iconPath = GetItemInfo(link)
            local itemID = GetInventoryItemID("player", slot)
            if name and itemID then
                entries[#entries + 1] = {
                    kind = "equipped",
                    id = itemID,
                    name = name,
                    lowerName = lib.Fold(name .. " " .. ItemKeywords.Build(link)),
                    icon = iconPath or GetInventoryItemTexture("player", slot),
                    quality = quality,
                    secure = { type = "item", item = link },
                }
            elseif itemID then
                Native.RequestItem(itemID)
            end
        end
    end
    return entries
end

lib:RegisterIndexSource("equipped", Equipped)
