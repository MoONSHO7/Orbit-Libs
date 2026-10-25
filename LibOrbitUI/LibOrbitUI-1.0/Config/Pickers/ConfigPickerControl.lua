local _, addon = ...
local Config = addon.LibOrbitUI.Config
local HEIGHT = 24
local BG = { 0.08, 0.08, 0.1, 1 }
local BORDER = { 0, 0, 0, 1 }
local BORDER_HOVER = { 0.3, 0.3, 0.3, 1 }
local BORDER_OPEN = { 1, 0.82, 0, 0.65 }
local ACCENT = { 1, 0.82, 0, 1 }
local ARROW = "common-dropdown-icon-next"
local ARROW_SIZE, ARROW_INSET = 10, 8
local ARROW_DOWN, ARROW_UP = -math.pi / 2, math.pi / 2
local TEXT_GAP = 3
local WARNING_ATLAS = "transmog-icon-warning-small"

local function RefreshState(control)
    control.Arrow:SetRotation(control.isOpen and ARROW_UP or ARROW_DOWN)
    if control.isOpen then
        control:SetBackdropBorderColor(unpack(BORDER_OPEN))
        control.Arrow:SetVertexColor(unpack(ACCENT))
    elseif control.hovered then
        control:SetBackdropBorderColor(unpack(BORDER_HOVER))
        control.Arrow:SetVertexColor(1, 1, 1, 1)
    else
        control:SetBackdropBorderColor(unpack(BORDER))
        control.Arrow:SetVertexColor(1, 1, 1, 1)
    end
end

local function RefreshEnabled(control)
    RefreshState(control)
    Config.RefreshPickerValueWarning(control:GetParent())
end

-- [ VALUE WARNING ]----------------------------------------------------------------------------------------------------
local function HideWarningTooltip(badge)
    if badge.configTooltip:IsOwned(badge) then
        badge.configTooltipHide()
    end
end

local function ShowWarningTooltip(badge)
    local warning = badge:GetParent().valueWarning
    local title = Config.ResolveText(warning.title)
    if not title or title == "" then
        return
    end
    local tooltip = badge.configTooltip
    tooltip:SetOwner(badge, "ANCHOR_RIGHT")
    tooltip:SetText(title, 1, 1, 1)
    local text = Config.ResolveText(warning.text)
    if text and text ~= "" then
        tooltip:AddLine(text, nil, nil, nil, true)
    end
    tooltip:Show()
end

local function CreateWarningBadge(layout, frame)
    local options = layout.configOptions
    local badge = CreateFrame("Frame", nil, frame)
    badge:EnableMouseMotion(true)
    badge:SetMouseClickEnabled(false)
    badge.configLayout, badge.configTooltip, badge.configTooltipHide = layout, options.tooltip, options.tooltipHide
    badge.Icon = badge:CreateTexture(nil, "OVERLAY")
    badge.Icon:SetAtlas(WARNING_ATLAS)
    badge.Icon:SetAllPoints()
    badge:Hide()
    badge:SetScript("OnEnter", ShowWarningTooltip)
    badge:SetScript("OnLeave", HideWarningTooltip)
    badge:SetScript("OnHide", HideWarningTooltip)
    frame.ValueWarning = badge
end

local function WarningApplies(warning, value)
    local visible = warning.visible
    if type(visible) == "function" then
        return visible(value) and true or false
    end
    return visible ~= false
end

local function UpdateWarningShown(frame)
    local badge = frame.ValueWarning
    local shown = frame.valueWarningWanted and frame.Control:IsEnabled() and not frame.configMixed
    if shown == badge:IsShown() then
        return false
    end
    if shown then
        local options = badge.configLayout.configOptions
        local size = options.constants.Widget.ValueSwatchSize
        badge:SetSize(options.pixel:SnapSize(size, size, badge:GetEffectiveScale(), true))
    end
    badge:SetShown(shown)
    return shown
end

