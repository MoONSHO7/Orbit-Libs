-- [ REGISTRY ]---------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local REQUIRED_PROVIDER_FUNCTIONS = { "IsAvailable", "BeginSession", "EndSession", "Query", "Present", "Activate" }
table.freeze(REQUIRED_PROVIDER_FUNCTIONS)

lib._indexSources = lib._indexSources or {}
lib._providers = lib._providers or {}
lib._providerKeyByKind = lib._providerKeyByKind or {}

-- [ INDEX SOURCES ]----------------------------------------------------------------------------------------------------
function lib:RegisterIndexSource(kind, source)
    assert(type(kind) == "string", "LibOrbitSearch: index source kind must be a string")
    assert(type(source) == "table" and type(source.Build) == "function", "LibOrbitSearch: index source needs Build")
    assert(source.GetAvailability == nil or type(source.GetAvailability) == "function", "Invalid GetAvailability")
    assert(not self._providerKeyByKind[kind], "LibOrbitSearch: kind already belongs to a provider: " .. kind)
    self._indexSources[kind] = source
    self:_ForgetKind(kind)
    self:_RefreshEventRegistration()
    self:_NotifySourcesChanged()
end

function lib:UnregisterIndexSource(kind)
    if not self._indexSources[kind] then
        return
    end
    self._indexSources[kind] = nil
    self:_ForgetKind(kind)
    self:_RefreshEventRegistration()
    self:_NotifySourcesChanged()
end

function lib:IsIndexSourceRegistered(kind)
    return self._indexSources[kind] ~= nil
end

function lib:NotifyIndexSourceChanged(kind)
    if not self._indexSources[kind] then
        return
    end
    self:MarkDirty(kind)
    self:_RefreshEventRegistration()
    for search in pairs(self._enabledSearches) do
        local row = search._rowsByKind[kind]
        if row and search:IsKindEnabled(row) then
            search:_NotifyResultsChanged()
        end
    end
end

-- [ PROVIDERS ]--------------------------------------------------------------------------------------------------------
function lib:RegisterProvider(key, provider)
    if type(key) ~= "string" or type(provider) ~= "table" then
        return false, "invalid"
    end
    if provider.contract ~= self.PROVIDER_CONTRACT then
        return false, "contract"
    end
    for _, name in ipairs(REQUIRED_PROVIDER_FUNCTIONS) do
        if type(provider[name]) ~= "function" then
            return false, "missing:" .. name
        end
    end
    if type(provider.kind) ~= "string" or self._indexSources[provider.kind] then
        return false, "kind"
    end
    local owner = self._providerKeyByKind[provider.kind]
    if owner and owner ~= key then
        return false, "duplicate"
    end
    local previous = self._providers[key]
    if previous and previous.kind ~= provider.kind then
        self._providerKeyByKind[previous.kind] = nil
    end
    self._providers[key] = provider
    self._providerKeyByKind[provider.kind] = key
    self:_NotifySourcesChanged()
    return true
end

function lib:UnregisterProvider(key)
    local provider = self._providers[key]
    if not provider then
        return false
    end
    self._providers[key] = nil
    self._providerKeyByKind[provider.kind] = nil
    self:_NotifySourcesChanged()
    return true
end

function lib:GetProvider(kind)
    local key = self._providerKeyByKind[kind]
    return key and self._providers[key], key
end

function lib:IsProviderRegistered(kind)
    return self._providerKeyByKind[kind] ~= nil
end

function lib:CallProvider(kind, method, ...)
    local provider, key = self:GetProvider(kind)
    if not provider then
        return false
    end
    return self:_CallProviderOwner(provider, key, method, ...)
end

function lib:_CallProviderOwner(provider, key, method, ...)
    local start, startKB
    if method == "BeginSession" or method == "EndSession" or method == "Activate" then
        start, startKB = self:_ProfileBegin()
    end
    local results = { pcall(provider[method], ...) }
    if start then
        self:_ProfileEnd("Search/Provider", key .. "." .. method, start, startKB)
    end
    if not results[1] then
        self:_Report(key .. "." .. method .. ": " .. tostring(results[2]))
        return false
    end
    return true, results[2], results[3]
end

function lib:IsProviderAvailable(kind)
    local ok, available = self:CallProvider(kind, "IsAvailable")
    return ok and available == true
end

function lib:_NotifySourcesChanged()
    if self.__building then
        return
    end
    for search in pairs(self._searches) do
        search:_InvalidateCategoryTokens()
        self._ProviderSessions.Reconcile(search)
    end
    for search in pairs(self._searches) do
        search:_NotifyResultsChanged()
    end
    self:_Fire("SourcesChanged")
    self:_Fire("InclusionChanged")
end

function lib:NotifyProviderChanged(key)
    if self._providers[key] then
        self:_NotifySourcesChanged()
    end
end
