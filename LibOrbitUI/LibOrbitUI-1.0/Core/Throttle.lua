local _, addon = ...
local UI = addon.LibOrbitUI

UI.Throttle = {}
local ThrottleMixin = {}

local function CheckInterval(interval)
    assert(
        type(interval) == "number" and interval > 0 and interval < math.huge,
        "LibOrbitUI interval must be finite and positive"
    )
end

function ThrottleMixin:Gate(state, field, interval, elapsed)
    CheckInterval(interval)
    state[field] = (state[field] or 0) + (elapsed or 0)
    if state[field] < interval then
        return false
    end
    state[field] = 0
    return true
end

function ThrottleMixin:OnUpdate(interval, owner, callback, source)
    CheckInterval(interval)
    local accumulated = 0
    local wrapped = UI.Callbacks:Wrap(callback, source or "OnUpdate")
    return function(frame, elapsed)
        accumulated = accumulated + elapsed
        if accumulated < interval then
            return
        end
        accumulated = 0
        wrapped(frame)
    end
end

table.freeze(ThrottleMixin)

function UI.Throttle:Create()
    return Mixin({}, ThrottleMixin)
end
