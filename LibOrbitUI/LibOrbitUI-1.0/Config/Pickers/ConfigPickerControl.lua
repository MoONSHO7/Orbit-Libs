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
    control:SetScript("OnEnable", RefreshState)
    control:SetScript("OnDisable", RefreshState)
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
