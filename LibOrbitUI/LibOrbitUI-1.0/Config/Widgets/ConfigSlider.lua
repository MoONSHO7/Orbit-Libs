local _, addon = ...
local Config = addon.LibOrbitUI.Config
local math_floor = math.floor
local STEPPER_DELAY = 0.1
local SLIDER_HEIGHT = 32

-- [ SLIDER WIDGET ]----------------------------------------------------------------------------------------------------
function Config:CreateSlider(parent, label, min, max, step, formatter, initialValue, callback, options)
    local Constants = self.configOptions.constants
    if not self.sliderPool then
        self.sliderPool = {}
    end
    local frame = table.remove(self.sliderPool)

    if not frame then
        frame = CreateFrame("Frame", nil, parent, "EditModeSettingSliderTemplate")
        frame.OrbitType = "Slider"

        frame.OnSliderValueChanged = function() end
        frame.OnSliderInteractStart = function() end
        frame.OnSliderInteractEnd = function() end

        frame.Value = frame:CreateFontString(nil, "OVERLAY", Constants.UI.ValueFont)
        frame.Value:SetTextColor(1, 0.82, 0, 1)
    end

    frame:SetParent(parent)

    local baseFormatter = formatter or function(value)
        return math_floor(value * 10 or 0) / 10
    end
    if options and options.mergeAtZero then
        frame.valueFormatter = function(value)
            if math_floor(value + 0.5) == 0 then
                local merged = self.configOptions.mergedLabel
                return type(merged) == "function" and merged() or merged
            end
            return baseFormatter(value)
        end
    else
        frame.valueFormatter = baseFormatter
    end
    frame.OnOrbitChange = callback
    -- Stepper hooks persist across pool reuse; the hook body checks this so a normal-mode slider doesn't double-fire.
    frame._updateOnRelease = options and options.updateOnRelease or false

    if frame.Slider then
        -- Unregister before re-registering — pool reuse would otherwise stack callbacks each acquire.
        if frame._callbackRegistered then
            frame.Slider:UnregisterCallback("OnValueChanged", frame)
        end

        -- Slider:Init fires OnValueChanged synchronously; guard prevents that fire from reaching onChange.
        frame._isInitializing = true

        frame.Slider:RegisterCallback("OnValueChanged", function(_, value)
            if frame.Value and frame.valueFormatter then
                frame.Value:SetText(frame.valueFormatter(value))
            end

            if frame._isInitializing then
                return
            end

            if options and options.updateOnRelease then
                return
            end

            if frame.OnOrbitChange then
                frame.OnOrbitChange(value)
            end
        end, frame)
        frame._callbackRegistered = true

        local steps = (max - min) / step
        local startValue = initialValue or min
        frame.Slider:Init(startValue, min, max, steps, {})

        frame._isInitializing = false

        local innerSlider = frame.Slider.Slider
        if innerSlider then
            if options and options.updateOnRelease then
                innerSlider:SetScript("OnMouseUp", function()
                    local val = innerSlider:GetValue()
                    if frame.OnOrbitChange then
                        frame.OnOrbitChange(val)
                    end
                end)
            else
                innerSlider:SetScript("OnMouseUp", nil)
            end

            for _, region in pairs({ innerSlider:GetRegions() }) do
                if region:GetObjectType() == "FontString" then
                    region:Hide()
                end
            end
        end

        -- HookScript with flag guard — SetScript would overwrite Blizzard's increment/decrement handler.
        local back = frame.Back or (frame.Slider and frame.Slider.Back)
        local forward = frame.Forward or (frame.Slider and frame.Slider.Forward)

        if options and options.updateOnRelease then
            local function createStepperCallback()
                return function()
                    if not frame._updateOnRelease then
                        return
                    end
                    if frame._stepperTimer then
                        frame._stepperTimer:Cancel()
                    end
                    frame._stepperTimer = C_Timer.NewTimer(STEPPER_DELAY, function()
                        frame._stepperTimer = nil
                        local val = innerSlider and innerSlider:GetValue() or 0
                        if frame.OnOrbitChange then
                            frame.OnOrbitChange(val)
                        end
                    end)
                end
            end

            if back and not back._orbitHooked then
                back:HookScript("OnClick", createStepperCallback())
                back._orbitHooked = true
            end
            if forward and not forward._orbitHooked then
                forward:HookScript("OnClick", createStepperCallback())
                forward._orbitHooked = true
            end
        end

        if frame.Value then
            frame.Value:SetText(frame.valueFormatter(startValue))
        end
    end

    local C = Constants

    if frame.Label then
        frame.Label:SetText(label)
        frame.Label:SetFontObject(Constants.UI.LabelFont)
        frame.Label:SetWidth(C.Widget.LabelWidth)
        frame.Label:SetJustifyH("LEFT")
        frame.Label:ClearAllPoints()
        frame.Label:SetPoint("LEFT", frame, "LEFT", 0, 0)
    end

    if frame.Slider then
        frame.Slider:ClearAllPoints()
        frame.Slider:SetPoint("LEFT", frame.Label, "RIGHT", C.Widget.LabelGap, 0)
        frame.Slider:SetPoint("RIGHT", frame, "RIGHT", -C.Widget.ValueWidth, 0)
    end

    local valueColorSwatch
    if options and options.valueColor then
        valueColorSwatch = self:ApplyValueColorSwatch(frame, options.valueColor)
        if valueColorSwatch then
            valueColorSwatch:ClearAllPoints()
            valueColorSwatch:SetPoint("LEFT", frame.Slider, "RIGHT", C.Widget.LabelGap, 0)
        end
    elseif frame.ValueColorSwatch then
        frame.ValueColorSwatch:Hide()
    end

    if frame.Value then
        frame.Value:ClearAllPoints()
        local valueWidth = C.Widget.ValueWidth - C.Widget.ValueInset
        if valueColorSwatch then
            valueWidth = valueWidth - C.Widget.ValueSwatchSize - C.Widget.LabelGap * 2
        end
        frame.Value:SetPoint("RIGHT", frame, "RIGHT", -C.Widget.ValueInset, 0)
        frame.Value:SetWidth(valueWidth)
        frame.Value:SetJustifyH("RIGHT")
    end

    frame:SetHeight(SLIDER_HEIGHT)
    return frame
end
