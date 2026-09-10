local _, addon = ...
local Config = addon.LibOrbitUI.Config

-- [ COLOR PICKER WIDGET ] ---------------------------------------------------------------------------------------------
local COMPACT_SWATCH_SIZE = 21
local COMPACT_ROW_HEIGHT = 26
local WIDGET_SIZE = { width = 260, height = 32 }

function Config:CreateColorPicker(parent, label, initialColor, callback, opts)
    local Layout = self
    local Constants = self.configOptions.constants
    local Pixel = self.configOptions.pixel
    opts = opts or {}
    if not self.colorPool then
        self.colorPool = {}
    end
    local frame = table.remove(self.colorPool)

    if not frame then
        frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
        frame.OrbitType = "Color"

        frame.Label = frame:CreateFontString(nil, "ARTWORK", Constants.UI.LabelFont)

        frame.Swatch = CreateFrame("Button", nil, frame, "BackdropTemplate")
        frame.Swatch:SetBackdrop({
            bgFile = Constants.Texture.White,
            edgeFile = Constants.Texture.White,
            edgeSize = Pixel:Multiple(1, frame.Swatch:GetEffectiveScale()),
        })
        frame.Swatch:SetBackdropBorderColor(0, 0, 0, 1)
        frame.Swatch:SetBackdropColor(0, 0, 0, 0)

        frame.Swatch.Checkerboard = frame.Swatch:CreateTexture(nil, "BACKGROUND")
        Pixel:Point(frame.Swatch.Checkerboard, "TOPLEFT", 1, -1)
        Pixel:Point(frame.Swatch.Checkerboard, "BOTTOMRIGHT", -1, 1)
        Config.PaintCheckerboard(frame.Swatch.Checkerboard, self.pickerOptions.color.checkerboard)
        frame.Swatch.Checkerboard:SetHorizTile(true)
        frame.Swatch.Checkerboard:SetVertTile(true)

        frame.Swatch.Color = frame.Swatch:CreateTexture(nil, "ARTWORK")
        Pixel:Point(frame.Swatch.Color, "TOPLEFT", 1, -1)
        Pixel:Point(frame.Swatch.Color, "BOTTOMRIGHT", -1, 1)
        frame.Swatch.Color:SetColorTexture(1, 1, 1, 1)
    end

    frame:SetParent(parent)
    frame.colorProvider = self.pickerOptions.color
    frame.configUnavailable = not Config.IsColorPickerAvailable(frame.colorProvider)
    frame.colorGeneration = (frame.colorGeneration or 0) + 1
    local generation = frame.colorGeneration
    frame.Swatch:SetScript("OnClick", function()
        local initData = { r = frame.r, g = frame.g, b = frame.b, a = frame.a }
        if frame.pinType then
            initData.type = frame.pinType
        end
        Layout:OpenColorPicker(frame, {
            initialData = initData,
            forceSingleColor = true,
            callback = function(result, wasCancelled)
                if generation ~= frame.colorGeneration or wasCancelled then
                    return
                end
                local pin = result and result.pins and result.pins[1]
                if pin and pin.color then
                    frame.UpdateColor(pin.color.r, pin.color.g, pin.color.b, pin.color.a, pin.type)
                elseif frame.allowClear then
                    frame.ClearColor()
                end
            end,
        })
    end)
    frame.Swatch:SetEnabled(not frame.configUnavailable)

    -- Store per-acquire so the create-time OnClick (installed once) reads this call's value, not the first caller's.
    frame.allowClear = opts.allowClear
    frame.OrbitHalfWidth = not opts.compact

    if initialColor and initialColor.pins then
        local p = initialColor.pins[1]
        initialColor = (p and p.color) and { r = p.color.r, g = p.color.g, b = p.color.b, a = p.color.a, type = p.type }
            or nil
    end
    local c = initialColor or { r = 1, g = 1, b = 1, a = 1 }
    frame.pinType = c.type
    frame.r, frame.g, frame.b, frame.a = self.pickerOptions.color.resolveValue(c)
    frame.oldR, frame.oldG, frame.oldB, frame.oldA = frame.r, frame.g, frame.b, frame.a
    frame.Swatch.Color:SetVertexColor(frame.r, frame.g, frame.b, frame.a)

    frame.UpdateColor = function(r, g, b, a, pinType)
        frame.r, frame.g, frame.b, frame.a = r, g, b, a
        frame.pinType = pinType
        frame.Swatch.Color:SetVertexColor(r, g, b, a)
        local result = { r = r, g = g, b = b, a = a }
        if pinType then
            result.type = pinType
        end
        if callback then
            callback(result)
        end
    end

    frame.ClearColor = function()
        if callback then
            callback(nil)
        end
    end

    frame.SetColorQuiet = function(_, r, g, b, a)
        frame.r, frame.g, frame.b, frame.a = r, g, b, a
        frame.Swatch.Color:SetVertexColor(r, g, b, a)
    end

    local C = Constants

    frame.Label:SetText(label)
    frame.Label:SetJustifyH("LEFT")
    frame.Label:ClearAllPoints()
    frame.Swatch:ClearAllPoints()

    if opts.compact then
        frame:SetHeight(COMPACT_ROW_HEIGHT)
        frame.Swatch:SetSize(COMPACT_SWATCH_SIZE, COMPACT_SWATCH_SIZE)
        frame.Swatch:SetPoint("LEFT", frame, "LEFT", 0, 0)

        frame.Label:SetWidth(0)
        frame.Label:SetPoint("LEFT", frame.Swatch, "RIGHT", 4, 0)

        frame:SetSize(
            Pixel:Snap(COMPACT_SWATCH_SIZE + 4 + frame.Label:GetStringWidth(), frame:GetEffectiveScale()),
            COMPACT_ROW_HEIGHT
        )
    else
        frame.Swatch:SetSize(C.Widget.ValueSwatchSize, C.Widget.ValueSwatchSize)
        frame.Swatch:SetPoint("LEFT", frame, "LEFT", 0, 0)

        frame.Label:SetWidth(C.Widget.LabelWidth)
        frame.Label:SetPoint("LEFT", frame.Swatch, "RIGHT", C.Widget.LabelGap, 0)

        frame:SetSize(WIDGET_SIZE.width, WIDGET_SIZE.height)
    end

    return frame
end
