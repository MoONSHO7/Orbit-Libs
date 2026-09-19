-- [ MERGE ]------------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Matcher = lib._Matcher

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local PROFILER_GROUP = "Search/Provider"
local RAW_WORD_PATTERN = "[^\t\n\r ]+"
local PROVIDER_BAND_OFFSET = 0.5

local Merge = {}
lib._Merge = Merge

-- [ PROVIDER QUERY ]---------------------------------------------------------------------------------------------------
-- Fold lowercases bytes only; providers own UTF-8-safe folding, so they receive the raw words.
local function ProviderText(rawText, parsed, kind)
    if parsed.kindFilter ~= kind then
        return rawText
    end
    local rawWords = {}
    for word in rawText:gmatch(RAW_WORD_PATTERN) do
        rawWords[#rawWords + 1] = word
    end
    if #rawWords ~= #parsed.words then
        return rawText
    end
    local rest = {}
    for index, word in ipairs(rawWords) do
        if not parsed.consumed[index] then
            rest[#rest + 1] = word
        end
    end
    return table.concat(rest, " ")
end

local function BuildEntry(session, record)
    local ok, presentation = lib:_CallProviderOwner(session.providerOwner, session.providerKey, "Present", record)
    if not ok or type(presentation) ~= "table" or type(presentation.name) ~= "string" then
        return nil
    end
    return {
        kind = session.kind,
        provider = true,
        providerOwner = session.providerOwner,
        id = record.id,
        name = presentation.name,
        lowerName = lib.Fold(presentation.name),
        detail = presentation.detail,
        atlas = presentation.atlas,
        texture = presentation.texture,
        texCoords = presentation.texCoords,
        vertexColor = presentation.vertexColor,
        tier = record.tier,
        record = record,
    }
end

local function QueryProvider(search, kind, text, options, scoped)
    local session = search._sessions[kind]
    if not session or not session.open or not session.ready then
        return {}, nil
    end
    local start, startKB = lib:_ProfileBegin()
    local query = { text = text, fuzzy = options.fuzzy, limit = options.maxResults, scoped = scoped }
    local ok, records, status =
        lib:_CallProviderOwner(session.providerOwner, session.providerKey, "Query", session, query)
    local entries = {}
    if ok and type(records) == "table" then
        for index = 1, math.min(#records, options.maxResults) do
            if not session.open then
                break
            end
            local entry = BuildEntry(session, records[index])
            if entry and session.open then
                entries[#entries + 1] = entry
            end
        end
    end
    lib:_ProfileEnd(PROFILER_GROUP, kind, start, startKB)
    return entries, ok and type(status) == "string" and status or nil
end

local function QueryProviders(search, rawText, parsed, enabledKinds, options)
    local entries, status = {}, nil
    if parsed.digits then
        return entries, status
    end
    for _, row in ipairs(search._rows) do
        if row.provider and enabledKinds[row.kind] and (not parsed.kindFilter or parsed.kindFilter == row.kind) then
            local found, kindStatus =
                QueryProvider(search, row.kind, ProviderText(rawText, parsed, row.kind), options, false)
            for _, entry in ipairs(found) do
                entries[#entries + 1] = entry
            end
            status = status or kindStatus
        end
    end
    return entries, status
end

-- [ MERGE ]------------------------------------------------------------------------------------------------------------
local function MergeResults(search, localEntries, localTiers, providerEntries, maxResults)
    local priority = search._priority
    local providerPriorities = {}
    for _, entry in ipairs(providerEntries) do
        providerPriorities[priority[entry.kind] or 0] = true
    end
    local function Band(kindPriority, isProvider)
        local band = isProvider and PROVIDER_BAND_OFFSET or 0
        for providerPriority in pairs(providerPriorities) do
            if providerPriority > kindPriority then
                band = band + 1
            end
        end
        return band
    end
    local items = {}
    for index, entry in ipairs(localEntries) do
        local band = Band(priority[entry.kind] or 0, false)
        items[#items + 1] = { entry = entry, tier = localTiers[index] or 0, band = band, order = index }
    end
    for index, entry in ipairs(providerEntries) do
        local band = Band(priority[entry.kind] or 0, true)
        items[#items + 1] = { entry = entry, tier = entry.tier or 0, band = band, order = index }
    end
    table.sort(items, function(a, b)
        if a.tier ~= b.tier then
            return a.tier > b.tier
        end
        if a.band ~= b.band then
            return a.band < b.band
        end
        return a.order < b.order
    end)
    local out = {}
    for index = 1, math.min(#items, maxResults) do
        out[index] = items[index].entry
    end
    return out
end

function Merge.Run(search, master, rawText, enabledKinds, options, recentBoost)
    local folded = lib.Fold(rawText)
    if options.scope then
        local parsed = Matcher.Parse(search, folded, true)
        if parsed.digits or not enabledKinds[options.scope] then
            return {}, nil
        end
        return QueryProvider(search, options.scope, rawText, options, true)
    end
    local parsed = Matcher.Parse(search, folded)
    local found, tiers = Matcher.Query(search, master, parsed, enabledKinds, options, recentBoost)
    local provided, status = QueryProviders(search, rawText, parsed, enabledKinds, options)
    if parsed.partial and #found == 0 and #provided == 0 then
        parsed = Matcher.Parse(search, folded, true)
        found, tiers = Matcher.Query(search, master, parsed, enabledKinds, options, recentBoost)
        provided, status = QueryProviders(search, rawText, parsed, enabledKinds, options)
    end
    if #provided == 0 then
        return found, status
    end
    return MergeResults(search, found, tiers, provided, options.maxResults), status
end

-- [ ACTIVATION ]-------------------------------------------------------------------------------------------------------
function Merge.Activate(entry)
    if
        (entry.providerOwner and entry.providerOwner ~= lib:GetProvider(entry.kind))
        or not lib:IsProviderAvailable(entry.kind)
    then
        return nil
    end
    local ok, outcome = lib:CallProvider(entry.kind, "Activate", entry.record)
    if not ok or type(outcome) ~= "table" then
        return nil
    end
    return outcome
end
