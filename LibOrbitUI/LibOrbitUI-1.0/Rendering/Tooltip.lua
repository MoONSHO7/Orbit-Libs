local _, addon = ...
local UI = addon.LibOrbitUI
local TOOLTIP_SCALE = 0.9
local BACKGROUND_ALPHA = 0.75
local BORDER_PIXELS = 2

UI.Tooltip = {}
function UI.Tooltip:Create(name, pixel)
    assert(not _G[name], "LibOrbitUI tooltip name is already in use")
    local tooltip = CreateFrame("GameTooltip", name, UIParent, "GameTooltipTemplate")
    tooltip:SetClampedToScreen(true)
    tooltip:SetScale(TOOLTIP_SCALE)
    local background = tooltip:CreateTexture(nil, "BACKGROUND")
    background:SetAllPoints(tooltip)
    background:SetColorTexture(0, 0, 0, BACKGROUND_ALPHA)
    local borders = {}
    for _, edge in ipairs({ "Top", "Bottom", "Left", "Right" }) do
        local border = tooltip:CreateTexture(nil, "OVERLAY")
        border:SetColorTexture(0, 0, 0, 1)
        borders[edge] = border
    end
    tooltip:HookScript("OnShow", function(self)
        -- Native restricted tooltips must keep their chrome; test geometry before any appearance writes.
        local width, scale = self:GetWidth(), self:GetEffectiveScale()
        if issecretvalue(width) or issecretvalue(scale) then
            self.NineSlice:Show()
            background:Hide()
            for _, border in pairs(borders) do
                border:Hide()
            end
            return
        end
        self.NineSlice:Hide()
        background:Show()
        local thickness = pixel:Multiple(BORDER_PIXELS, scale)
        borders.Top:SetPoint("TOPLEFT", self, "TOPLEFT", 0, 0)
        borders.Top:SetPoint("TOPRIGHT", self, "TOPRIGHT", 0, 0)
        borders.Top:SetHeight(thickness)
        borders.Bottom:SetPoint("BOTTOMLEFT", self, "BOTTOMLEFT", 0, 0)
        borders.Bottom:SetPoint("BOTTOMRIGHT", self, "BOTTOMRIGHT", 0, 0)
        borders.Bottom:SetHeight(thickness)
        borders.Left:SetPoint("TOPLEFT", self, "TOPLEFT", 0, 0)
        borders.Left:SetPoint("BOTTOMLEFT", self, "BOTTOMLEFT", 0, 0)
        borders.Left:SetWidth(thickness)
        borders.Right:SetPoint("TOPRIGHT", self, "TOPRIGHT", 0, 0)
        borders.Right:SetPoint("BOTTOMRIGHT", self, "BOTTOMRIGHT", 0, 0)
        borders.Right:SetWidth(thickness)
        for _, border in pairs(borders) do
            border:Show()
        end
    end)
    return tooltip
end
table.freeze(UI.Tooltip)
