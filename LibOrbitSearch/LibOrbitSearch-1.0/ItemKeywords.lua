-- [ ITEM KEYWORDS ]----------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local SLOT_SYNONYM = {
    INVTYPE_FINGER = "ring",
    INVTYPE_NECK = "neck",
    INVTYPE_CLOAK = "cloak",
}
table.freeze(SLOT_SYNONYM)

local ItemKeywords = {}
lib._ItemKeywords = ItemKeywords
lib._itemKeywordTerms = lib._itemKeywordTerms or {}

-- [ TERMS ]------------------------------------------------------------------------------------------------------------
-- Blizzard has no global for these synonyms, so a consumer supplies its localized ring/neck/cloak/reagent/warbound.
function lib:SetItemKeywordTerms(terms)
    self._itemKeywordTerms = terms or {}
    self:InvalidateAll()
end

-- [ BUILD ]------------------------------------------------------------------------------------------------------------
function ItemKeywords.Build(itemRef, isQuestItem)
    local terms = lib._itemKeywordTerms
    local parts = {}
    if _G.ITEMS then
        parts[#parts + 1] = _G.ITEMS
    end
    if isQuestItem and _G.BAG_FILTER_QUEST_ITEMS then
        parts[#parts + 1] = _G.BAG_FILTER_QUEST_ITEMS
    end
    if not itemRef or not GetItemInfo then
        return table.concat(parts, " ")
    end
    local _, _, _, _, _, itemType, itemSubType, _, equipLoc, _, _, _, _, bindType, _, _, isCraftingReagent =
        GetItemInfo(itemRef)
    if not itemType then
        return table.concat(parts, " ")
    end
    parts[#parts + 1] = itemType
    if itemSubType and itemSubType ~= "" and itemSubType ~= itemType then
        parts[#parts + 1] = itemSubType
    end
    if equipLoc and equipLoc ~= "" then
        local slotName = _G[equipLoc]
        if slotName and slotName ~= "" then
            parts[#parts + 1] = slotName
        end
        local synonym = SLOT_SYNONYM[equipLoc] and terms[SLOT_SYNONYM[equipLoc]]
        if synonym then
            parts[#parts + 1] = synonym
        end
    end
    if isCraftingReagent and terms.reagent then
        parts[#parts + 1] = terms.reagent
    end
    local bind = Enum and Enum.ItemBind
    if
        bind
        and bindType
        and (
            bindType == bind.ToWoWAccount
            or bindType == bind.ToBnetAccount
            or bindType == bind.ToBnetAccountUntilEquipped
        )
    then
        if terms.warbound then
            parts[#parts + 1] = terms.warbound
        end
        local accountStr = _G.ITEM_ACCOUNTBOUND
        if accountStr and accountStr ~= "" then
            parts[#parts + 1] = accountStr
        end
    elseif bind and bindType and bindType == bind.OnEquip then
        local boe = _G.ITEM_BIND_ON_EQUIP
        if boe and boe ~= "" then
            parts[#parts + 1] = boe
        end
    end
    return table.concat(parts, " ")
end
