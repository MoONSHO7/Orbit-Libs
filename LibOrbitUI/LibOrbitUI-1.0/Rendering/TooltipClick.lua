local _, addon = ...
local UI = addon.LibOrbitUI
local ICON_SIZE = 18
local KEY_WIDTH = 36
local ICON_Y_OFFSET = -1
local CHORD_JOIN = " "
local LIB_PATH =
    assert(debugstack(1, 1, 0):match("Interface.*LibOrbitUI%-1%.0[\\/]"), "Missing LibOrbitUI embedding path")
local ASSET_PATH = LIB_PATH .. "Rendering\\Assets\\"
local function Markup(file, width)
    return CreateSimpleTextureMarkup(ASSET_PATH .. file .. ".tga", width, ICON_SIZE, 0, ICON_Y_OFFSET)
end
local markup = {}
for button, file in pairs({ Left = "left", Middle = "middle", Right = "right" }) do
    markup[button] = Markup("orbit-click-" .. file, ICON_SIZE)
end
table.freeze(markup)
local keys = {}
for modifier, file in pairs({ Shift = "shift", Control = "control", Alt = "alt" }) do
    keys[modifier] = Markup("orbit-key-" .. file, KEY_WIDTH)
end
table.freeze(keys)

local function Chord(icon, ...)
    local chord = icon
    for index = select("#", ...), 1, -1 do
        local key = assert(keys[select(index, ...)], "Unknown modifier key")
        chord = chord and (key .. CHORD_JOIN .. chord) or key
    end
    return chord
end

UI.TooltipClick = {}
function UI.TooltipClick:Create(label)
    local clicks = {}
    local function prefix(icon, text)
        return text and (icon .. " " .. text) or icon
    end
    function clicks:Left(text, ...)
        if label and text == label("left") then
            return Chord(markup.Left, ...)
        elseif label and text == label("shift") then
            return Chord(markup.Left, "Shift")
        end
        return prefix(Chord(markup.Left, ...), text)
    end
    function clicks:Right(text, ...)
        if label and text == label("right") then
            return Chord(markup.Right, ...)
        end
        return prefix(Chord(markup.Right, ...), text)
    end
    function clicks:Middle(text, ...)
        return prefix(Chord(markup.Middle, ...), text)
    end
    function clicks:Scroll(text, ...)
        return prefix(Chord(markup.Middle, ...), text)
    end
    function clicks:Hold(text, ...)
        return prefix(assert(Chord(nil, ...), "Hold needs a modifier key"), text)
    end
    return table.freeze(clicks)
end
table.freeze(UI.TooltipClick)
