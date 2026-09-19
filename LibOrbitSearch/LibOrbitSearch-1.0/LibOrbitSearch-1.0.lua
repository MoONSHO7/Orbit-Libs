-- [ LibOrbitSearch-1.0 ]-----------------------------------------------------------------------------------------------
local MAJOR, MINOR = "LibOrbitSearch-1.0", 3
local lib = LibStub:NewLibrary(MAJOR, MINOR)
if not lib then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local CALLBACK_EVENTS = { SourcesChanged = true, InclusionChanged = true }

-- [ INSTALL ]----------------------------------------------------------------------------------------------------------
-- LibStub answers nil to an older or duplicate copy, whose remaining files check this flag and stand down.
lib.__building = true
lib.API = 1
lib.INDEX_CONTRACT = 1
lib.PROVIDER_CONTRACT = 1
lib.MAJOR = MAJOR
lib._callbacks = lib._callbacks or {}
lib._searches = lib._searches or setmetatable({}, { __mode = "k" })
lib._enabledSearches = lib._enabledSearches or {}
lib._openSearches = lib._openSearches or {}

-- [ CALLBACKS ]--------------------------------------------------------------------------------------------------------
function lib.RegisterCallback(owner, event, callback)
    assert(CALLBACK_EVENTS[event], "LibOrbitSearch: unknown callback event " .. tostring(event))
    lib._callbacks[event] = lib._callbacks[event] or {}
    lib._callbacks[event][owner] = callback
end

function lib.UnregisterCallback(owner, event)
    local listeners = lib._callbacks[event]
    if listeners then
        listeners[owner] = nil
    end
end

function lib:_Report(message)
    geterrorhandler()(message)
end

function lib:_Fire(event, ...)
    for _, callback in pairs(self._callbacks[event] or {}) do
        local ok, err = pcall(callback, ...)
        if not ok then
            self:_Report(err)
        end
    end
end

-- [ PROFILER ]---------------------------------------------------------------------------------------------------------
function lib:SetProfiler(profiler)
    self._profiler = profiler
end

function lib:_ProfileBegin()
    local profiler = self._profiler
    if profiler then
        return profiler.Begin()
    end
end

function lib:_ProfileEnd(group, name, start, startKB)
    local profiler = self._profiler
    if profiler and start then
        profiler.End(group, name, start, startKB)
    end
end
