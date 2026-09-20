local _, addon = ...
local UI = addon.LibOrbitUI
local STANDARD_EVENTS = { "PLAYER_ENTERING_WORLD", "DISPLAY_SIZE_CHANGED", "UI_SCALE_CHANGED" }
local VISIBILITY_EVENTS = {
    "PLAYER_REGEN_DISABLED",
    "PLAYER_REGEN_ENABLED",
    "PET_BATTLE_OPENING_START",
    "PET_BATTLE_CLOSE",
    "PLAYER_MOUNT_DISPLAY_CHANGED",
}
local VISIBILITY_UNIT_EVENTS = { "UNIT_ENTERED_VEHICLE", "UNIT_EXITED_VEHICLE" }

UI.Controller = {}
local ControllerMixin = {}

function ControllerMixin:GetSetting(index, key)
    return self.store:Get(index, key)
end

function ControllerMixin:SetSetting(index, key, value)
    local ok, err = self.store:Set(index, key, value)
    if ok and self.onSettingChanged then
        self.onSettingChanged(self, type(index) == "number" and index or 1, key, value)
    end
    return ok, err
end

function ControllerMixin:GetLifecycleGeneration()
    return self.generation
end

function ControllerMixin:IsActive()
    return self.active
end

function ControllerMixin:IsEnabled()
    if self.alwaysEnabled then
        return true
    end
    return self:GetSetting(1, "Enabled") ~= false
end

function ControllerMixin:IsProfileSuppressed()
    return self.profileSuppressed == true
end

function ControllerMixin:RegisterUpdate(callback, interval)
    assert(type(callback) == "function", "LibOrbitUI update callback is required")
    assert(
        interval == nil or (type(interval) == "number" and interval > 0 and interval < math.huge),
        "LibOrbitUI update interval must be positive"
    )
    if not self.updateFrame then
        self.updateFrame = CreateFrame("Frame")
    end
    local accumulated = 0
    local wrapped = UI.Callbacks:Wrap(callback, self.name .. ".OnUpdate")
    self.updateFrame:SetScript("OnUpdate", function(_, elapsed)
        if not self.active then
            return
        end
        accumulated = accumulated + elapsed
        if interval and accumulated < interval then
            return
        end
        elapsed, accumulated = accumulated, 0
        wrapped(self, elapsed)
    end)
    self.updateFrame:Show()
end

function ControllerMixin:RemoveUpdate()
    if self.updateFrame then
        self.updateFrame:SetScript("OnUpdate", nil)
        self.updateFrame:Hide()
    end
end

function ControllerMixin:Subscribe(event, callback, boundSelf)
    if boundSelf then
        return self.eventBus:On(event, function(_, ...)
            return callback(boundSelf, ...)
        end, self)
    end
    return self.eventBus:On(event, callback, self)
end

local function ApplyActive(self)
    if self.active then
        self:ApplySettings()
    end
end

local function ApplyVisibility(self)
    if self.active and (not self.shouldApplyVisibility or self.shouldApplyVisibility(self)) then
        self:ApplySettings()
    end
end

function ControllerMixin:RegisterStandardEvents()
    if self.standardEvents then
        return
    end
    for _, event in ipairs(STANDARD_EVENTS) do
        self:Subscribe(event, ApplyActive)
    end
    self.standardEvents = true
end

function ControllerMixin:RegisterVisibilityEvents()
    if self.visibilityEvents then
        return
    end
    for _, event in ipairs(VISIBILITY_EVENTS) do
        self:Subscribe(event, ApplyVisibility)
    end
    for _, event in ipairs(VISIBILITY_UNIT_EVENTS) do
        self:Subscribe(event, function(owner, unit)
            if unit == "player" then
                ApplyVisibility(owner)
            end
        end)
    end
    self.visibilityEvents = true
end

function ControllerMixin:Disable()
    if not self.loaded or not (self.active or self.needsDisable) then
        return true
    end
    self.generation = self.generation + 1
    self.active = false
    self.needsDisable = false
    self.disabling = true
    local ok, err = true, nil
    if self.OnDisable then
        ok, err = pcall(self.OnDisable, self)
    end
    self.disabling = false
    self:RemoveUpdate()
    self.eventBus:OffContext(self)
    self.standardEvents, self.visibilityEvents = false, false
    if not ok then
        self.needsDisable = true
        UI.Callbacks:LogError(self.name, "OnDisable", err)
    end
    return ok, err
end

function ControllerMixin:Enable()
    if self.active then
        return true
    end
    if self.loadError then
        return nil, self.loadError
    end
    assert(
        not self.activating and not self.disabling,
        "LibOrbitUI controller lifecycle transition is already in progress"
    )
    if self.needsDisable then
        local ok, err = self:Disable()
        if not ok then
            return nil, err
        end
    end
    self.activating = true
    local ok, err = pcall(function()
        if not self.loaded then
            if self.OnLoad then
                self:OnLoad()
            end
            self.loaded = true
        end
        self.needsDisable = true
        if not self.attached then
            if self.onLoaded then
                self.onLoaded(self)
            end
            self.attached = true
        end
        self.generation = self.generation + 1
        if self.OnEnable then
            self:OnEnable()
        end
        if self.needsDisable then
            self.active = true
            self:ApplySettings()
        end
    end)
    self.activating = false
    if not ok then
        if self.loaded then
            self:Disable()
        else
            -- Named-frame construction cannot be retried safely after a partial OnLoad failure.
            self.loadError = err
            self.generation = self.generation + 1
            self:RemoveUpdate()
            self.eventBus:OffContext(self)
            self.standardEvents, self.visibilityEvents = false, false
        end
        UI.Callbacks:LogError(self.name, "Enable", err)
        return nil, err
    end
    return self.active
end

table.freeze(ControllerMixin)

function UI.Controller:Create(spec)
    assert(type(spec.name) == "string" and spec.name ~= "", "LibOrbitUI controller name is required")
    local defaults = spec.defaults or {}
    local alwaysEnabled = spec.alwaysEnabled == true
    if alwaysEnabled then
        defaults.Enabled = nil
    elseif defaults.Enabled == nil then
        defaults.Enabled = true
    end
    local indexed = spec.indexDefaults or {}
    return Mixin({
        name = spec.name,
        system = spec.system,
        displayName = spec.displayName or spec.name,
        defaults = defaults,
        indexDefaults = indexed,
        context = spec.context,
        store = spec.store or UI.SettingsStore:Create(defaults, indexed, spec.settingTypes),
        eventBus = spec.events or UI.Events:Create(),
        shouldApplyVisibility = spec.shouldApplyVisibility,
        alwaysEnabled = alwaysEnabled,
        generation = 0,
        active = false,
    }, ControllerMixin)
end
