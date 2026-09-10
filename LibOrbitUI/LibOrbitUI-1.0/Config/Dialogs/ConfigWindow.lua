local _, addon = ...
local UI = addon.LibOrbitUI
local DIALOG_WIDTH = 350
local DIALOG_HEIGHT = 150
local DIALOG_LEVEL = 200
local TITLE_OFFSET = 20
local CLOSE_OFFSET = -2
local ESC_RESTORE_DELAY = 0.05

UI.ConfigWindow = {}

function UI.ConfigWindow:Create(context, options)
    assert(type(options.name) == "string" and not _G[options.name], "LibOrbitUI window needs an unused global name")
    assert(type(options.title) == "string", "LibOrbitUI window needs a localized title")
    local chrome = context.chrome or UI.DialogChrome:Create(options.backdrop or UI.Config.Defaults.DialogBackdrop)
    local dialog = CreateFrame("Frame", options.name, UIParent)
    dialog:Hide()
    dialog:SetSize(options.width or DIALOG_WIDTH, options.height or DIALOG_HEIGHT)
    local position = options.position
    if position then
        dialog:SetPoint(
            position.point,
            UIParent,
            position.relativePoint or position.point,
            position.x or 0,
            position.y or 0
        )
    else
        dialog:SetPoint("CENTER", UIParent, "CENTER")
    end
    dialog:SetFrameStrata(options.strata or UI.Config.Defaults.Strata.Dialog)
    dialog:SetFrameLevel(options.level or DIALOG_LEVEL)
    dialog:SetMovable(true)
    dialog:SetClampedToScreen(true)
    dialog:EnableMouse(true)
    dialog:RegisterForDrag("LeftButton")
    dialog.Chrome = chrome:ApplyChrome(dialog)
    dialog:SetScript("OnDragStart", function(self)
        self:StartMoving()
    end)
    dialog:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        local top, left = self:GetTop(), self:GetLeft()
        if not top or not left then
            return
        end
        self:ClearAllPoints()
        self:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", left, top)
        if options.onPositionChanged then
            options.onPositionChanged(context.owner, { x = left, y = top }, self)
        end
    end)
    if options.hideInCombat ~= false then
        dialog:RegisterEvent("PLAYER_REGEN_DISABLED")
        dialog:SetScript("OnEvent", function(self)
            if self:IsShown() then
                self:Hide()
            end
        end)
    end
    dialog.Title = dialog:CreateFontString(nil, "ARTWORK", "GameFontHighlightLarge")
    dialog.Title:SetPoint("TOP", dialog, "TOP", 0, -TITLE_OFFSET)
    dialog.Title:SetText(options.title)
    dialog.CloseButton = CreateFrame("Button", nil, dialog, "UIPanelCloseButton")
    -- Housing chrome's close inset is a logical-unit offset, matching the existing Orbit shell.
    dialog.CloseButton:SetPoint("TOPRIGHT", dialog, "TOPRIGHT", CLOSE_OFFSET, CLOSE_OFFSET)
    dialog.CloseButton:SetScript("OnClick", function()
        dialog:Hide()
    end)
    if options.escapeClose ~= false then
        UISpecialFrames[#UISpecialFrames + 1] = options.name
        if not InCombatLockdown() then
            dialog:SetPropagateKeyboardInput(true)
        end
        dialog:SetScript("OnKeyDown", function(self, key)
            if key ~= "ESCAPE" or InCombatLockdown() then
                return
            end
            self:SetPropagateKeyboardInput(false)
            self:Hide()
            C_Timer.After(ESC_RESTORE_DELAY, function()
                if not InCombatLockdown() then
                    self:SetPropagateKeyboardInput(true)
                end
            end)
        end)
    end
    dialog:HookScript("OnHide", function(self)
        self:StopMovingOrSizing()
    end)
    return dialog
end
