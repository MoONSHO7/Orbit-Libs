-- [ LibOrbitBridge-1.0 ]-----------------------------------------------------------------------------------------------
local MAJOR, MINOR = "LibOrbitBridge-1.0", 1
local lib = LibStub:NewLibrary(MAJOR, MINOR)
if not lib then
    return
end

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local CALLBACK_EVENTS = {
    QuestieIndexReady = true,
    QuestieExistenceChanged = true,
    QuestieLogChanged = true,
    QuestiePlacesFound = true,
}

-- [ INSTALL ]----------------------------------------------------------------------------------------------------------
-- LibStub answers nil to an older or duplicate copy, whose remaining files check this flag and stand down.
lib.__building = true
lib.API = 1
lib.MAJOR = MAJOR
lib._callbacks = lib._callbacks or {}
lib._demand = lib._demand or {}
lib.Questie = lib.Questie or {}

-- [ CALLBACKS ]--------------------------------------------------------------------------------------------------------
function lib.RegisterCallback(owner, event, callback)
    assert(CALLBACK_EVENTS[event], "LibOrbitBridge: unknown callback event " .. tostring(event))
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

-- [ DEMAND ]-----------------------------------------------------------------------------------------------------------
-- Background work runs only while some consumer wants it; a consumer that disables itself releases its demand.
function lib:_Demand(owner)
    if not self._demand[owner] then
        self._demand[owner] = true
        self:_DemandChanged()
    end
end

function lib.Release(owner)
    lib._demand[owner] = nil
    lib:_DemandChanged()
end

function lib:_Demanded()
    return next(self._demand) ~= nil
end

-- [ DRIVERS ]----------------------------------------------------------------------------------------------------------
-- A driver runs `step` once per frame while it has work and some consumer demands it; `step` answers true when done.
lib._drivers = lib._drivers or {}

function lib:_SyncDriver(driver)
    local run = driver.pending and self:_Demanded()
    if run == driver.running then
        return
    end
    driver.running = run
    driver.frame:SetScript("OnUpdate", run and driver.update or nil)
end

function lib:_StartDriver(name, step)
    local driver = self._drivers[name]
    if not driver then
        driver = { frame = CreateFrame("Frame"), running = false }
        driver.update = function()
            if driver.step() then
                driver.pending = false
                lib:_SyncDriver(driver)
            end
        end
        self._drivers[name] = driver
    end
    driver.step, driver.pending = step, true
    self:_SyncDriver(driver)
end

function lib:_DemandChanged()
    for _, driver in pairs(self._drivers) do
        self:_SyncDriver(driver)
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

function lib:_ProfileEnd(name, start, startKB)
    local profiler = self._profiler
    if profiler and start then
        profiler.End(MAJOR, name, start, startKB)
    end
end

function lib:_Count(name)
    local profiler = self._profiler
    if profiler and profiler.Count then
        profiler.Count(MAJOR, name)
    end
end

-- [ READERS ]----------------------------------------------------------------------------------------------------------
function lib.Readable(value)
    if not issecretvalue(value) then
        return value
    end
end

function lib.Number(value)
    value = lib.Readable(value)
    if type(value) == "number" and value == value and math.abs(value) < math.huge then
        return value
    end
end

function lib.Text(value)
    value = lib.Readable(value)
    return type(value) == "string" and value ~= "" and value or nil
end

-- [ EVENTS ]-----------------------------------------------------------------------------------------------------------
lib._events = lib._events or CreateFrame("Frame")
lib._eventHandlers = lib._eventHandlers or {}

function lib:_On(event, handler)
    self._eventHandlers[event] = handler
    if C_EventUtils.IsEventValid(event) then
        self._events:RegisterEvent(event)
    end
end

lib._events:SetScript("OnEvent", function(_, event, ...)
    local handler = lib._eventHandlers[event]
    if handler then
        handler(event, ...)
    end
end)
