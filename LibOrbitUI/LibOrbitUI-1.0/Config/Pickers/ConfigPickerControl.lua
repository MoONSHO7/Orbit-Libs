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
local WARNING_SIZE, WARNING_GAP = 14, 4

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

local function EnterControl(control)
    control.hovered = true
    RefreshState(control)
end

local function LeaveControl(control)
    control.hovered = false
    RefreshState(control)
end

local function RefreshEnabled(control)
    RefreshState(control)
    Config.RefreshPickerValueWarning(control)
end

-- [ VALUE WARNING ]----------------------------------------------------------------------------------------------------
local function HideWarningTooltip(badge)
    if badge.configTooltip:IsOwned(badge) then
        badge.configTooltipHide()
    end
end

-- The badge takes the picker's motion focus, so it carries the picker's hover border too.
local function ShowWarningTooltip(badge)
    local control = badge:GetParent()
    EnterControl(control)
    local warning = control.valueWarning
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

local function LeaveWarning(badge)
    LeaveControl(badge:GetParent())
    HideWarningTooltip(badge)
end

local function CreateWarningBadge(layout, control)
    local options = layout.configOptions
    local badge = CreateFrame("Frame", nil, control)
    -- Motion-only input shows the tooltip while clicks fall through to the picker beneath.
    badge:EnableMouseMotion(true)
    badge:SetMouseClickEnabled(false)
    badge.configPixel, badge.configTooltip, badge.configTooltipHide =
        options.pixel, options.tooltip, options.tooltipHide
    badge.Icon = badge:CreateTexture(nil, "OVERLAY")
    badge.Icon:SetAtlas(WARNING_ATLAS)
    badge.Icon:SetAllPoints()
    badge:Hide()
    badge:SetScript("OnEnter", ShowWarningTooltip)
    badge:SetScript("OnLeave", LeaveWarning)
    badge:SetScript("OnHide", HideWarningTooltip)
    control.ValueWarning = badge
end

local function WarningApplies(warning, value)
    local visible = warning.visible
    if type(visible) == "function" then
        return visible(value) and true or false
    end
    return visible ~= false
end

function Config.RefreshPickerValueWarning(control)
    local badge = control.ValueWarning
    if not badge then
        return
    end
    local shown = control.valueWarningWanted and control:IsEnabled() and not control:GetParent().configMixed
    if shown == badge:IsShown() then
        return
    end
    local Pixel = badge.configPixel
    if shown then
        badge:SetSize(Pixel:SnapSize(WARNING_SIZE, WARNING_SIZE, badge:GetEffectiveScale(), true))
        Pixel:Point(badge, "RIGHT", control.Arrow, "LEFT", -WARNING_GAP, 0)
        Pixel:Point(control.Text, "RIGHT", badge, "LEFT", -TEXT_GAP, 0)
        badge:Show()
    else
        badge:Hide()
        Pixel:Point(control.Text, "RIGHT", control.Arrow, "LEFT", -TEXT_GAP, 0)
    end
end

function Config.ApplyPickerValueWarning(layout, control, warning, value)
    if not warning and not control.ValueWarning then
        return
    end
    if not control.ValueWarning then
        CreateWarningBadge(layout, control)
    end
    control.valueWarning = warning
    control.valueWarningWanted = warning ~= nil and WarningApplies(warning, value)
    Config.RefreshPickerValueWarning(control)
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
    control:SetScript("OnEnter", EnterControl)
    control:SetScript("OnLeave", LeaveControl)
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
