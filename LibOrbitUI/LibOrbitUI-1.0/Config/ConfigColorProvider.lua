local _, addon = ...
local Config = addon.LibOrbitUI.Config

local function GetPicker()
    local picker = LibStub and LibStub("LibOrbitColorPicker-1.0", true)
    return picker and picker.GetCheckerboardTexture and picker or nil
end

local function DefaultClassColor()
    local _, class = UnitClass("player")
    local color = class and not issecretvalue(class) and RAID_CLASS_COLORS[class]
    return color or { r = 1, g = 1, b = 1, a = 1 }
end

function Config.CreateColorProvider(context, options)
    options = options or {}
    local getPicker = options.getPicker or GetPicker
    local activeOwner, activePicker, activeSession
    local classColor = options.classColor or DefaultClassColor
    local provider = {
        removeTooltip = options.removeTooltip,
        resolveValue = options.resolveValue or function(value)
            local color = value and value.type == "class" and classColor() or value or {}
            local alpha = value and value.a
            return color.r or 1, color.g or 1, color.b or 1, alpha or color.a or 1
        end,
        resolvePin = options.resolvePin or function(pin)
            local color = pin.type == "class" and classColor() or pin.color or {}
            return {
                r = color.r or 1,
                g = color.g or 1,
                b = color.b or 1,
                a = (pin.color and pin.color.a) or color.a or 1,
            }
        end,
    }
    local picker = getPicker()
    provider.checkerboard = options.checkerboard
        or (picker and picker.GetCheckerboardTexture and picker:GetCheckerboardTexture())
    function provider.isAvailable()
        return getPicker() ~= nil
    end
    function provider.open(owner, pickerOptions)
        local current = getPicker()
        if not current then
            return false
        end
        local request = {}
        for key, value in pairs(pickerOptions) do
            request[key] = value
        end
        request.tooltip, request.tooltipHide = context.tooltip, context.tooltipHide
        request.classColor = classColor
        request.recentColorsDb = options.getRecentColors and options.getRecentColors() or nil
        request.onOpen = options.onOpen
        local session = current:Open(request)
        if session == false or (session and current.sessionId ~= session) then
            return false
        end
        activeOwner, activePicker, activeSession = owner, current, session or current.sessionId
        return true
    end
    function provider.close(owner)
        if activeOwner ~= owner then
            return
        end
        local current, session = activePicker, activeSession
        activeOwner, activePicker, activeSession = nil, nil, nil
        if current.sessionId == session and current:IsOpen() then
            current.wasCancelled = true
            current:CloseFrame()
        end
    end
    return provider
end
