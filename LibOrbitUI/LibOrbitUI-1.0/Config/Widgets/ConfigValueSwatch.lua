local _, addon = ...
local Config = addon.LibOrbitUI.Config

-- [ VALUE-COLUMN CONTROLS ]--------------------------------------------------------------------------------------------
local SLIDER_BTN_W = 36
local SLIDER_POPUP_LEVEL = 1000

local function HideTooltip(control)
    local tooltip = control.valueTooltip
    if tooltip and tooltip:GetOwner() == control then
        tooltip:Hide()
    end
end

local function ReleaseSwatch(swatch)
    swatch.colorGeneration = (swatch.colorGeneration or 0) + 1
    if swatch.colorProvider.close then
        swatch.colorProvider.close(swatch)
    end
    HideTooltip(swatch)
    swatch:SetScript("OnClick", nil)
    swatch:SetScript("OnEnter", nil)
    swatch:SetScript("OnLeave", nil)
    swatch.value = nil
    swatch:Hide()
end

local function ResolvePreviewColor(layout, curveMode, value)
    if not value then
        return 1, 1, 1, 1
    end
    if curveMode then
        local pins = value.pins
        if not pins or #pins == 0 then
            return 0.5, 0.5, 0.5, 1
        end
        local first = pins[1]
        for i = 2, #pins do
            if pins[i].position < first.position then
                first = pins[i]
            end
        end
        local color = layout.pickerOptions.color.resolvePin(first)
        return color.r, color.g, color.b, color.a or 1
    end
    return layout.pickerOptions.color.resolveValue(value)
end

local function RenderSwatchColor(layout, swatch, allowNone)
    if allowNone and swatch.value and swatch.value.none then
        Config.PaintCheckerboard(swatch.Color, layout.pickerOptions.color.checkerboard)
        swatch.Color:SetVertexColor(1, 1, 1, 1)
    else
        swatch.Color:SetColorTexture(1, 1, 1, 1)
        swatch.Color:SetVertexColor(ResolvePreviewColor(layout, swatch.curveMode, swatch.value))
    end
end

function Config:OpenColorPicker(owner, options)
    local provider = self.pickerOptions.color
    if not Config.IsColorPickerAvailable(provider) then
        return false
    end
    options.anchor = options.anchor or self.GetPickerAnchor(owner)
    return provider.open(owner, options)
end

