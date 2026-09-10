local _, addon = ...
local Config = addon.LibOrbitUI.Config
local CHECKER_GRAY = 0.35

local function ResolveValue(value)
    value = value or {}
    return value.r or 1, value.g or 1, value.b or 1, value.a or 1
end

function Config.PaintCheckerboard(texture, path)
    if path then
        texture:SetTexture(path, "REPEAT", "REPEAT")
    else
        texture:SetColorTexture(CHECKER_GRAY, CHECKER_GRAY, CHECKER_GRAY, 1)
    end
end

function Config.IsColorPickerAvailable(provider)
    return provider.open ~= nil and (not provider.isAvailable or provider.isAvailable())
end

local function ReleaseColor(control)
    control.colorGeneration = (control.colorGeneration or 0) + 1
    if control.colorProvider.close then
        control.colorProvider.close(control)
    end
    control.Swatch:SetScript("OnClick", nil)
    control.UpdateColor, control.ClearColor, control.SetColorQuiet = nil, nil, nil
end

local function ReleaseCurve(control)
    control.colorGeneration = (control.colorGeneration or 0) + 1
    if control.colorProvider.close then
        control.colorProvider.close(control)
    end
    control:SetScript("OnClick", nil)
    control.onChangeCallback, control.curveData = nil, nil
end

local function ReleaseMedia(control)
    if control.Dropdown then
        control.Dropdown:Hide()
    end
    control.fontCallback, control.textureCallback = nil, nil
end

function Config.InstallPickerWidgets(layout, options)
    options = options or {}
    local color = options.color or {}
    local resolveValue = color.resolveValue or ResolveValue
    layout.pickerOptions = {
        color = {
            open = color.open,
            close = color.close,
            isAvailable = color.isAvailable,
            resolveValue = resolveValue,
            resolvePin = color.resolvePin or function(pin)
                local r, g, b, a = resolveValue(pin.color)
                return { r = r, g = g, b = b, a = a }
            end,
            checkerboard = color.checkerboard,
            removeTooltip = color.removeTooltip,
        },
        media = options.media,
    }
    layout.OpenColorPicker = Config.OpenColorPicker
    layout.ApplyValueColorSwatch = Config.ApplyValueColorSwatch
    layout.ApplyValueSliderButton = Config.ApplyValueSliderButton
    layout.ApplyValueCheckbox = Config.ApplyValueCheckbox
    layout.CreateColorPicker = Config.CreateColorPicker
    layout.CreateColorCurvePicker = Config.CreateColorCurvePicker
    layout:RegisterControlPool("Color", "colorPool", ReleaseColor)
    layout:RegisterControlPool("ColorCurve", "colorCurvePool", ReleaseCurve)
    layout:RegisterWidgetType("color", function(container, def, getValue, callback)
        return layout:CreateColorPicker(container, def.label, getValue(), callback)
    end)
    layout:RegisterWidgetType("solidcolor", function(container, def, getValue, callback)
        return layout:CreateColorPicker(container, def.label, getValue(), callback, {
            compact = def.compact,
            allowClear = def.allowClear,
        })
    end)
    layout:RegisterWidgetType("colorcurve", function(container, def, getValue, callback)
        local widget = layout:CreateColorCurvePicker(container, def.label, getValue(), callback, def.valueCheckbox)
        widget.singleColorMode = def.singleColor
        widget.hasDesaturation = def.hasDesaturation
        return widget
    end)
    if options.media then
        layout.CreateFontPicker = Config.CreateFontPicker
        layout.CreateTexturePicker = Config.CreateTexturePicker
        layout:RegisterControlPool("Font", "fontPool", ReleaseMedia)
        layout:RegisterControlPool("Texture", "texturePool", ReleaseMedia)
        layout:RegisterWidgetType("font", function(container, def, getValue, callback)
            local widget = layout:CreateFontPicker(container, def.label, getValue(), callback, def.valueColor)
            layout:AttachLabelTooltip(widget, def.label, def.tooltip)
            return widget
        end)
        layout:RegisterWidgetType("texture", function(container, def, getValue, callback)
            local widget = layout:CreateTexturePicker(
                container,
                def.label,
                getValue(),
                callback,
                def.previewColor,
                def.valueCheckbox,
                def.valueColor,
                def.mediaCategory
            )
            layout:AttachLabelTooltip(widget, def.label, def.tooltip)
            return widget
        end)
    end
    return layout
end
