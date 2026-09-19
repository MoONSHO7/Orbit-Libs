-- [ SEARCH ]-----------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Merge = lib._Merge
local Recents = lib._Recents
local IDLookup = lib._IDLookup
local Sessions = lib._ProviderSessions

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local EMPTY = {}
local ALREADY_INDEXED_AS = {
    spell = { "spellbook", "professions" },
    item = { "bags", "equipped", "toys", "heirlooms" },
}
table.freeze(EMPTY)
table.freeze(ALREADY_INDEXED_AS)

local SearchMixin = {}
-- Instances resolve methods through the installed copy, so a newer embedded revision upgrades existing searches.
lib._SearchMeta = lib._SearchMeta or {
    __index = function(_, key)
        return lib._SearchMixin[key]
    end,
}

-- [ CONSTRUCTION ]-----------------------------------------------------------------------------------------------------
function lib:NewSearch(config)
    assert(type(config) == "table" and type(config.kinds) == "table", "LibOrbitSearch: NewSearch needs kinds")
    local priority, rowsByKind = {}, {}
    for _, row in ipairs(config.kinds) do
        assert(type(row.kind) == "string", "LibOrbitSearch: every kind row needs a kind")
        priority[row.kind] = row.priority or 0
        rowsByKind[row.kind] = row
    end
    local search = setmetatable({
        _config = config,
        _rows = config.kinds,
        _rowsByKind = rowsByKind,
        _priority = priority,
        _sessions = {},
    }, lib._SearchMeta)
    self._searches[search] = true
    return search
end

function lib:IsKindIncluded(kind)
    for search in pairs(self._enabledSearches) do
        local row = search._rowsByKind[kind]
        if row and search:IsKindListed(row) and search:IsKindEnabled(row) then
            return true
        end
    end
    return false
end

-- [ LIFECYCLE ]--------------------------------------------------------------------------------------------------------
function SearchMixin:Enable()
    if lib._enabledSearches[self] then
        return
    end
    lib._enabledSearches[self] = true
    lib:_RefreshEventRegistration()
    lib:_Fire("InclusionChanged")
end

function SearchMixin:Disable()
    self:SetOpen(false)
    if not lib._enabledSearches[self] then
        return
    end
    lib._enabledSearches[self] = nil
    lib:_RefreshEventRegistration()
    lib:_Fire("InclusionChanged")
end

function SearchMixin:IsEnabled()
    return lib._enabledSearches[self] == true
end

function SearchMixin:SetOpen(open)
    lib._openSearches[self] = open and true or nil
    if not open then
        self:EndSessions()
    end
end

function SearchMixin:NotifySettingsChanged()
    self:_InvalidateCategoryTokens()
    lib:_RefreshEventRegistration()
    Sessions.Reconcile(self)
    self:_NotifyResultsChanged()
    lib:_Fire("InclusionChanged")
end

function SearchMixin:_NotifyResultsChanged()
    if self._sessionCallback then
        local ok, err = pcall(self._sessionCallback)
        if not ok then
            lib:_Report(err)
        end
    elseif lib._openSearches[self] then
        self:_NotifyIndexUpdated()
    end
end

function SearchMixin:_InvalidateCategoryTokens()
    self._categoryTokens, self._aliasExact, self._keywordOnlyKinds = nil, nil, nil
end

function SearchMixin:_NotifyIndexUpdated()
    local callback = self._config.onIndexUpdated
    if not callback then
        return
    end
    local ok, err = pcall(callback)
    if not ok then
        lib:_Report(err)
    end
end

-- [ KINDS ]------------------------------------------------------------------------------------------------------------
function SearchMixin:GetKinds()
    return self._rows
end

function SearchMixin:GetKindRow(kind)
    return self._rowsByKind[kind]
end

function SearchMixin:GetKindLabel(kind)
    local row = self._rowsByKind[kind]
    if not row then
        return nil
    end
    local getLabel = self._config.GetKindLabel
    if getLabel then
        return getLabel(row)
    end
    return row.label
end

function SearchMixin:IsKindListed(row)
    return not row.provider or lib:IsProviderRegistered(row.kind)
end

function SearchMixin:IsKindEnabled(row)
    local isEnabled = self._config.IsKindEnabled
    return not isEnabled or isEnabled(row) == true
end

function SearchMixin:GetEnabledKinds()
    local enabled = {}
    for _, row in ipairs(self._rows) do
        local available = not row.provider or lib:IsProviderAvailable(row.kind)
        enabled[row.kind] = available and self:IsKindEnabled(row)
    end
    return enabled
end