function Config:ApplyValueColorSwatch(frame, cfg, anchorX)
    local Layout = self
    local Constants = self.configOptions.constants
    local Pixel = self.configOptions.pixel
    local GameTooltip = self.configOptions.tooltip
    local GameTooltip_Hide = self.configOptions.tooltipHide
    local WHITE8x8 = Constants.Texture.White
    local enabled = cfg.enabled
    if type(enabled) == "function" then
        enabled = enabled()
    end
    if enabled == false then
        if frame.ValueColorSwatch then
            ReleaseSwatch(frame.ValueColorSwatch)
        end
        return
    end

    if not frame.ValueColorSwatch then
        local swatch = CreateFrame("Button", nil, frame, "BackdropTemplate")
        swatch:SetSize(Constants.Widget.ValueSwatchSize, Constants.Widget.ValueSwatchSize)
        swatch:SetBackdrop({
            bgFile = WHITE8x8,
            edgeFile = WHITE8x8,
            edgeSize = Pixel:Multiple(1, swatch:GetEffectiveScale()),
        })
        swatch:SetBackdropBorderColor(0, 0, 0, 1)
        swatch.Color = swatch:CreateTexture(nil, "OVERLAY")
        Pixel:Point(swatch.Color, "TOPLEFT", 1, -1)
        Pixel:Point(swatch.Color, "BOTTOMRIGHT", -1, 1)
        swatch.Color:SetColorTexture(1, 1, 1, 1)
        frame.ValueColorSwatch = swatch
    end

    local C = Constants
    local swatch = frame.ValueColorSwatch
    swatch.colorProvider = self.pickerOptions.color
    swatch.valueTooltip = GameTooltip
    swatch.colorGeneration = (swatch.colorGeneration or 0) + 1
    local generation = swatch.colorGeneration
    swatch.curveMode = cfg.curve and true or false
    local initial = cfg.initialValue
    if type(initial) == "function" then
        initial = initial()
    end
    swatch.value = initial

    swatch:ClearAllPoints()
    local ax = anchorX or (C.Widget.ValueSwatchSize / 2 + C.Widget.ValueInset)
    swatch:SetPoint("CENTER", frame, "RIGHT", -Pixel:Snap(ax, frame:GetEffectiveScale()), 0)
    if cfg.allowNone then
        swatch:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    else
        swatch:RegisterForClicks("LeftButtonUp")
    end
    RenderSwatchColor(self, swatch, cfg.allowNone)

    swatch:SetScript("OnClick", function(_, button)
        if cfg.allowNone and button == "RightButton" then
            swatch.value = { none = true }
            RenderSwatchColor(Layout, swatch, true)
            if cfg.callback then
                cfg.callback(swatch.value)
            end
            return
        end
        local initialData
        if swatch.curveMode then
            initialData = swatch.value
        else
            local v = swatch.value or {}
            initialData = { r = v.r or 1, g = v.g or 1, b = v.b or 1, a = v.a or 1 }
            if v.type then
                initialData.type = v.type
            end
        end

        Layout:OpenColorPicker(swatch, {
            initialData = initialData,
            forceSingleColor = not swatch.curveMode,
            callback = function(result, wasCancelled)
                if generation ~= swatch.colorGeneration or wasCancelled or not result then
                    return
                end
                local newValue
                if swatch.curveMode then
                    if result.pins and #result.pins > 0 then
                        newValue = { pins = result.pins }
                        if result.desaturated ~= nil then
                            newValue.desaturated = result.desaturated
                        end
                    end
                else
                    local pin = result.pins and result.pins[1]
                    if pin and pin.color then
                        newValue = { r = pin.color.r, g = pin.color.g, b = pin.color.b, a = pin.color.a or 1 }
                        if pin.type then
                            newValue.type = pin.type
                        end
                    end
                end
                if not newValue then
                    return
                end
                swatch.value = newValue
                RenderSwatchColor(Layout, swatch, cfg.allowNone)
                if cfg.callback then
                    cfg.callback(newValue)
                end
            end,
        })
    end)

    if cfg.tooltip then
        swatch:SetScript("OnEnter", function(self)
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:SetText(cfg.tooltip, 1, 1, 1, 1, true)
            if cfg.allowNone and Layout.pickerOptions.color.removeTooltip then
                GameTooltip:AddLine(Layout.pickerOptions.color.removeTooltip, 0.6, 0.6, 0.6, true)
            end
            GameTooltip:Show()
        end)
        swatch:SetScript("OnLeave", GameTooltip_Hide)
    else
        swatch:SetScript("OnEnter", nil)
        swatch:SetScript("OnLeave", nil)
    end

    swatch:SetEnabled(Config.IsColorPickerAvailable(self.pickerOptions.color))
    swatch:Show()
    return swatch
end

