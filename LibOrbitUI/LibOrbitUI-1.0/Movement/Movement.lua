local _, addon = ...
local UI = addon.LibOrbitUI
local SYNC_INTERVAL = 0.1
local NUDGE_PIXELS = 1
local FAST_NUDGE_PIXELS = 10
local OVERLAY_STRATA = "HIGH"
local DIRECTIONS = { UP = { 0, 1 }, DOWN = { 0, -1 }, LEFT = { -1, 0 }, RIGHT = { 1, 0 } }
local INSET_KEYS = { "left", "right", "top", "bottom" }

UI.Movement = {}
local MovementMixin = {}

local function CanApply(movement)
    return not movement.destroyed
        and movement.session.enabled
        and not InCombatLockdown()
        and (movement.options.blockEncounter == false or not C_InstanceEncounter.IsEncounterInProgress())
        and (not movement.options.canEdit or movement.options.canEdit(movement.context.owner))
end

local function ShowSelection(movement)
    if movement.selected then
        movement.overlay:ShowSelected()
    else
        movement.overlay:ShowHighlighted()
    end
end

function MovementMixin:Sync()
    local insets = self.options.getSelectionInsets and self.options.getSelectionInsets(self.context.owner)
    if insets then
        self.selectionInsets = self.selectionInsets or {}
        for _, key in ipairs(INSET_KEYS) do
            self.selectionInsets[key] = insets[key] or 0
        end
    else
        self.selectionInsets = nil
    end
    local left, bottom, width, height = UI.Geometry:GetRectInUIParent(self.frame, self.selectionInsets)
    if not left or width <= 0 or height <= 0 then
        self.overlay:Hide()
        return false
    end
    local pixel, overlay = self.context.pixel, self.overlay
    local scale = overlay:GetEffectiveScale()
    overlay:SetSize(pixel:Snap(width, scale), pixel:Snap(height, scale))
    overlay:ClearAllPoints()
    overlay:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", pixel:Snap(left, scale), pixel:Snap(bottom, scale))
    return true
end

function MovementMixin:SetSelected(selected)
    self.selected = not not selected
    if selected then
        local previous = self.context.movementSelection
        if previous and previous ~= self then
            previous:SetSelected(false)
        end
        self.context.movementSelection = self
    elseif self.context.movementSelection == self then
        self.context.movementSelection = nil
    end
    if not InCombatLockdown() then
        self.overlay:EnableKeyboard(self.selected)
        self.overlay:SetPropagateKeyboardInput(true)
    end
    if self.session:IsActive() and self.overlay:IsShown() then
        ShowSelection(self)
    end
end

function MovementMixin:AbortDrag()
    local drag = self.drag
    if not drag then
        return
    end
    self.drag = nil
    UI.Geometry:EndMove(self.overlay, drag)
    if self.options.onDragChanged then
        self.options.onDragChanged(self.context.owner, false)
    end
end

function MovementMixin:Refresh()
    if self.destroyed or self.transitioning then
        return
    end
    self.session:Refresh("refresh")
    if self.session:IsActive() and not self.drag and self:Sync() then
        ShowSelection(self)
    end
end

function MovementMixin:IsEditing()
    return self.session:IsActive()
end

function MovementMixin:SetEnabled(enabled)
    self.session:SetEnabled(enabled)
end

function MovementMixin:Reset(position)
    if not CanApply(self) then
        return false
    end
    if not position and self.options.getPosition then
        position = self.options.getPosition(self.context.owner)
    end
    assert(position, "LibOrbitUI movement reset needs a position")
    self:AbortDrag()
    if not CanApply(self) then
        return false
    end
    self.options.applyPosition(self.context.owner, position, "reset")
    self:Refresh()
    return true
end

