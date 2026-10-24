local _, addon = ...
local Config = addon.LibOrbitUI.Config
local math_floor = math.floor
local STEPPER_DELAY = 0.1
local SLIDER_HEIGHT = 32
local PRESS_ACTIVE = "active"
local PRESS_RELEASING = "releasing"
local PRESS_CANCELLED = "cancelled"

-- [ SLIDER LIFECYCLE ]-------------------------------------------------------------------------------------------------
local function InitializeSlider(frame, value, minValue, maxValue, step)
    frame._sliderMin, frame._sliderMax, frame._sliderStep = minValue, maxValue, step
    -- Slider:Init fires OnValueChanged synchronously; guard prevents that fire from reaching onChange.
    frame._isInitializing = true
    frame.Slider:Init(value, minValue, maxValue, (maxValue - minValue) / step, {})
    frame._isInitializing = false
    if frame.Value then
        frame.Value:SetText(frame.valueFormatter(value))
    end
end

local function CancelStepperCommit(frame)
    if frame._stepperTimer then
        frame._stepperTimer:Cancel()
        frame._stepperTimer = nil
    end
end

local function CancelPendingCommit(frame)
    CancelStepperCommit(frame)
    local press = frame._sliderPress
    if press == PRESS_ACTIVE or press == PRESS_RELEASING then
        frame._sliderPress = PRESS_CANCELLED
        if press == PRESS_ACTIVE and frame._onDragStop then
            frame._onDragStop(true)
        end
    end
end

local function SetCallbacks(frame, callback, onDragStart, onDragStop)
    CancelPendingCommit(frame)
    frame.OnOrbitChange = callback
    frame._onDragStart, frame._onDragStop = onDragStart, onDragStop
end

local function Reinitialize(frame, value, minValue, maxValue, step)
    CancelStepperCommit(frame)
    InitializeSlider(
        frame,
        value,
        minValue or frame._sliderMin,
        maxValue or frame._sliderMax,
        step or frame._sliderStep
    )
end

local function BeginPress(frame, inner, button)
    if frame._sliderPress == PRESS_ACTIVE or not inner:IsEnabled() then
        return
    end
    frame._sliderPress, frame._sliderPressButton = PRESS_ACTIVE, button
    if frame._onDragStart then
        frame._onDragStart()
    end
end

-- The drag stop runs before the commit, as in the range slider; it may cancel the commit or rebind the slider.
local function EndPress(frame, inner, button)
    if button ~= frame._sliderPressButton then
        return
    end
    local value = inner:GetValue()
    if frame._sliderPress == PRESS_ACTIVE then
        frame._sliderPress = PRESS_RELEASING
        if frame._onDragStop then
            frame._onDragStop(false)
        end
    end
    -- Cancellation, rebinding or pool release during the stop leaves another state, so only this press commits.
    local committed = frame._sliderPress == PRESS_RELEASING
    frame._sliderPress, frame._sliderPressButton = nil, nil
    if frame._updateOnRelease and committed and frame.OnOrbitChange then
        frame.OnOrbitChange(value)
    end
end

local function ScheduleStepperCommit(frame)
    if not frame._updateOnRelease then
        return
    end
    CancelStepperCommit(frame)
    frame._stepperTimer = C_Timer.NewTimer(STEPPER_DELAY, function()
        frame._stepperTimer = nil
        local inner = frame.Slider and frame.Slider.Slider
        local value = inner and inner:GetValue() or 0
        if frame.OnOrbitChange then
            frame.OnOrbitChange(value)
        end
    end)
end

-- Hooks keep Blizzard's own mouse and stepper handlers; their bodies read per-binding state, so pooling reuses them.
local function InstallLifecycle(frame)
    frame.SetCallbacks = SetCallbacks
    frame.Reinitialize = Reinitialize
    frame.CancelPendingCommit = CancelPendingCommit
    frame:HookScript("OnHide", CancelPendingCommit)
    local stepper = frame.Slider
    if not stepper then
        return
    end
    local inner = stepper.Slider
    if inner then
        inner:HookScript("OnMouseDown", function(slider, button)
            BeginPress(frame, slider, button)
        end)
        inner:HookScript("OnMouseUp", function(slider, button)
            EndPress(frame, slider, button)
        end)
    end
    local function Step()
        ScheduleStepperCommit(frame)
    end
    if stepper.Back then
        stepper.Back:HookScript("OnClick", Step)
    end
    if stepper.Forward then
        stepper.Forward:HookScript("OnClick", Step)
    end
end

function Config.ReleaseSlider(control)
    if control.Slider and control.Slider.UnregisterCallback then
        control.Slider:UnregisterCallback("OnValueChanged", control)
    end
    control._callbackRegistered = nil
    control._updateOnRelease = false
    SetCallbacks(control)
    control._sliderPress, control._sliderPressButton = nil, nil
end

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
        frame._onValueChanged = function(_, value)
            if frame.Value and frame.valueFormatter then
                frame.Value:SetText(frame.valueFormatter(value))
            end
            if frame._isInitializing or frame._updateOnRelease then
                return
            end
            if frame.OnOrbitChange then
                frame.OnOrbitChange(value)
            end
        end
        InstallLifecycle(frame)
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
    frame:SetCallbacks(callback, options and options.onDragStart, options and options.onDragStop)
    frame._updateOnRelease = options and options.updateOnRelease or false

    if frame.Slider then
        -- Unregister before re-registering — pool reuse would otherwise stack callbacks each acquire.
        if frame._callbackRegistered then
            frame.Slider:UnregisterCallback("OnValueChanged", frame)
        end
        frame.Slider:RegisterCallback("OnValueChanged", frame._onValueChanged, frame)
        frame._callbackRegistered = true

        InitializeSlider(frame, initialValue or min, min, max, step)

        local innerSlider = frame.Slider.Slider
        if innerSlider then
            for _, region in pairs({ innerSlider:GetRegions() }) do
                if region:GetObjectType() == "FontString" then
                    region:Hide()
                end
            end
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
