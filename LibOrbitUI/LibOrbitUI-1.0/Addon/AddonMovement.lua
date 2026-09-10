local _, addon = ...
local UI = addon.LibOrbitUI
local AddonMixin = UI.AddonMixin

function AddonMixin:RestorePosition(frame, index)
    local record = self.frameRecords[index]
    local position = self.controller:GetSetting(index, "Position")
        or frame.defaultPosition
        or (record and record.defaultPosition)
    if not position or frame.orbitIsDragging or InCombatLockdown() then
        return
    end
    frame:ClearAllPoints()
    frame:SetPoint(position.point, UIParent, position.relativePoint or position.point, position.x, position.y)
end

function AddonMixin:AttachMovement()
    for _, record in ipairs(self.options.frames()) do
        local frame, index = record.frame, record.index
        assert(frame and type(index) == "number", "LibOrbitUI addon movement needs a frame and numeric index")
        self.frameRecords[index] = record
        self:RestorePosition(frame, index)
        self.movements[index] = UI.Movement:Create(self.context, frame, {
            label = record.label,
            getSelectionInsets = record.getSelectionInsets,
            getPosition = function()
                return self.controller:GetSetting(index, "Position") or frame.defaultPosition or record.defaultPosition
            end,
            applyPosition = function(_, position, reason)
                if reason then
                    self.controller:SetSetting(index, "Position", position)
                end
                frame:ClearAllPoints()
                frame:SetPoint(
                    position.point,
                    UIParent,
                    position.relativePoint or position.point,
                    position.x,
                    position.y
                )
                self:Apply()
            end,
            canEdit = function()
                return self.controller:IsActive() and frame:IsShown() and (not record.canEdit or record.canEdit())
            end,
            onSelect = function()
                self:ShowSettings(index)
            end,
            onEditChanged = function(_, active)
                if record.onEditChanged then
                    record.onEditChanged(active)
                end
                if record.applyOnEditChanged ~= false then
                    self:Apply()
                end
            end,
            onDragChanged = function(_, active)
                frame.orbitIsDragging = active
                if record.onDragChanged then
                    record.onDragChanged(active)
                end
            end,
        })
    end
end

function AddonMixin:ResetPosition(index)
    index = index or 1
    if not self.ready or InCombatLockdown() then
        return
    end
    if self.options.bridge then
        self.options.bridge.ResetPosition(index)
    else
        local record = self.frameRecords[index]
        if record then
            local position = record.defaultPosition or record.frame.defaultPosition
            if position then
                self.movements[index]:Reset(CopyTable(position))
            end
        end
    end
end