function MovementMixin:Destroy()
    if self.destroyed then
        return
    end
    self.destroyed = true
    self.session:Destroy()
    self:AbortDrag()
    self:SetSelected(false)
    self.overlay:Hide()
    self.updates:Hide()
    self.updates:SetScript("OnUpdate", nil)
    self.overlay:UnregisterAllEvents()
    for _, script in ipairs({
        "OnUpdate",
        "OnEvent",
        "OnMouseDown",
        "OnMouseUp",
        "OnDragStart",
        "OnDragStop",
        "OnKeyDown",
        "OnKeyUp",
    }) do
        self.overlay:SetScript(script, nil)
    end
end

local function BeginDrag(movement)
    movement.session:Refresh("drag")
    if not movement.session:IsActive() or movement.drag or not movement:Sync() then
        return
    end
    movement:SetSelected(true)
    movement.suppressClick = true
    movement.drag = { generation = movement.session.generation }
    if movement.options.onDragChanged then
        movement.options.onDragChanged(movement.context.owner, true)
    end
    movement.session:Refresh("drag")
    if movement.drag and movement.session:IsActive() then
        UI.Geometry:BeginMove(movement.overlay, movement.drag)
    end
end

local function EndDrag(movement)
    local drag = movement.drag
    if not drag then
        return
    end
    movement.session:Refresh("drop")
    if movement.drag ~= drag or not movement.session:IsActive() then
        return
    end
    UI.Geometry:EndMove(movement.overlay, drag)
    local position =
        UI.Geometry:CapturePosition(movement.overlay, movement.frame, movement.context.pixel, movement.selectionInsets)
    movement.drag = nil
    if movement.options.onDragChanged then
        movement.options.onDragChanged(movement.context.owner, false)
    end
    movement.session:Refresh("drop")
    if
        position
        and movement.session:IsActive()
        and movement.session.generation == drag.generation
        and CanApply(movement)
    then
        movement.options.applyPosition(movement.context.owner, position, "drag")
    end
    movement:Refresh()
end

local function Nudge(movement, key)
    if InCombatLockdown() then
        return
    end
    movement.overlay:SetPropagateKeyboardInput(true)
    movement.session:Refresh("nudge")
    local direction = DIRECTIONS[key]
    if
        not direction
        or not movement.selected
        or not movement.session:IsActive()
        or movement.drag
        or GetCurrentKeyBoardFocus()
    then
        return
    end
    if not movement:Sync() then
        return
    end
    movement.overlay:SetPropagateKeyboardInput(false)
    local pixel, overlay = movement.context.pixel, movement.overlay
    local scale = overlay:GetEffectiveScale()
    local step = pixel:Multiple(IsShiftKeyDown() and FAST_NUDGE_PIXELS or NUDGE_PIXELS, scale)
    local left, bottom = overlay:GetLeft() + direction[1] * step, overlay:GetBottom() + direction[2] * step
    left = math.max(0, math.min(left, UIParent:GetWidth() - overlay:GetWidth()))
    bottom = math.max(0, math.min(bottom, UIParent:GetHeight() - overlay:GetHeight()))
    overlay:ClearAllPoints()
    overlay:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", pixel:Snap(left, scale), pixel:Snap(bottom, scale))
    local position = UI.Geometry:CapturePosition(overlay, movement.frame, pixel, movement.selectionInsets)
    if position and CanApply(movement) then
        movement.options.applyPosition(movement.context.owner, position, "nudge")
    end
    movement:Refresh()
end

local function OnUpdate(movement, elapsed)
    if movement.drag then
        movement.session:Refresh("drag")
        if movement.drag then
            UI.Geometry:UpdateMove(movement.overlay, movement.drag)
        end
    else
        movement.elapsed = movement.elapsed + elapsed
        if movement.elapsed >= SYNC_INTERVAL then
            movement.elapsed = 0
            movement:Refresh()
        end
    end
end

local function Dispatch(movement, callback, ...)
    local ok, err = pcall(callback, movement, ...)
    if not ok then
        movement.transitioning = false
        local cleanupOK, cleanupError = pcall(movement.SetEnabled, movement, false)
        movement.overlay:Hide()
        movement.updates:Hide()
        geterrorhandler()(err)
        if not cleanupOK then
            geterrorhandler()(cleanupError)
        end
    end
