local _, addon = ...
local UI = addon.LibOrbitUI

function UI.CreateContext(options)
    assert(type(options.name) == "string" and options.name ~= "", "LibOrbitUI context needs a unique name")
    assert(options.owner, "LibOrbitUI context needs an owner")
    local context = {
        owner = options.owner,
        name = options.name,
        pixel = options.pixel or UI.Pixel:Create({ onDisplayChanged = options.onDisplayChanged }),
        runtime = UI.Runtime:Create(options.owner),
        ownsPixel = options.pixel == nil,
        ownsTooltip = options.tooltip == nil,
        dialogLifecycles = {},
    }
    if options.tooltip then
        assert(options.tooltipHide, "LibOrbitUI borrowed tooltip needs a hide callback")
        context.tooltip = options.tooltip
        context.tooltipHide = options.tooltipHide
    else
        assert(not _G[options.name .. "Tooltip"], "LibOrbitUI tooltip name is already in use")
        context.tooltip = CreateFrame("GameTooltip", options.name .. "Tooltip", UIParent, "GameTooltipTemplate")
        context.tooltip:SetClampedToScreen(true)
        context.tooltipHide = function()
            context.tooltip:Hide()
        end
    end
    function context:Destroy()
        if self.destroyed then
            return
        end
        self.destroyed = true
        for lifecycle in pairs(self.dialogLifecycles) do
            lifecycle:Destroy()
        end
        self.runtime:Destroy()
        if self.ownsPixel then
            self.pixel:Destroy()
        end
        if self.ownsTooltip then
            self.tooltip:Hide()
        end
    end
    return context
end
