local _, addon = ...
local UI = addon.LibOrbitUI
local CONTAINER_ATLAS = "housing-basic-container"

UI.DialogChrome = {}
local ChromeMixin = {}

function ChromeMixin:ApplyChrome(frame)
    local background = frame:CreateTexture(nil, "BACKGROUND", nil, -1)
    if C_Texture and C_Texture.GetAtlasInfo and C_Texture.GetAtlasInfo(CONTAINER_ATLAS) then
        background:SetAtlas(CONTAINER_ATLAS)
    else
        local color = self.defaultBackdrop
        background:SetColorTexture(color.r, color.g, color.b, color.a)
    end
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