end

table.freeze(MovementMixin)

function UI.Movement:Create(context, frame, options)
    assert(type(options.label) == "string", "LibOrbitUI movement needs a localized label")
    assert(options.applyPosition and options.onSelect, "LibOrbitUI movement needs position and selection callbacks")
    local movement = Mixin({ context = context, frame = frame, options = options, elapsed = 0 }, MovementMixin)
    movement.updates = CreateFrame("Frame", nil, UIParent)
    movement.updates:Hide()
    -- The native template's Selection parentKey must land on an owned frame, never on UIParent or the secure target.
    local overlay = CreateFrame("Frame", nil, movement.updates, "EditModeSystemSelectionTemplate")
    movement.overlay = overlay
    overlay:Hide()
    overlay:SetToplevel(false)
    overlay:SetFrameStrata(OVERLAY_STRATA)
    overlay:SetMovable(true)
    overlay:SetClampedToScreen(true)
    if not InCombatLockdown() then
        overlay:EnableKeyboard(false)
        overlay:SetPropagateKeyboardInput(true)
    end
    -- Replace only this owned template instance's manager/tooltip dispatch; native system registration stays untouched.
    overlay.CheckShowInstructionalTooltip = function() end
    overlay.HideInstructionalTooltip = function() end
    overlay.GetLabelText = function()
        return options.label
    end
    overlay:SetScript("OnMouseDown", function(_, button)
        Dispatch(movement, function(self)
            self.session:Refresh("select")
            if button == "LeftButton" and self.session:IsActive() then
                self.suppressClick = false
                self.clickGeneration = self.session.generation
                self:SetSelected(true)
            end
        end)
    end)
    overlay:SetScript("OnMouseUp", function(_, button)
        Dispatch(movement, function(self)
            self.session:Refresh("select")
            local generation = self.clickGeneration
            self.clickGeneration = nil
            if
                button == "LeftButton"
                and self.session:IsActive()
                and generation == self.session.generation
                and not self.suppressClick
            then
                options.onSelect(context.owner)
            end
        end)
    end)
    overlay:SetScript("OnDragStart", function()
        Dispatch(movement, BeginDrag)
    end)
    overlay:SetScript("OnDragStop", function()
        Dispatch(movement, EndDrag)
    end)
    overlay:SetScript("OnKeyDown", function(_, key)
        Dispatch(movement, Nudge, key)
    end)
    overlay:SetScript("OnKeyUp", function()
        if not InCombatLockdown() then
            overlay:SetPropagateKeyboardInput(true)
        end
    end)
    movement.updates:SetScript("OnUpdate", function(_, elapsed)
        Dispatch(movement, OnUpdate, elapsed)
    end)
    overlay:RegisterEvent("GLOBAL_MOUSE_DOWN")
    overlay:SetScript("OnEvent", function()
        Dispatch(movement, function(self)
            if not self.selected then
                return
            end
            for _, focus in ipairs(GetMouseFoci()) do
                if focus == overlay then
                    return
                end
            end
            self:SetSelected(false)
        end)
    end)
    movement.session = UI.EditSession:Create(movement, {
        enabled = false,
        blockEncounter = options.blockEncounter,
        canEdit = function()
            return not options.canEdit or options.canEdit(context.owner)
        end,
        onEnter = function(self, reason)
            self.transitioning = true
            if options.onEditChanged then
                options.onEditChanged(context.owner, true, reason)
            end
            self.transitioning = false
            self:SetSelected(false)
            self.updates:Show()
            if self:Sync() then
                ShowSelection(self)
            end
        end,
        onExit = function(self, reason)
            self.transitioning = false
            self.clickGeneration = nil
            self:AbortDrag()
            self:SetSelected(false)
            overlay:Hide()
            self.updates:Hide()
            if options.onEditChanged then
                options.onEditChanged(context.owner, false, reason)
            end
        end,
    })
    Dispatch(movement, function(self)
        self.session:SetEnabled(options.enabled ~= false)
    end)
    return movement
end