-- The warning leads the accessory group, so showing or hiding it never moves the checkbox or swatch beside it.
local function LayoutValueColumn(frame)
    local badge = frame.ValueWarning
    badge.configLayout:LayoutValueControls(frame, badge, frame.ValueCheckbox, frame.ValueColorSwatch)
end

function Config.RefreshPickerValueWarning(frame)
    if frame.ValueWarning and UpdateWarningShown(frame) then
        LayoutValueColumn(frame)
    end
end

function Config.ApplyPickerValueWarning(layout, frame, warning, value)
    if not warning and not frame.ValueWarning then
        return
    end
    if not frame.ValueWarning then
        CreateWarningBadge(layout, frame)
    end
    frame.valueWarning = warning
    frame.valueWarningWanted = warning ~= nil and WarningApplies(warning, value)
    UpdateWarningShown(frame)
    if warning then
        LayoutValueColumn(frame)
    end
end

-- [ PICKER CONTROL ]---------------------------------------------------------------------------------------------------
function Config:CreatePickerControl(frame, opts)
    local Pixel = self.configOptions.pixel
    local white = self.configOptions.constants.Texture.White
    opts = opts or {}
    Pixel:Enforce(frame)
    local control = CreateFrame("Button", nil, frame, "BackdropTemplate")
    Pixel:Enforce(control)
    control:SetBackdrop({ bgFile = white, edgeFile = white, edgeSize = Pixel:Multiple(1, control:GetEffectiveScale()) })
    control:SetBackdropColor(unpack(BG))
    control:SetBackdropBorderColor(unpack(BORDER))
    control:SetHeight(opts.height or HEIGHT)
    control.Arrow = control:CreateTexture(nil, "OVERLAY")
    Pixel:Enforce(control.Arrow, { centerAnchored = true })
    control.Arrow:SetAtlas(ARROW)
    control.Arrow:SetSize(ARROW_SIZE, ARROW_SIZE)
    Pixel:Point(control.Arrow, "RIGHT", -ARROW_INSET, 0)
    control.Text = control:CreateFontString(nil, "OVERLAY", opts.fontObject or "GameFontHighlight")
    Pixel:Point(control.Text, "RIGHT", control.Arrow, "LEFT", -TEXT_GAP, 0)
    control.Text:SetJustifyH(opts.justify or "LEFT")
    control.Text:SetWordWrap(false)
    control:SetScript("OnClick", function()
        if control.isOpen then
            control.Popup:Hide()
        else
            frame:ShowDropdown()
        end
    end)
    control:SetScript("OnEnter", function()
        control.hovered = true
        RefreshState(control)
    end)
    control:SetScript("OnLeave", function()
        control.hovered = false
        RefreshState(control)
    end)
    control:SetScript("OnEnable", RefreshEnabled)
    control:SetScript("OnDisable", RefreshEnabled)
    control:SetScript("OnHide", function()
        control.hovered = false
        if control.Popup then
            control.Popup:Hide()
        end
        RefreshState(control)
    end)
    RefreshState(control)
    frame.Control = control
    return control
end

function Config:BindPickerDropdown(control, popup)
    control.Popup = popup
    popup:HookScript("OnShow", function()
        control.isOpen = true
        RefreshState(control)
    end)
    popup:HookScript("OnHide", function()
        control.isOpen = false
        RefreshState(control)
    end)
end

function Config:LayoutPickerLabelAndControl(frame, label)
    local C = self.configOptions.constants
    frame.Label:SetText(label)
    frame.Label:SetWidth(C.Widget.LabelWidth)
    frame.Label:SetJustifyH("LEFT")
    frame.Label:ClearAllPoints()
    frame.Label:SetPoint("LEFT", frame, "LEFT", 0, 0)
    frame.Control:ClearAllPoints()
    frame.Control:SetPoint("LEFT", frame.Label, "RIGHT", C.Widget.LabelGap, 0)
    frame.Control:SetPoint("RIGHT", frame, "RIGHT", -C.Widget.ValueWidth, 0)
end
