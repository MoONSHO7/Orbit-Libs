local _, addon = ...
local UI = addon.LibOrbitUI
local CONTAINER_ATLAS = "housing-basic-container"

UI.DialogChrome = {}
local ChromeMixin = {}

function ChromeMixin:ApplyChrome(frame)
    local background = frame:CreateTexture(nil, "BACKGROUND", nil, -1)
    background:SetAtlas(CONTAINER_ATLAS)
    background:SetAllPoints(frame)
    return { Background = background }
end

function ChromeMixin:ApplyBackdrop(background, streaks, color)
    local value = color or self.defaultBackdrop
    background:SetHorizTile(false)
    background:SetVertTile(false)
    background:SetColorTexture(value.r, value.g, value.b, value.a)
    if streaks then
        streaks:Hide()
    end
end

table.freeze(ChromeMixin)

function UI.DialogChrome:Create(defaultBackdrop)
    return Mixin({ defaultBackdrop = defaultBackdrop }, ChromeMixin)
end
