local _, addon = ...
local UI = addon.LibOrbitUI
local CUSTOM_PREFIX = "ORBIT_"

UI.Events = {}
local EventsMixin = {}

local function IsCustom(event)
    return event:sub(1, #CUSTOM_PREFIX) == CUSTOM_PREFIX
end

function EventsMixin:On(event, callback, context)
    assert(type(event) == "string" and event ~= "", "LibOrbitUI event name is required")
    assert(type(callback) == "function", "LibOrbitUI event callback is required")
    local listeners = self.listeners[event]
    if not listeners then
        if not IsCustom(event) then
            self.frame:RegisterEvent(event)
        end
        listeners = {}
        self.listeners[event] = listeners
    end
    local listener = { callback = callback, context = context }
    listeners[#listeners + 1] = listener
    return listener
end

local function ReleaseEmpty(self, event, listeners)
    if #listeners == 0 then
        self.listeners[event] = nil
        if not IsCustom(event) then
            self.frame:UnregisterEvent(event)
        end
    end
end

function EventsMixin:Off(event, callback)
    local listeners = self.listeners[event]
    if not listeners then
        return false
    end
    for index = #listeners, 1, -1 do
        if listeners[index].callback == callback then
            table.remove(listeners, index)
            ReleaseEmpty(self, event, listeners)
            return true
        end
    end
    return false
end

function EventsMixin:OffContext(context)
    for event, listeners in pairs(self.listeners) do
        for index = #listeners, 1, -1 do
            if listeners[index].context == context then
                table.remove(listeners, index)
            end
        end
        ReleaseEmpty(self, event, listeners)
    end
end

local function Dispatch(self, event, filtered, context, ...)
    local listeners = self.listeners[event]
    if not listeners then
        return
    end
    self.depth = self.depth + 1
    local snapshot = self.snapshots[self.depth] or {}
    self.snapshots[self.depth] = snapshot
    local count = 0
    for _, listener in ipairs(listeners) do
        if not filtered or listener.context == context then
            count = count + 1
            snapshot[count] = listener
        end
    end
    for index = 1, count do
        local listener = snapshot[index]
        local ok, err
        if listener.context ~= nil then
            ok, err = pcall(listener.callback, listener.context, ...)
        else
            ok, err = pcall(listener.callback, ...)
        end
        if not ok then
            -- An error-handler failure must not strand nested dispatch state or skip the remaining listeners.
            pcall(UI.Callbacks.LogError, UI.Callbacks, "Events", event, err)
        end
    end
    for index = count, 1, -1 do
        snapshot[index] = nil
    end
    self.depth = self.depth - 1
end

function EventsMixin:Fire(event, ...)
    Dispatch(self, event, false, nil, ...)
end

function EventsMixin:FireContext(event, context, ...)
    Dispatch(self, event, true, context, ...)
end

table.freeze(EventsMixin)

function UI.Events:Create()
    local events = Mixin({ listeners = {}, snapshots = {}, depth = 0, frame = CreateFrame("Frame") }, EventsMixin)
    events.frame:SetScript("OnEvent", function(_, event, ...)
        events:Fire(event, ...)
    end)
    return events
end
