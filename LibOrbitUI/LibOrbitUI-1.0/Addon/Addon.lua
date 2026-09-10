local _, addon = ...
local UI = addon.LibOrbitUI
local SETTINGS_BUTTON_WIDTH, SETTINGS_BUTTON_HEIGHT = 240, 30
local SETTINGS_PADDING = 20
local APPLY_DELAY = 0.01

UI.Addon = {}
local AddonMixin = {}
UI.AddonMixin = AddonMixin

function AddonMixin:IsEditMode()
    local manager = EditModeManagerFrame
    return manager and manager:IsEditModeActive() and manager:IsShown() and not InCombatLockdown() or false
end

function AddonMixin:IsEnabled()
    if self.options.bridge then
        return self.options.bridge.IsEnabled()
    end
    return self.controller:GetSetting(1, "Enabled")
end

function AddonMixin:SetEnabled(enabled)
    if self.options.bridge then
        self.options.bridge.SetEnabled(enabled)
    else
        self.controller:SetSetting(1, "Enabled", enabled)
        self:Apply()
    end
end

function AddonMixin:Reconcile()
    if not self.ready then
        return
    end
    if self.options.bridge then
        self.options.bridge.Apply()
        return
    end
    local enabled = self:IsEnabled()
    if enabled then
        if self.controller:IsActive() then
            self.controller:ApplySettings()
        else
            self.controller:Enable()
        end
    else
        self.controller:Disable()
    end
    for _, movement in pairs(self.movements) do
        movement:SetEnabled(enabled and self.controller:IsActive())
        movement:Refresh()
    end
end

function AddonMixin:Apply()
    if self.ready then
        self.runtime:Debounce("apply", function()
            self.runtime:Invalidate(self.reconciler)
        end, APPLY_DELAY)
    end
end

function AddonMixin:EnterEditMode()
    if InCombatLockdown() then
        return
    end
    for _, dialog in pairs(self.dialogs) do
        dialog:Hide()
    end
    if self.options.bridge then
        self.options.bridge.EnterEditMode()
    elseif EditModeManagerFrame and EditModeManagerFrame:CanEnterEditMode() then
        securecall("ShowUIPanel", EditModeManagerFrame)
    end
end

local function RegisterSettings(app)
    local panel = CreateFrame("Frame")
    panel:Hide()
    local button = CreateFrame("Button", nil, panel, "UIPanelButtonTemplate")
    button:SetSize(SETTINGS_BUTTON_WIDTH, SETTINGS_BUTTON_HEIGHT)
    app.context.pixel:Point(button, "TOPLEFT", panel, "TOPLEFT", SETTINGS_PADDING, -SETTINGS_PADDING)
    button:SetText(app.options.labels.settings)
    button:SetScript("OnClick", function()
        app:ShowSettings()
    end)
    app.category = Settings.RegisterCanvasLayoutCategory(panel, app.options.title)
    Settings.RegisterAddOnCategory(app.category)
end

local function RegisterCommands(app)
    local options = app.options
    for index, command in ipairs(options.slash) do
        _G["SLASH_" .. options.slashKey .. index] = command
    end
    SlashCmdList[options.slashKey] = function(command)
        command = command:match("^%s*(.-)%s*$"):lower()
        if command == "move" then
            app:EnterEditMode()
        elseif command == "reset" then
            app:ResetPosition()
        else
            app:ShowSettings()
        end
    end
end

function UI.Addon:Create(options)
    assert(options.addonName and options.name and options.controller and options.context)
    local app = Mixin({
        options = options,
        context = options.context,
        controller = options.controller,
        ready = false,
        storeReady = options.bridge ~= nil,
        movements = {},
        frameRecords = {},
        dialogs = {},
    }, AddonMixin)
    app.runtime = UI.Runtime:Create(app)
    app.reconciler = app.runtime:RegisterReconciler("lifecycle", function()
        app:Reconcile()
    end)
    if not options.bridge then
        app.controller.onLoaded = function()
            app:AttachMovement()
        end
        app.controller.onSettingChanged = function()
            app:Apply()
        end
    end
    local events = CreateFrame("Frame")
    events:RegisterEvent("ADDON_LOADED")
    events:RegisterEvent("PLAYER_LOGIN")
    events:SetScript("OnEvent", function(_, event, name)
        if event == "ADDON_LOADED" and name == options.addonName then
            if not options.bridge then
                local data, err = options.store:Initialize(options.readStore())
                app.storeReady = data ~= nil
                app.storeError = err
                if data then
                    options.writeStore(data)
                end
            end
            RegisterSettings(app)
            RegisterCommands(app)
            events:UnregisterEvent("ADDON_LOADED")
        elseif event == "PLAYER_LOGIN" then
            events:UnregisterEvent("PLAYER_LOGIN")
            app.ready = app.storeReady
            if app.ready then
                if options.bridge and options.bridge.Ready then
                    options.bridge.Ready()
                elseif not options.bridge then
                    app.runtime:Invalidate(app.reconciler)
                end
            end
        end
    end)
    app.events = events
    return app
end
