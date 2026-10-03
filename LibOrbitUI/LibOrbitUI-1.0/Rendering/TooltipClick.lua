local _, addon = ...
local UI = addon.LibOrbitUI
local ICON_SIZE = 18
local ICON_Y_OFFSET = -1
local LIB_PATH =
    assert(debugstack(1, 1, 0):match("Interface.*LibOrbitUI%-1%.0[\\/]"), "Missing LibOrbitUI embedding path")
local markup = {}
for button, file in pairs({ Left = "left", Middle = "middle", Right = "right" }) do
    markup[button] = CreateSimpleTextureMarkup(
        LIB_PATH .. "Rendering\\Assets\\orbit-click-" .. file .. ".tga",
        ICON_SIZE,
        ICON_SIZE,
        0,
        ICON_Y_OFFSET
    )
end
table.freeze(markup)

UI.TooltipClick = {}
function UI.TooltipClick:Create(label)
    local clicks = {}
    local function prefix(icon, text)
        return text and (icon .. " " .. text) or icon
    end
    function clicks:Left(text)
        if label and text == label("left") then
            return markup.Left
        elseif label and text == label("shift") then
            return SHIFT_KEY_TEXT .. " + " .. markup.Left
        end
        return prefix(markup.Left, text)
    end
    function clicks:Right(text)
        if label and text == label("right") then
            return markup.Right
        end
        return prefix(markup.Right, text)
    end
    function clicks:Middle(text)
        return prefix(markup.Middle, text)
    end
    function clicks:Scroll(text)
        return prefix(markup.Middle, text)
    end
    function clicks:ControlScroll(text)
        return assert(label and label("control"), "Localized control modifier required")
            .. " + "
            .. prefix(markup.Middle, text)
    end
    function clicks:ShiftRight(text)
        return SHIFT_KEY_TEXT .. " + " .. prefix(markup.Right, text)
    end
    return table.freeze(clicks)
end
table.freeze(UI.TooltipClick)
