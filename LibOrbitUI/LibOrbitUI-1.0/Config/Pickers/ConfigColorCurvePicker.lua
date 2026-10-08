local _, addon = ...
local Config = addon.LibOrbitUI.Config

-- [ COLOR CURVE PICKER WIDGET ] ---------------------------------------------------------------------------------------
local WIDGET_HEIGHT = 32

function Config:CreateColorCurvePicker(parent, label, initialCurveData, callback, valueCheckboxCfg)
    local Layout = self
    local Constants = self.configOptions.constants
    local Pixel = self.configOptions.pixel
    if not self.colorCurvePool then
        self.colorCurvePool = {}
    end
    local frame = table.remove(self.colorCurvePool)

    if not frame then
        frame = CreateFrame("Button", nil, parent, "BackdropTemplate")
        frame.OrbitType = "ColorCurve"

        frame.Label = frame:CreateFontString(nil, "ARTWORK", Constants.UI.LabelFont)

        frame.GradientBar = CreateFrame("Frame", nil, frame, "BackdropTemplate")
        frame.GradientBar:SetBackdrop({
            bgFile = Constants.Texture.White,
            edgeFile = Constants.Texture.White,
            edgeSize = Pixel:Multiple(1, frame.GradientBar:GetEffectiveScale()),
        })
        frame.GradientBar:SetBackdropBorderColor(0, 0, 0, 1)
        frame.GradientBar:SetBackdropColor(0, 0, 0, 0)

        frame.Checkerboard = frame.GradientBar:CreateTexture(nil, "BACKGROUND")
        Pixel:Point(frame.Checkerboard, "TOPLEFT", 1, -1)
        Pixel:Point(frame.Checkerboard, "BOTTOMRIGHT", -1, 1)
        Config.PaintCheckerboard(frame.Checkerboard, self.pickerOptions.color.checkerboard)
        frame.Checkerboard:SetHorizTile(true)
        frame.Checkerboard:SetVertTile(true)

        frame.GradientTexture = frame.GradientBar:CreateTexture(nil, "ARTWORK")
        Pixel:Point(frame.GradientTexture, "TOPLEFT", 1, -1)
        Pixel:Point(frame.GradientTexture, "BOTTOMRIGHT", -1, 1)
        frame.GradientTexture:SetTexture(Constants.Texture.White)
    end

    frame:SetParent(parent)
    frame.colorProvider = self.pickerOptions.color
    frame.configUnavailable = not Config.IsColorPickerAvailable(frame.colorProvider)
    frame.colorGeneration = (frame.colorGeneration or 0) + 1
    local generation = frame.colorGeneration
    frame:SetScript("OnClick", function(self)
        Layout:OpenColorPicker(self, {
            initialData = self.curveData,
            forceSingleColor = self.singleColorMode,
            hasDesaturation = self.hasDesaturation,
            callback = function(result, wasCancelled)
                if generation ~= self.colorGeneration or wasCancelled then
                    return
                end
                if result and result.pins and #result.pins > 0 then
                    self.curveData = { pins = result.pins }
                    if result.desaturated ~= nil then
                        self.curveData.desaturated = result.desaturated
                    end
                else
                    self.curveData = nil
                end
                self:UpdatePreview()
                if self.onChangeCallback then
                    self.onChangeCallback(self.curveData)
                end
            end,
        })
    end)
    frame:SetEnabled(not frame.configUnavailable)
    frame.singleColorMode, frame.hasDesaturation = nil, nil

    frame.curveData = initialCurveData
    frame.onChangeCallback = callback

    if not frame.UpdatePreview then
        frame.UpdatePreview = function(self)
            Config.PaintColorCurve(Layout, self.GradientTexture, self.curveData)
        end
    end

    frame:UpdatePreview()

    local C = Constants

    frame.Label:SetText(label)
    frame.Label:SetWidth(C.Widget.LabelWidth)
    frame.Label:SetJustifyH("LEFT")
    frame.Label:ClearAllPoints()
    -- Frame-relative, not bar-relative: Canvas's ApplyCompactLayout re-anchors the bar to the label, which would cycle.
    frame.Label:SetPoint("LEFT", frame, "LEFT", C.Widget.ValueSwatchSize + C.Widget.LabelGap, 0)

    frame.GradientBar:ClearAllPoints()
    frame.GradientBar:SetSize(C.Widget.ValueSwatchSize, C.Widget.ValueSwatchSize)
    frame.GradientBar:SetPoint("LEFT", frame, "LEFT", 0, 0)

    if valueCheckboxCfg then
        self:ApplyValueCheckbox(frame, valueCheckboxCfg)
    elseif frame.ValueCheckbox then
        frame.ValueCheckbox:Hide()
    end

    frame.OrbitHalfWidth = not valueCheckboxCfg
    frame:SetSize(260, WIDGET_HEIGHT)
    return frame
end
