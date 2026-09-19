-- [ INDEX MANAGER ]----------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local REBUILD_DELAY = 0.5
local PROFILER_GROUP = "Search/Index"
local WAKE_EVENTS = { "ADDON_LOADED", "PLAYER_ENTERING_WORLD" }
local EMPTY = {}
table.freeze(EMPTY)
table.freeze(WAKE_EVENTS)
local Native = lib._NativeContract

lib._entries = lib._entries or {}
lib._dirty = lib._dirty or {}
lib._built = lib._built or {}
lib._buildErrors = lib._buildErrors or {}
lib._buildCounts = lib._buildCounts or {}
lib._revision = lib._revision or 0
lib._kindRevisions = lib._kindRevisions or {}
lib._pendingRebuildKinds = lib._pendingRebuildKinds or {}
lib._eventFrame = lib._eventFrame or CreateFrame("Frame")
lib._sourceStates = lib._sourceStates or {}
lib._entryOwners = lib._entryOwners or setmetatable({}, { __mode = "k" })
lib._eventKinds = {}
lib._buildingKinds = {}
for kind in pairs(lib._built) do
    if not lib._sourceStates[kind] then
        lib._dirty[kind] = true
    end
end

local function AdvanceRevision(kind)
    lib._revision = lib._revision + 1
    lib._kindRevisions[kind] = (lib._kindRevisions[kind] or 0) + 1
end

local function ProbeSource(kind, source)
    if not source.GetAvailability then
        return "ready"
    end
    local ok, state, reason = pcall(source.GetAvailability, source)
    if ok and (state == "ready" or state == "pending" or state == "unsupported") then
        return state, reason
    end
    local message = ok and "invalid-availability" or tostring(state)
    if lib._buildErrors[kind] ~= message then
        lib:_Report(kind .. ".GetAvailability: " .. message)
    end
    lib._buildErrors[kind] = message
    return "failed", message
end

local function RetireKind(kind, state, reason, blocked)
    local previous = lib._sourceStates[kind]
    if not previous or previous.state ~= state or previous.reason ~= reason or lib._entries[kind] ~= EMPTY then
        AdvanceRevision(kind)
    end
    lib._entries[kind] = EMPTY
    lib._buildCounts[kind] = 0
    lib._sourceStates[kind] = { state = state, reason = reason, blocked = blocked }
end

function lib:GetIndexSourceState(kind)
    local source = self._indexSources[kind]
    if not source then
        return "unsupported", "unregistered"
    end
    local state, reason = ProbeSource(kind, source)
    if state ~= "ready" then
        RetireKind(kind, state, reason, true)
        self._built[kind], self._dirty[kind] = true, nil
        return state, reason
    end
    local previous = self._sourceStates[kind]
    if previous and previous.blocked then
        self._dirty[kind] = true
    end
    if previous and not previous.blocked then
        return previous.state, previous.reason
    end
    return "pending", "not-built"
end

-- [ EVENTS ]-----------------------------------------------------------------------------------------------------------
lib._eventFrame:SetScript("OnEvent", function(_, event)
    local kinds = lib._eventKinds[event] or EMPTY
    for kind in pairs(kinds) do
        lib:MarkDirty(kind)
    end
    lib:_RefreshEventRegistration()
end)

function lib:_RefreshEventRegistration()
    if self.__building then
        return
    end
    local frame = self._eventFrame
    frame:UnregisterAllEvents()
    self._eventKinds = {}
    local function Include(kind, events)
        for _, event in ipairs(events) do
            if Native.IsEventValid(event) then
                local kinds = self._eventKinds[event]
                if not kinds then
                    kinds = {}
                    self._eventKinds[event] = kinds
                    frame:RegisterEvent(event)
                end
                kinds[kind] = true
            end
        end
    end
    for kind, source in pairs(self._indexSources) do
        if self:IsKindIncluded(kind) then
            local state = ProbeSource(kind, source)
            if state == "ready" or state == "pending" then
                Include(kind, source.events or EMPTY)
            end
            if source.GetAvailability then
                Include(kind, source.wakeEvents or WAKE_EVENTS)
            end
        end
    end
    self._IDLookup.RefreshEvents()
end