-- [ VALUE-COLUMN SLIDER BUTTON ]---------------------------------------------------------------------------------------
local function BuildSliderPopup(layout, btn)
    local Constants = layout.configOptions.constants
    local Pixel = layout.configOptions.pixel
    local WHITE8x8 = Constants.Texture.White
    local popup = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
    popup:SetFrameStrata(Constants.Strata.FullscreenDialog)
    popup:SetFrameLevel(SLIDER_POPUP_LEVEL) -- strata-ok: slider popup above every dialog surface
    popup:SetSize(190, 58)
    popup:SetBackdrop({ bgFile = WHITE8x8, edgeFile = WHITE8x8, edgeSize = 1 })
    popup:SetBackdropColor(0.06, 0.06, 0.07, 0.98)
    popup:SetBackdropBorderColor(0.3, 0.3, 0.34, 1)
    popup:EnableMouse(true)
    popup:Hide()

    popup.Value = popup:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    popup.Value:SetPoint("TOP", 0, -7)

    local slider = CreateFrame("Slider", nil, popup)
    slider:SetOrientation("HORIZONTAL")
    slider:SetObeyStepOnDrag(true)
    slider:SetPoint("BOTTOMLEFT", 14, 12)
    slider:SetPoint("BOTTOMRIGHT", -14, 12)
    slider:SetHeight(16)
    local track = slider:CreateTexture(nil, "BACKGROUND")
    track:SetPoint("LEFT")
    track:SetPoint("RIGHT")
    track:SetHeight(Pixel:Multiple(3, slider:GetEffectiveScale()))
    track:SetColorTexture(0.25, 0.25, 0.28, 1)
    local fill = slider:CreateTexture(nil, "ARTWORK")
    fill:SetPoint("LEFT")
    fill:SetHeight(Pixel:Multiple(3, slider:GetEffectiveScale()))
    fill:SetColorTexture(0.3, 0.62, 1, 1)
    local thumb = slider:CreateTexture(nil, "OVERLAY")
    thumb:SetColorTexture(0.55, 0.78, 1, 1)
    thumb:SetSize(6, 16)
    slider:SetThumbTexture(thumb)
    popup.Slider = slider

    slider:SetScript("OnValueChanged", function(self, v)
        local c = btn.cfg
        if not c then
            return
        end
        local w = self:GetWidth()
        local lo, hi = self:GetMinMaxValues()
        fill:SetWidth(math.max(1, w * ((v - lo) / (hi - lo))))
        local txt = c.format and c.format(v) or tostring(v)
        popup.Value:SetText(txt)
        btn.value = v
        btn.Text:SetText(txt)
        if not btn.suppressCb and c.callback then
            c.callback(v)
        end
    end)

    popup:SetScript("OnShow", function(self)
        self:SetScript("OnUpdate", function(d)
            if not btn:IsVisible() then
                d:Hide()
                return
            end
            if
                not (d:IsMouseOver() or btn:IsMouseOver())
                and (IsMouseButtonDown("LeftButton") or IsMouseButtonDown("RightButton"))
            then
                d:Hide()
            end
        end)
    end)
    popup:SetScript("OnHide", function(self)
        self:SetScript("OnUpdate", nil)
    end)
    return popup
end

function Config:ApplyValueSliderButton(frame, cfg, anchorX)
    local Layout = self
    local Constants = self.configOptions.constants
    local Pixel = self.configOptions.pixel
    local GameTooltip = self.configOptions.tooltip
    local GameTooltip_Hide = self.configOptions.tooltipHide
    local WHITE8x8 = Constants.Texture.White
    if not frame.ValueSliderButton then
        local btn = CreateFrame("Button", nil, frame, "BackdropTemplate")
        btn:SetSize(SLIDER_BTN_W, Constants.Widget.ValueSwatchSize)
        btn:SetBackdrop({
            bgFile = WHITE8x8,
            edgeFile = WHITE8x8,
            edgeSize = Pixel:Multiple(1, btn:GetEffectiveScale()),
        })
        btn:SetBackdropColor(0.12, 0.12, 0.14, 1)
        btn:SetBackdropBorderColor(0, 0, 0, 1)
        btn.Text = btn:CreateFontString(nil, "OVERLAY", Constants.UI.LabelFont)
        btn.Text:SetPoint("CENTER")
        frame.ValueSliderButton = btn
    end

    local C = Constants
    local btn = frame.ValueSliderButton
    btn.valueTooltip = GameTooltip
    btn.cfg = cfg
    local initial = cfg.initialValue
    if type(initial) == "function" then
        initial = initial()
    end
    btn.value = initial or cfg.min
    btn.Text:SetText(cfg.format and cfg.format(btn.value) or tostring(btn.value))

    btn:ClearAllPoints()
    local ax = anchorX or (C.Widget.ValueInset + C.Widget.ValueSwatchSize + 3 + SLIDER_BTN_W / 2)
    btn:SetPoint("CENTER", frame, "RIGHT", -Pixel:Snap(ax, frame:GetEffectiveScale()), 0)

    btn:SetScript("OnClick", function()
        local cfg = btn.cfg
        if not cfg then
            return
        end
        if not btn.popup then
            btn.popup = BuildSliderPopup(self, btn)
        end
        local p = btn.popup
        p.Slider:SetMinMaxValues(cfg.min, cfg.max)
        p.Slider:SetValueStep(cfg.step)
        p.Slider:SetObeyStepOnDrag(true)
        btn.suppressCb = true
        p.Slider:SetValue(btn.value)
        btn.suppressCb = false
        p.Value:SetText(cfg.format and cfg.format(btn.value) or tostring(btn.value))
        p:ClearAllPoints()
        p:SetPoint("TOP", btn, "BOTTOM", 0, -2)
        p:SetShown(not p:IsShown())
    end)
    btn:SetScript("OnEnter", function(self)
        self:SetBackdropBorderColor(0.4, 0.4, 0.4, 1)
        if cfg.tooltip then
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:SetText(cfg.tooltip, 1, 1, 1, 1, true)
            GameTooltip:Show()
        end
    end)
    btn:SetScript("OnLeave", function(self)
        self:SetBackdropBorderColor(0, 0, 0, 1)
        GameTooltip_Hide()
    end)
    btn:Show()
    return btn
