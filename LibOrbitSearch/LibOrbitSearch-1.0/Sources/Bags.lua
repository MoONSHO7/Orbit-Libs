-- [ BAGS SOURCE ]------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end
local ItemKeywords = lib._ItemKeywords
local Native = lib._NativeContract

local Bags = {
    kind = "bags",
    -- Quest markers follow the quest log, so Blizzard's bags also redraw on these quest events.
    events = { "BAG_UPDATE_DELAYED", "QUEST_ACCEPTED", "UNIT_QUEST_LOG_CHANGED", "GET_ITEM_INFO_RECEIVED" },
}

function Bags:GetAvailability()
    local state, reason = Native.Require(C_Container, "GetContainerNumSlots", "GetContainerItemInfo")
    if state ~= "ready" then
        return state, reason
    end
    if
        not Enum
        or not Enum.BagIndex
        or type(Enum.BagIndex.Backpack) ~= "number"
        or type(NUM_TOTAL_EQUIPPED_BAG_SLOTS) ~= "number"
    then
        return "unsupported", "missing:bag-range"
    end
    return Native.Require(_G, "GetItemInfo", "GetItemCount")
end

local function IsQuestItem(bag, slot)
    if not C_Container.GetContainerItemQuestInfo then
        return false
    end
    local questInfo = C_Container.GetContainerItemQuestInfo(bag, slot)
    return questInfo and (questInfo.questID ~= nil or questInfo.isQuestItem) or false
end

function Bags:Build()
    local entries = {}
    local seen = {}
    local bags = {}
    for bag = Enum.BagIndex.Backpack, NUM_TOTAL_EQUIPPED_BAG_SLOTS do
        bags[#bags + 1] = bag
    end
    if Enum.BagIndex.Keyring and C_ActionBar and C_ActionBar.ShouldShowKeyring and C_ActionBar.ShouldShowKeyring() then
        bags[#bags + 1] = Enum.BagIndex.Keyring
    end
    for _, bag in ipairs(bags) do
        local slots = C_Container.GetContainerNumSlots(bag) or 0
        for slot = 1, slots do
            local info = C_Container.GetContainerItemInfo(bag, slot)
            if info and info.itemID and info.hyperlink and not seen[info.itemID] then
                seen[info.itemID] = true
                local name, _, quality = GetItemInfo(info.hyperlink)
                if not name then
                    Native.RequestItem(info.itemID)
                end
                name = name or info.hyperlink
                entries[#entries + 1] = {
                    kind = "bags",
                    id = info.itemID,
                    name = name,
                    lowerName = lib.Fold(name .. " " .. ItemKeywords.Build(info.hyperlink, IsQuestItem(bag, slot))),
                    icon = info.iconFileID,
                    count = GetItemCount(info.itemID),
                    quality = quality,
                    secure = { type = "item", item = info.hyperlink },
                }
            end
        end
    end
    return entries
end

lib:RegisterIndexSource("bags", Bags)
