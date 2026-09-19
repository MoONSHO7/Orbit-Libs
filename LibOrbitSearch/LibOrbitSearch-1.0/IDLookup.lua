-- [ ID LOOKUP ]--------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local MAX_ID = 10000000
local CACHE_SIZE = 256
local PENDING_SIZE = 256
local ID_KIND = "ids"
local SPELL_ID_TYPE = "spell"
local ITEM_ID_TYPE = "item"
local REQUEST_TIMEOUT = 30
local WAKE_EVENTS = { "ADDON_LOADED", "PLAYER_ENTERING_WORLD" }
local Native = lib._NativeContract

local Create = lib._BoundedCache.Create
lib._idCaches = lib._idCaches
    or {
        spell = Create(CACHE_SIZE),
        item = Create(CACHE_SIZE),
        spellPending = Create(PENDING_SIZE),
        itemPending = Create(PENDING_SIZE),
    }
lib._idFrame = lib._idFrame or CreateFrame("Frame")

local Lookup = {}
lib._IDLookup = Lookup

function Lookup.IsAvailable(idType)
    if idType == SPELL_ID_TYPE then
        return Native.Require(C_Spell, "GetSpellName", "GetSpellTexture", "IsSpellDataCached", "RequestLoadSpellData")
                == "ready"
            and Native.IsEventValid("SPELL_DATA_LOAD_RESULT")
    elseif idType == ITEM_ID_TYPE then
        return Native.Require(
            C_Item,
            "GetItemNameByID",
            "GetItemIconByID",
            "GetItemQualityByID",
            "IsItemDataCachedByID",
            "RequestLoadItemDataByID"
        ) == "ready" and Native.IsEventValid("GET_ITEM_INFO_RECEIVED")
    end
    return false
end

local function IncludesType(search, idType)
    local row = search._rowsByKind[ID_KIND]
    local predicate = search._config.IsIDTypeEnabled
    return row and search:IsKindEnabled(row) and (not predicate or predicate(idType) == true)
end

function Lookup.RefreshEvents()
    local frame, caches = lib._idFrame, lib._idCaches
    frame:UnregisterAllEvents()
    local spell, item = false, false
    for search in pairs(lib._enabledSearches) do
        spell = spell or IncludesType(search, SPELL_ID_TYPE)
        item = item or IncludesType(search, ITEM_ID_TYPE)
    end
    if spell or item then
        for _, event in ipairs(WAKE_EVENTS) do
            if Native.IsEventValid(event) then
                frame:RegisterEvent(event)
            end
        end
    end
    if spell and Lookup.IsAvailable(SPELL_ID_TYPE) then
        frame:RegisterEvent("SPELL_DATA_LOAD_RESULT")
    else
        caches.spellPending = Create(PENDING_SIZE)
    end
    if item and Lookup.IsAvailable(ITEM_ID_TYPE) then
        frame:RegisterEvent("GET_ITEM_INFO_RECEIVED")
    else
        caches.itemPending = Create(PENDING_SIZE)
    end
end

-- [ BUILD ]------------------------------------------------------------------------------------------------------------
local function BuildSpell(spellID)
    local name = C_Spell.GetSpellName(spellID)
    if not name or name == "" then
        return nil
    end
    return {
        kind = ID_KIND,
        idType = SPELL_ID_TYPE,
        id = spellID,
        name = name,
        lowerName = lib.Fold(name),
        icon = C_Spell.GetSpellTexture(spellID),
        keepOpen = true,
    }
end

local function BuildItem(itemID)
    local name = C_Item.GetItemNameByID(itemID)
    if not name or name == "" then
        return nil
    end
    return {
        kind = ID_KIND,
        idType = ITEM_ID_TYPE,
        id = itemID,
        name = name,
        lowerName = lib.Fold(name),
        icon = C_Item.GetItemIconByID(itemID),
        quality = C_Item.GetItemQualityByID(itemID),
        keepOpen = true,
    }
end

-- [ RESOLVE ]----------------------------------------------------------------------------------------------------------
-- An uncached id has no name and its existence check can answer false, so the load request is the only test.
local function ResolveCached(id, cache, pending, isCached, request, build)
    local cached = cache:Get(id)
    if cached ~= nil then
        return cached or nil
    end
    if isCached(id) then
        local entry = build(id)
        cache:Set(id, entry or false)
        return entry
    end
    local requested = pending:Get(id)
    if type(requested) ~= "number" or time() - requested >= REQUEST_TIMEOUT then
        pending:Set(id, time())
        request(id)
    end
    return nil
end

function Lookup.Resolve(id, enabledKinds, isTypeEnabled)
    local out = {}
    if not enabledKinds[ID_KIND] or type(id) ~= "number" or id % 1 ~= 0 or id <= 0 or id > MAX_ID then
        return out
    end
    local caches = lib._idCaches
    local spell = Lookup.IsAvailable(SPELL_ID_TYPE)
        and (not isTypeEnabled or isTypeEnabled(SPELL_ID_TYPE))
        and ResolveCached(
            id,
            caches.spell,
            caches.spellPending,
            C_Spell.IsSpellDataCached,
            C_Spell.RequestLoadSpellData,
            BuildSpell
        )
    if spell then
        out[#out + 1] = spell
    end
    local item = Lookup.IsAvailable(ITEM_ID_TYPE)
        and (not isTypeEnabled or isTypeEnabled(ITEM_ID_TYPE))
        and ResolveCached(
            id,
            caches.item,
            caches.itemPending,
            C_Item.IsItemDataCachedByID,
            C_Item.RequestLoadItemDataByID,
            BuildItem
        )
    if item then
        out[#out + 1] = item
    end
    return out
end

-- [ EVENTS ]-----------------------------------------------------------------------------------------------------------
local function OnLoadResult(cache, pending, build, idType, id, success)
    if not pending:Get(id) then
        return
    end
    pending:Remove(id)
    local entry = success and build(id) or nil
    cache:Set(id, entry or false)
    if entry then
        for search in pairs(lib._openSearches) do
            if lib._enabledSearches[search] and IncludesType(search, idType) then
                search:_NotifyIndexUpdated()
            end
        end
    end
end

lib._idFrame:SetScript("OnEvent", function(_, event, id, success)
    if event == "ADDON_LOADED" or event == "PLAYER_ENTERING_WORLD" then
        Lookup.RefreshEvents()
        for search in pairs(lib._openSearches) do
            if
                lib._enabledSearches[search]
                and (IncludesType(search, SPELL_ID_TYPE) or IncludesType(search, ITEM_ID_TYPE))
            then
                search:_NotifyIndexUpdated()
            end
        end
        return
    end
    local caches = lib._idCaches
    if event == "SPELL_DATA_LOAD_RESULT" then
        OnLoadResult(caches.spell, caches.spellPending, BuildSpell, SPELL_ID_TYPE, id, success)
    else
        OnLoadResult(caches.item, caches.itemPending, BuildItem, ITEM_ID_TYPE, id, success)
    end
end)
