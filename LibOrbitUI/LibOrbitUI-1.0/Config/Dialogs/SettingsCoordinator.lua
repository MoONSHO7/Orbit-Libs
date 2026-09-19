local _, addon = ...
local UI = addon.LibOrbitUI
local SHARED_NAME = "LibOrbitUISettingsCoordinator"
local PROTOCOL_VERSION = 1

if _G[SHARED_NAME] then
    assert(
        _G[SHARED_NAME].protocolVersion == PROTOCOL_VERSION,
        "Incompatible LibOrbitUI settings coordination protocol"
    )
    UI.SettingsCoordinator = _G[SHARED_NAME]
    return
end

local CoordinatorMixin = {}

function CoordinatorMixin:IsEditing()
    local manager = EditModeManagerFrame
    return manager and manager:IsEditModeActive()
end

function CoordinatorMixin:Activate(dialog)
    if not self:IsEditing() or not dialog:IsShown() then
        return
    end
    self.current = dialog
    for window in pairs(self.windows) do
        if self.current ~= dialog or not dialog:IsShown() then
            return
        end
        if window ~= dialog and window:IsShown() then
            window:Hide()
        end
    end
    if self.current ~= dialog or not dialog:IsShown() then
        return
    end
    if self.native and dialog ~= self.native and self.native:IsShown() and not InCombatLockdown() then
        -- Hiding alone leaves the system selected, so clicking that same native frame cannot reopen its editor.
        securecallfunction(EditModeManagerFrame.ClearSelectedSystem, EditModeManagerFrame)
    end
end

function CoordinatorMixin:ObserveNative()
    local native = EditModeSystemSettingsDialog
    if self.native or not native then
        return
    end
    self.native = native
    hooksecurefunc(
        native,
        "Show",
        UI.Callbacks:Wrap(function()
            self:Activate(native)
        end, "SettingsCoordinator")
    )
end

function CoordinatorMixin:OnEnter()
    self:ObserveNative()
    local latest, sequence = nil, 0
    for window, order in pairs(self.windows) do
        if window:IsShown() and order > sequence then
            latest, sequence = window, order
        end
    end
    if self.native and self.native:IsShown() then
        latest = self.native
    end
    if latest then
        self:Activate(latest)
    end
end

function CoordinatorMixin:Register(dialog)
    if self.windows[dialog] then
        return
    end
    self:ObserveNative()
    self.windows[dialog] = 0
    dialog:HookScript("OnShow", function()
        self.sequence = self.sequence + 1
        self.windows[dialog] = self.sequence
        self:Activate(dialog)
    end)
    dialog:HookScript("OnHide", function()
        if self.current == dialog then
            self.current = nil
        end
    end)
    if dialog:IsShown() then
        self.sequence = self.sequence + 1
        self.windows[dialog] = self.sequence
        self:Activate(dialog)
    end
end

table.freeze(CoordinatorMixin)

local coordinator = Mixin({
    protocolVersion = PROTOCOL_VERSION,
    windows = setmetatable({}, { __mode = "k" }),
    sequence = 0,
}, CoordinatorMixin)
_G[SHARED_NAME] = coordinator
UI.SettingsCoordinator = coordinator
EventRegistry:RegisterCallback("EditMode.Enter", coordinator.OnEnter, coordinator)
