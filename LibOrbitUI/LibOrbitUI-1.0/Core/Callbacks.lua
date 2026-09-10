local _, addon = ...
local UI = addon.LibOrbitUI
local ERROR_FORMAT = "LibOrbitUI [%s:%s] %s"

UI.Callbacks = {}

function UI.Callbacks:LogError(context, event, err)
    geterrorhandler()(ERROR_FORMAT:format(tostring(context), tostring(event), tostring(err)))
end

function UI.Callbacks:Run(callback, context, ...)
    local ok, result = pcall(callback, ...)
    if not ok then
        self:LogError(context or "Unknown", "wrapped_call", result)
    end
    return ok, result
end

function UI.Callbacks:Wrap(callback, context)
    return function(...)
        local ok, result = self:Run(callback, context, ...)
        if ok then
            return result
        end
    end
end

table.freeze(UI.Callbacks)