-- [ DIRTY MARKS ]------------------------------------------------------------------------------------------------------
local function RebuildOpenSearches()
    lib._rebuildTimer = nil
    local pending = lib._pendingRebuildKinds
    lib._pendingRebuildKinds = {}
    local interested, enabledKinds = {}, {}
    for search in pairs(lib._openSearches) do
        local enabled = search:GetEnabledKinds()
        interested[search] = enabled
        for kind, included in pairs(enabled) do
            enabledKinds[kind] = enabledKinds[kind] or included
        end
    end
    lib:_EnsureKindsBuilt(enabledKinds)
    for search, enabled in pairs(interested) do
        if lib._openSearches[search] then
            for kind, revision in pairs(pending) do
                if enabled[kind] and (lib._kindRevisions[kind] or 0) ~= revision then
                    search:_NotifyIndexUpdated()
                    break
                end
            end
        end
    end
end

function lib:MarkDirty(kind)
    if not self._built[kind] and not self._buildingKinds[kind] then
        return
    end
    local revision = self._kindRevisions[kind] or 0
    self._dirty[kind] = true
    RetireKind(kind, "pending", "invalidated", false)
    if not next(self._openSearches) then
        return
    end
    -- Preserve the first revision even if a synchronous query rebuilds before the debounce fires.
    self._pendingRebuildKinds[kind] = self._pendingRebuildKinds[kind] or revision
    if self._rebuildTimer then
        self._rebuildTimer:Cancel()
    end
    self._rebuildTimer = C_Timer.NewTimer(REBUILD_DELAY, RebuildOpenSearches)
end

function lib:InvalidateAll()
    for kind in pairs(self._built) do
        self:MarkDirty(kind)
    end
end

function lib:_ForgetKind(kind)
    self._entries[kind] = nil
    self._dirty[kind] = nil
    self._built[kind] = nil
    self._buildErrors[kind] = nil
    self._buildCounts[kind] = nil
    self._sourceStates[kind] = nil
    self._revision = self._revision + 1
    self._kindRevisions[kind] = (self._kindRevisions[kind] or 0) + 1
end

-- [ BUILD ]------------------------------------------------------------------------------------------------------------
function lib:_BuildKind(kind)
    local source = self._indexSources[kind]
    local revision = self._kindRevisions[kind] or 0
    self._buildingKinds[kind] = true
    local start, startKB = self:_ProfileBegin()
    local ok, built, state, reason = pcall(source.Build, source)
    self._buildingKinds[kind] = nil
    self:_ProfileEnd(PROFILER_GROUP, kind, start, startKB)
    if self._indexSources[kind] ~= source or (self._kindRevisions[kind] or 0) ~= revision then
        return true
    end
    self._built[kind] = true
    self._dirty[kind] = nil
    if not ok or (state ~= "pending" and state ~= "unsupported" and type(built) ~= "table") then
        local message = ok and "invalid-build-result" or tostring(built)
        self._buildErrors[kind] = message
        RetireKind(kind, "failed", message, false)
        self:_Report(kind .. ".Build: " .. message)
        return true
    end
    self._buildErrors[kind] = nil
    if state == "pending" or state == "unsupported" then
        RetireKind(kind, state, reason, false)
        return true
    end
    self._entries[kind] = built
    self._buildCounts[kind] = #built
    self._sourceStates[kind] = { state = "ready" }
    AdvanceRevision(kind)
    for _, entry in ipairs(built) do
        self._entryOwners[entry] = { source = source, revision = self._kindRevisions[kind] }
    end
    return true
end

function lib:_EnsureKindsBuilt(enabledKinds)
    local rebuilt = false
    for kind, enabled in pairs(enabledKinds) do
        if enabled and self._indexSources[kind] then
            self:GetIndexSourceState(kind)
            if not self._buildingKinds[kind] and (self._dirty[kind] or not self._built[kind]) then
                rebuilt = self:_BuildKind(kind) or rebuilt
            end
        end
    end
    return rebuilt
end

function lib:IsIndexEntryCurrent(entry)
    local owner = self._entryOwners[entry]
    return owner ~= nil
        and owner.source == self._indexSources[entry.kind]
        and owner.revision == self._kindRevisions[entry.kind]
        and not self._dirty[entry.kind]
        and self:GetIndexSourceState(entry.kind) == "ready"
end

function lib:GetBuildCounts()
    return self._buildCounts
end

function lib:GetBuildErrors()
    return self._buildErrors
end

-- An embedded upgrade must not leave the previous revision's debounce callback in charge of shared refreshes.
if lib._rebuildTimer then
    lib._rebuildTimer:Cancel()
    for kind in pairs(lib._dirty) do
        lib._pendingRebuildKinds[kind] = lib._pendingRebuildKinds[kind] or lib._kindRevisions[kind] or 0
    end
    lib._rebuildTimer = C_Timer.NewTimer(REBUILD_DELAY, RebuildOpenSearches)
end
