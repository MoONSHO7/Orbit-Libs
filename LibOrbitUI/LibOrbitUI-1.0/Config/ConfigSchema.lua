local _, addon = ...
local Config = addon.LibOrbitUI.Config
local CALLBACK_KEYS = {
    onChange = true,
    onClick = true,
    onTabSelected = true,
    onCopy = true,
    onReset = true,
    onDelete = true,
    callback = true,
    action = true,
}
local VALUE_CONTROLS = { "valueColor", "valueCheckbox", "valueSlider" }

function Config.GuardCallback(callback, isCurrent)
    return function(...)
        if isCurrent() then
            return callback(...)
        end
    end
end

function Config.BindDefinition(definition, isCurrent)
    local bound = {}
    for key, value in pairs(definition) do
        bound[key] = CALLBACK_KEYS[key] and type(value) == "function" and Config.GuardCallback(value, isCurrent)
            or value
    end
    for _, key in ipairs(VALUE_CONTROLS) do
        if definition[key] then
            bound[key] = Config.BindDefinition(definition[key], isCurrent)
        end
    end
    local function BindOptions(options)
        local boundOptions = {}
        for index, option in ipairs(options) do
            boundOptions[index] = type(option) == "table" and Config.BindDefinition(option, isCurrent) or option
        end
        return boundOptions
    end
    if type(definition.options) == "table" then
        bound.options = BindOptions(definition.options)
    elseif type(definition.options) == "function" then
        bound.options = function()
            return BindOptions(definition.options())
        end
    end
    return bound
end

function Config.ResolveValue(spec, control)
    local value
    if control.getValue then
        value = control.getValue()
    elseif spec.get then
        value = spec.get(control.key)
    end
    if value == nil then
        value = control.default
    end
    return value
end

function Config.CommitValue(spec, control, value)
    if control.onChange then
        control.onChange(value)
    else
        assert(spec.set, "LibOrbitUI config needs a setting writer")
        spec.set(control.key, value)
    end
    if spec.onChange then
        spec.onChange(control.key, value)
    end
end

function Config.IsControlVisible(control)
    local value = control.visible
    if type(value) == "function" then
        value = value()
    end
    if value == false then
        return false
    end
    local predicate = control.visibleIf
    if type(predicate) == "function" then
        return not not predicate()
    end
    return predicate == nil or not not predicate
end

function Config.IsControlEnabled(control)
    local value = control.isEnabled
    if type(value) == "function" then
        value = value()
    end
    return value ~= false
end

function Config.ValidateControl(control, layout)
    assert(type(control.type) == "string", "LibOrbitUI control needs a widget type")
    if layout then
        assert(layout:HasWidgetType(control.type), "Unregistered LibOrbitUI widget type: " .. control.type)
    end
    if control.type ~= "spacer" and control.type ~= "label" and control.type ~= "description" then
        assert(type(control.label or control.text) == "string", "LibOrbitUI control needs a localized label")
    end
    if control.type == "slider" then
        assert(type(control.min) == "number" and type(control.max) == "number" and control.max > control.min)
        assert(type(control.step) == "number" and control.step > 0)
    elseif control.type == "button" then
        assert(type(control.onClick) == "function", "LibOrbitUI button needs a callback")
    end
end
