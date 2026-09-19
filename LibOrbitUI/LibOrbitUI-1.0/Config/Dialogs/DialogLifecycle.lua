local _, addon = ...
local UI = addon.LibOrbitUI
local POLICIES = { auto = true, required = true, manual = true }

UI.DialogLifecycle = {}
local LifecycleMixin = {}

function LifecycleMixin:IsOpen()
    return self.open and not self.destroyed and not self.context.destroyed and self.dialog:IsShown()
end

function LifecycleMixin:Begin()
    if self.destroyed or self.context.destroyed or self.closing or InCombatLockdown() then
        self.dialog:Hide()
        return
    end
    self.open = true
    local manager = EditModeManagerFrame
    self.editModeBound = self.policy == "required" or (self.policy == "auto" and manager and manager:IsEditModeActive())
    self.editSession:SetEnabled(self.editModeBound)
    if self.editModeBound and not self.editSession:IsActive() then
        self.dialog:Hide()
    end
end

function LifecycleMixin:End()
    if not self.open then
        return
    end
    self.open = false
    self.closing = true
    self.editSession:SetEnabled(false)
    if self.options.onClose then
        self.options.onClose(self.dialog)
    end
    self.closing = false
end

function LifecycleMixin:RefreshMode()
    if not self:IsOpen() then
        return
    end
    self.editSession:Refresh("dialog")
    if self:IsOpen() and self.options.onRefresh then
        self.options.onRefresh(self.dialog)
    end
end

function LifecycleMixin:Destroy()
    if self.destroyed then
        return
    end
    self.destroyed = true
    self.dialog:Hide()
    self:End()
    self.editSession:Destroy()
    self.events:UnregisterAllEvents()
    self.events:SetScript("OnEvent", nil)
    EventRegistry:UnregisterCallback("EditMode.Enter", self)
    EventRegistry:UnregisterCallback("EditMode.Exit", self)
    self.context.dialogLifecycles[self] = nil
end

table.freeze(LifecycleMixin)

function UI.DialogLifecycle:Create(context, dialog, options)
    assert(not context.destroyed, "LibOrbitUI context is destroyed")
    options = options or {}
    local policy = options.editModePolicy or "auto"
    assert(POLICIES[policy], "Unknown LibOrbitUI dialog Edit Mode policy")
    local lifecycle = Mixin({
        context = context,
        dialog = dialog,
        options = options,
        policy = policy,
        open = false,
    }, LifecycleMixin)
    context.dialogLifecycles = context.dialogLifecycles or {}
    context.dialogLifecycles[lifecycle] = true
    lifecycle.editSession = UI.EditSession:Create(lifecycle, {
        enabled = false,
        blockEncounter = false,
        onExit = function(self)
            if self.open then
                self.dialog:Hide()
            end
        end,
    })
    lifecycle.events = CreateFrame("Frame")
    lifecycle.events:RegisterEvent("PLAYER_REGEN_DISABLED")
    lifecycle.events:SetScript("OnEvent", function()
        dialog:Hide()
    end)
    dialog:HookScript("OnShow", function()
        lifecycle:Begin()
    end)
    dialog:HookScript("OnHide", function()
        lifecycle:End()
    end)
    EventRegistry:RegisterCallback("EditMode.Enter", lifecycle.RefreshMode, lifecycle)
    EventRegistry:RegisterCallback("EditMode.Exit", lifecycle.RefreshMode, lifecycle)
    if dialog:IsShown() then
        lifecycle:Begin()
    end
    return lifecycle
end
