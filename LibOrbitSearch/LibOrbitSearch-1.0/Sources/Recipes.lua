local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract
local Recipes = {
    kind = "recipes",
    events = {
        "TRADE_SKILL_SHOW",
        "TRADE_SKILL_CLOSE",
        "TRADE_SKILL_DATA_SOURCE_CHANGING",
        "TRADE_SKILL_DATA_SOURCE_CHANGED",
        "TRADE_SKILL_LIST_UPDATE",
        "TRADE_SKILL_DETAILS_UPDATE",
        "TRADE_SKILL_NAME_UPDATE",
        "TRADE_SKILL_FAVORITES_CHANGED",
        "NEW_RECIPE_LEARNED",
        "SKILL_LINES_CHANGED",
        { event = "GET_ITEM_INFO_RECEIVED", items = true },
        { event = "ITEM_DATA_LOAD_RESULT", items = true },
    },
}

local function GetProfession()
    local info = C_TradeSkillUI.GetBaseProfessionInfo()
    if info and info.professionID and info.professionID > 0 then
        return info
    end
end

function Recipes:GetAvailability()
    local state, reason = Native.Require(
        C_TradeSkillUI,
        "GetBaseProfessionInfo",
        "GetFilteredRecipeIDs",
        "GetRecipeInfo",
        "IsDataSourceChanging"
    )
    if state ~= "ready" then
        return state, reason
    end
    if C_TradeSkillUI.IsDataSourceChanging() then
        return "pending", "recipe-data-changing"
    end
    if not GetProfession() then
        return "pending", "recipe-profession"
    end
    return "ready"
end

local function OpenRecipe(entry)
    if
        InCombatLockdown()
        or not C_TradeSkillUI
        or not C_TradeSkillUI.OpenRecipe
        or Recipes:GetAvailability() ~= "ready"
    then
        return
    end
    local profession = GetProfession()
    if
        not profession
        or profession.professionID ~= entry.professionID
        or profession.sourceCounter ~= entry.sourceCounter
    then
        return
    end
    C_TradeSkillUI.OpenRecipe(entry.recipeID)
end

local function AppendItemName(terms, itemID, names)
    if not itemID or not C_Item or not C_Item.GetItemNameByID then
        return
    end
    if names[itemID] == nil then
        names[itemID] = C_Item.GetItemNameByID(itemID) or false
        if not names[itemID] then
            Native.RequestItem(Recipes, itemID)
        end
    end
    if names[itemID] then
        terms[#terms + 1] = names[itemID]
    end
end

local function AppendSchematicTerms(terms, info, names)
    if not C_TradeSkillUI.GetRecipeSchematic then
        return
    end
    local schematic = C_TradeSkillUI.GetRecipeSchematic(info.recipeID, info.isRecraft == true)
    if not schematic then
        return
    end
    AppendItemName(terms, schematic.outputItemID, names)
    for _, slot in ipairs(schematic.reagentSlotSchematics) do
        for _, reagent in ipairs(slot.reagents) do
            AppendItemName(terms, reagent.itemID, names)
            if reagent.currencyID and C_CurrencyInfo and C_CurrencyInfo.GetCurrencyInfo then
                local currency = C_CurrencyInfo.GetCurrencyInfo(reagent.currencyID)
                if currency and currency.name then
                    terms[#terms + 1] = currency.name
                end
            end
        end
    end
end

function Recipes:Build()
    local profession = GetProfession()
    if not profession or C_TradeSkillUI.IsDataSourceChanging() then
        return nil, "pending", "recipe-profession"
    end
    local recipeIDs = C_TradeSkillUI.GetFilteredRecipeIDs()
    if not recipeIDs then
        return nil, "pending", "recipe-list"
    end
    local entries, seen, categories, itemNames = {}, {}, {}, {}
    for _, recipeID in ipairs(recipeIDs) do
        local info = C_TradeSkillUI.GetRecipeInfo(recipeID)
        if info and info.name and info.name ~= "" and not seen[info.recipeID] and not info.isDummyRecipe then
            seen[info.recipeID] = true
            local categoryName = ""
            if info.categoryID and C_TradeSkillUI.GetCategoryInfo then
                if categories[info.categoryID] == nil then
                    local category = C_TradeSkillUI.GetCategoryInfo(info.categoryID)
                    categories[info.categoryID] = category and category.name or ""
                end
                categoryName = categories[info.categoryID]
            end
            local stateName = info.learned and PROFESSION_RECIPES_SHOW_LEARNED or PROFESSION_RECIPES_SHOW_UNLEARNED
            local topic = table.concat({ profession.professionName, categoryName, stateName or "" }, " · ")
            local terms = { info.name, topic }
            AppendSchematicTerms(terms, info, itemNames)
            entries[#entries + 1] = {
                kind = "recipes",
                id = info.recipeID,
                recipeID = info.recipeID,
                professionID = profession.professionID,
                sourceCounter = profession.sourceCounter,
                name = info.name,
                lowerName = lib.Fold(table.concat(terms, " ")),
                topic = topic,
                icon = info.icon,
                description = info.disabledReason,
                professionName = profession.professionName,
                categoryName = categoryName,
                learned = info.learned,
                favorite = info.favorite,
                tooltipLink = info.hyperlink,
                onClick = C_TradeSkillUI.OpenRecipe and OpenRecipe or nil,
            }
        end
    end
    return entries
end

lib:RegisterIndexSource("recipes", Recipes)