end

-- [ VALUE-COLUMN CHECKBOX ]--------------------------------------------------------------------------------------------
function Config:ApplyValueCheckbox(frame, cfg, anchorX)
    local Layout = self
    local Constants = self.configOptions.constants
    local Pixel = self.configOptions.pixel
    local GameTooltip = self.configOptions.tooltip
    local GameTooltip_Hide = self.configOptions.tooltipHide
    local WHITE8x8 = Constants.Texture.White
    if not frame.ValueCheckbox then
        frame.ValueCheckbox = CreateFrame("CheckButton", nil, frame, "UICheckButtonTemplate")
        frame.ValueCheckbox:SetSize(Constants.Widget.ValueCheckboxSize, Constants.Widget.ValueCheckboxSize)
    end

    local C = Constants
    local vcb = frame.ValueCheckbox
    vcb.valueTooltip = GameTooltip
    vcb:ClearAllPoints()
    local ax = anchorX or (C.Widget.ValueSwatchSize / 2 + C.Widget.ValueInset)
    vcb:SetPoint("CENTER", frame, "RIGHT", -Pixel:Snap(ax, frame:GetEffectiveScale()), 0)

    local initial = cfg.initialValue
    if type(initial) == "function" then
        initial = initial()
    end
    vcb:SetChecked(initial or false)

    local function RenderTooltip(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        local tt = cfg.tooltip
        if type(tt) == "function" then
            local title, subtext = tt(self:GetChecked())
            GameTooltip:SetText(title, 1, 1, 1, 1, true)
            if subtext then
                GameTooltip:AddLine(subtext, 0.6, 0.6, 0.6, true)
            end
        else
            GameTooltip:SetText(tt, 1, 1, 1, 1, true)
        end
        GameTooltip:Show()
    end

    vcb:SetScript("OnClick", function(self)
        if cfg.callback then
            cfg.callback(self:GetChecked())
        end
        if cfg.tooltip and GameTooltip:GetOwner() == self then
            RenderTooltip(self)
        end
    end)

    if cfg.tooltip then
        vcb:SetScript("OnEnter", RenderTooltip)
        vcb:SetScript("OnLeave", GameTooltip_Hide)
    else
        vcb:SetScript("OnEnter", nil)
        vcb:SetScript("OnLeave", nil)
    end

    vcb:Show()
    return vcb
end

function Config.ReleaseValueControls(control)
    local swatch = control.ValueColorSwatch
    if swatch then
        ReleaseSwatch(swatch)
    end
    local checkbox = control.ValueCheckbox
    if checkbox then
        HideTooltip(checkbox)
        checkbox:SetScript("OnClick", nil)
        checkbox:SetScript("OnEnter", nil)
        checkbox:SetScript("OnLeave", nil)
        checkbox:Hide()
    end
    local slider = control.ValueSliderButton
    if slider then
        HideTooltip(slider)
        slider.cfg = nil
        slider:SetScript("OnClick", nil)
        slider:SetScript("OnEnter", nil)
        slider:SetScript("OnLeave", nil)
        if slider.popup then
            slider.popup:Hide()
        end
        slider:Hide()
    end
end