function SearchMixin:EntryID(entry)
    local row = entry and self._rowsByKind[entry.kind]
    if not row or not row.idSearch then
        return nil
    end
    local id = entry.spellID or entry.id
    return type(id) == "number" and id or nil
end

-- [ INDEX ]------------------------------------------------------------------------------------------------------------
function SearchMixin:EnsureBuilt(enabledKinds)
    return lib:_EnsureKindsBuilt(enabledKinds or self:GetEnabledKinds())
end

function SearchMixin:GetMaster()
    if self._masterRevision == lib._revision then
        return self._master
    end
    local master = {}
    for _, row in ipairs(self._rows) do
        local entries = lib._entries[row.kind]
        if entries then
            for i = 1, #entries do
                master[#master + 1] = entries[i]
            end
        end
    end
    self._master, self._masterRevision = master, lib._revision
    return master
end

-- [ QUERY ]------------------------------------------------------------------------------------------------------------
local function PrependTypedID(search, results, folded, enabledKinds)
    local id = tonumber(folded:match("^%s*(%d+)%s*$"))
    if not id then
        return
    end
    local seen = {}
    for i = 1, #results do
        if search:EntryID(results[i]) == id then
            seen[results[i].kind] = true
        end
    end
    local resolved = IDLookup.Resolve(id, enabledKinds, search._config.IsIDTypeEnabled)
    for i = #resolved, 1, -1 do
        local entry = resolved[i]
        local owned = false
        for _, kind in ipairs(ALREADY_INDEXED_AS[entry.idType]) do
            owned = owned or seen[kind]
        end
        if not owned then
            table.insert(results, 1, entry)
        end
    end
end

function SearchMixin:Query(text, options)
    local start, startKB = lib:_ProfileBegin()
    Sessions.Reconcile(self)
    local enabledKinds = self:GetEnabledKinds()
    self:EnsureBuilt(enabledKinds)
    local recentBoost = self._config.recents and Recents.GetBoostIndex(self._config.recents) or EMPTY
    local results, status = Merge.Run(self, self:GetMaster(), text, enabledKinds, options, recentBoost)
    if not options.scope then
        PrependTypedID(self, results, lib.Fold(text), enabledKinds)
    end
    lib:_ProfileEnd("Search", "Query", start, startKB)
    return results, status
end

function SearchMixin:Recents(limit)
    local store = self._config.recents
    if not store then
        return {}
    end
    local start, startKB = lib:_ProfileBegin()
    local enabledKinds = self:GetEnabledKinds()
    self:EnsureBuilt(enabledKinds)
    local wanted, results = {}, {}
    for index, key in ipairs(Recents.GetRankedKeys(store, limit)) do
        wanted[key] = index
    end
    for _, entry in ipairs(self:GetMaster()) do
        local rank = enabledKinds[entry.kind] and wanted[Recents.MakeKey(entry.kind, entry.id)]
        if rank then
            results[#results + 1] = { entry = entry, rank = rank }
        end
    end
    table.sort(results, function(a, b)
        return a.rank < b.rank
    end)
    local out = {}
    for index = 1, math.min(#results, limit) do
        out[index] = results[index].entry
    end
    lib:_ProfileEnd("Search", "Recents", start, startKB)
    return out
end

function SearchMixin:Record(entry)
    local store = self._config.recents
    if store then
        Recents.Record(store, entry)
    end
end

-- [ PROVIDERS ]--------------------------------------------------------------------------------------------------------
function SearchMixin:BeginSessions(onInvalidate)
    assert(type(onInvalidate) == "function", "LibOrbitSearch: BeginSessions needs an invalidation callback")
    Sessions.Begin(self, onInvalidate)
end

function SearchMixin:EndSessions()
    Sessions.End(self)
end

function SearchMixin:Activate(entry)
    local row = self._rowsByKind[entry.kind]
    if not row or not self:IsKindEnabled(row) then
        return nil
    end
    return Merge.Activate(entry)
end

function SearchMixin:IsEntryCurrent(entry)
    local row = entry and self._rowsByKind[entry.kind]
    if not row or not self:IsKindEnabled(row) then
        return false
    end
    if row.provider then
        return entry.providerOwner == lib:GetProvider(entry.kind) and lib:IsProviderAvailable(entry.kind)
    end
    if entry.kind == "ids" then
        local predicate = self._config.IsIDTypeEnabled
        return IDLookup.IsAvailable(entry.idType) and (not predicate or predicate(entry.idType) == true)
    end
    return lib:IsIndexEntryCurrent(entry)
end

table.freeze(SearchMixin)
lib._SearchMixin = SearchMixin
