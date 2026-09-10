local _, addon = ...
local UI = addon.LibOrbitUI
local POLL_INTERVAL = 0.1

UI.EditSession = {}
local SessionMixin = {}

function SessionMixin:IsActive()
    return self.active
end

function SessionMixin:Deactivate(reason)
    if not self.active then
        return
    end
    self.active = false
    self.generation = self.generation + 1
    if self.options.onExit then
        self.options.onExit(self.owner, reason, self.generation)
    end
end

function SessionMixin:Refresh(reason)
    if self.refreshing then
        return
    end
    local manager = EditModeManagerFrame
    local nativeActive = manager and manager:IsEditModeActive()
    self.poll:SetShown(not self.destroyed and self.enabled and nativeActive or false)
    local blocked
    if self.destroyed or not self.enabled then
        blocked = "disabled"
    elseif not nativeActive then
        blocked = "exit"
    elseif not manager:IsShown() or manager:IsEditModeLocked() then
        blocked = "hidden"
    elseif InCombatLockdown() then
        blocked = "combat"
    elseif self.options.blockEncounter ~= false and C_InstanceEncounter.IsEncounterInProgress() then
        blocked = "encounter"
    elseif self.options.canEdit and not self.options.canEdit(self.owner) then
        blocked = "policy"
    end
    self.refreshing = true
    if blocked then
        self:Deactivate(blocked)
    elseif not self.active then
        self.active = true
        self.generation = self.generation + 1
        if self.options.onEnter then
            self.options.onEnter(self.owner, reason or "enter", self.generation)
        end
    end
    self.refreshing = false
end

function SessionMixin:SetEnabled(enabled)
    if self.destroyed then
        return
    end
    self.enabled = not not enabled
    self:Refresh("enabled")
end

function SessionMixin:Destroy()
    if self.destroyed then
        return
    end
    self.destroyed = true
    self.enabled = false
    self.poll:Hide()
    self.poll:UnregisterAllEvents()
    self.poll:SetScript("OnEvent", nil)
    self.poll:SetScript("OnUpdate", nil)
    EventRegistry:UnregisterCallback("EditMode.Enter", self)
    EventRegistry:UnregisterCallback("EditMode.Exit", self)
    self:Deactivate("destroy")
end

table.freeze(SessionMixin)

local function Dispatch(session, reason)
    local ok, err = pcall(session.Refresh, session, reason)
    if not ok then
        session.refreshing = false
        session.enabled = false
        session.poll:Hide()
        local cleanupOK, cleanupError = pcall(session.Deactivate, session, "error")
        geterrorhandler()(err)
        if not cleanupOK then
            geterrorhandler()(cleanupError)
        end
    end
end

function UI.EditSession:Create(owner, options)
    local session = Mixin({
        owner = owner,
        options = options,
        active = false,
        enabled = options.enabled ~= false,
        generation = 0,
        elapsed = 0,
    }, SessionMixin)
    session.poll = CreateFrame("Frame", nil, UIParent)
    for _, event in ipairs({
        "PLAYER_REGEN_DISABLED",
        "PLAYER_REGEN_ENABLED",
        "ENCOUNTER_START",
        "ENCOUNTER_END",
        "PLAYER_ENTERING_WORLD",
    }) do
        session.poll:RegisterEvent(event)
    end
    session.poll:SetScript("OnEvent", function(_, event)
        Dispatch(session, event)
    end)
    session.poll:SetScript("OnUpdate", function(_, elapsed)
        session.elapsed = session.elapsed + elapsed
        if session.elapsed >= POLL_INTERVAL then
            session.elapsed = 0
            Dispatch(session, "poll")
        end
    end)
    -- Locked native panels omit Exit/Enter events; an owned poll observes their visibility without manager hooks.
    EventRegistry:RegisterCallback("EditMode.Enter", function()
        Dispatch(session, "enter")
    end, session)
    EventRegistry:RegisterCallback("EditMode.Exit", function()
        Dispatch(session, "exit")
    end, session)
    session:Refresh("create")
    return session
end
