local _, addon = ...
local UI = addon.LibOrbitUI

UI.Runtime = {}

local RuntimeMixin = {}

function RuntimeMixin:Cancel(key)
    local record = self.work[key]
    if record then
        self.work[key] = nil
        record.timer:Cancel()
    end
end

function RuntimeMixin:CancelAll()
    self.generation = self.generation + 1
    self.events:SetScript("OnUpdate", nil)
    for key in pairs(self.work) do
        self:Cancel(key)
    end
    for _, handle in pairs(self.reconcilers) do
        handle.pending = false
    end
end

local function Schedule(runtime, key, delay, callback, repeating)
    assert(not runtime.destroyed, "LibOrbitUI runtime is destroyed")
    assert(type(delay) == "number" and delay > 0, "LibOrbitUI timer interval must be positive")
    runtime:Cancel(key)
    local generation = runtime.generation
    local record = {}
    runtime.work[key] = record
    local function Dispatch()
        if runtime.destroyed or generation ~= runtime.generation or runtime.work[key] ~= record then
            return
        end
        if not repeating then
            runtime.work[key] = nil
        end
        local ok, err = pcall(callback, runtime.owner)
        if not ok then
            if runtime.work[key] == record then
                runtime:Cancel(key)
            end
            geterrorhandler()(err)
        end
    end
    record.timer = repeating and C_Timer.NewTicker(delay, Dispatch) or C_Timer.NewTimer(delay, Dispatch)
    return record.timer
end

function RuntimeMixin:After(key, delay, callback)
    return Schedule(self, key, delay, callback, false)
end

function RuntimeMixin:Debounce(key, callback, delay)
    return Schedule(self, key, delay, callback, false)
end

function RuntimeMixin:Ticker(key, interval, callback)
    return Schedule(self, key, interval, callback, true)
end

function RuntimeMixin:RegisterReconciler(key, callback, canApply)
    assert(not self.destroyed, "LibOrbitUI runtime is destroyed")
    assert(not self.reconcilers[key], "LibOrbitUI reconciler key already registered")
    local handle = { runtime = self, callback = callback, canApply = canApply, pending = false }
    self.reconcilers[key] = handle
    return handle
end

local function ApplyPending(runtime)
    if runtime.destroyed or runtime.applying or InCombatLockdown() then
        return
    end
    runtime.applying = true
    for _, handle in pairs(runtime.reconcilers) do
        if handle.pending then
            local ok, err = pcall(function()
                if not handle.canApply or handle.canApply(runtime.owner) then
                    handle.pending = false
                    handle.callback(runtime.owner)
                end
            end)
            if not ok then
                handle.pending = false
                geterrorhandler()(err)
            end
        end
    end
    runtime.applying = false
end

function RuntimeMixin:Invalidate(handle)
    assert(handle.runtime == self, "LibOrbitUI reconciler belongs to another runtime")
    if self.destroyed then
        return
    end
    handle.pending = true
    if self.applying then
        self.events:SetScript("OnUpdate", function(frame)
            frame:SetScript("OnUpdate", nil)
            ApplyPending(self)
        end)
        return
    end
    ApplyPending(self)
end

function RuntimeMixin:Destroy()
    self:CancelAll()
    self.destroyed = true
    self.events:UnregisterAllEvents()
    self.events:SetScript("OnEvent", nil)
end

table.freeze(RuntimeMixin)

function UI.Runtime:Create(owner)
    local runtime = Mixin({ owner = owner, generation = 0, work = {}, reconcilers = {} }, RuntimeMixin)
    runtime.events = CreateFrame("Frame")
    runtime.events:RegisterEvent("PLAYER_REGEN_ENABLED")
    runtime.events:RegisterEvent("ENCOUNTER_END")
    runtime.events:SetScript("OnEvent", function()
        ApplyPending(runtime)
    end)
    return runtime
end
