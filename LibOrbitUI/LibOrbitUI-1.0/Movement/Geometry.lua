local _, addon = ...
local UI = addon.LibOrbitUI
local MIN_SCALE = 0.01

UI.Geometry = {}
local Geometry = UI.Geometry

function Geometry:NearestEdge(left, bottom, width, height, screenWidth, screenHeight)
    local centerX, centerY = left + width / 2, bottom + height / 2
    local right, top = screenWidth - centerX, screenHeight - centerY
    local distance = math.min(centerX, right, top, centerY)
    if distance == centerX then
        return "LEFT"
    elseif distance == right then
        return "RIGHT"
    elseif distance == top then
        return "TOP"
    end
    return "BOTTOM"
end

function Geometry:DetectOrientation(frame, lastValid)
    if not frame or not frame.GetLeft then
        return lastValid or "LEFT"
    end
    local left, bottom = frame:GetLeft(), frame:GetBottom()
    local width, height = frame:GetWidth(), frame:GetHeight()
    if not left or not bottom or not width or not height then
        return lastValid or "LEFT"
    end
    return self:NearestEdge(left, bottom, width, height, GetScreenWidth(), GetScreenHeight())
end

function Geometry:GetRectInUIParent(frame, insets)
    local left, bottom, width, height = frame:GetRect()
    if not left or not bottom or not width or not height then
        return nil
    end
    if insets then
        local insetLeft, insetBottom = insets.left or 0, insets.bottom or 0
        left, bottom = left + insetLeft, bottom + insetBottom
        width, height = width - insetLeft - (insets.right or 0), height - insetBottom - (insets.top or 0)
    end
    local ratio = frame:GetEffectiveScale() / UIParent:GetEffectiveScale()
    return left * ratio, bottom * ratio, width * ratio, height * ratio
end

function Geometry:CapturePosition(frame, target, pixel, selectionInsets)
    local left, bottom = self:GetRectInUIParent(frame)
    if not left then
        return nil
    end
    local scale = target:GetEffectiveScale()
    local ratio = scale / UIParent:GetEffectiveScale()
    local insetLeft = selectionInsets and selectionInsets.left or 0
    local insetBottom = selectionInsets and selectionInsets.bottom or 0
    -- Snap the visible origin; odd dimensions need fractional CENTER offsets to preserve the same pixel grid.
    return {
        point = "CENTER",
        relativePoint = "CENTER",
        x = pixel:Snap(left / ratio - insetLeft, scale) + target:GetWidth() / 2 - UIParent:GetWidth() / (2 * ratio),
        y = pixel:Snap(bottom / ratio - insetBottom, scale)
            + target:GetHeight() / 2
            - UIParent:GetHeight() / (2 * ratio),
    }
end

function Geometry:BeginMove(moveFrame, drag)
    local left, bottom = moveFrame:GetLeft(), moveFrame:GetBottom()
    moveFrame:StartMoving()
    drag.manual = nil
    if moveFrame:GetNumPoints() > 0 then
        return
    end
    -- A failed native follow point must release its moving flag before manual cursor tracking takes over.
    moveFrame:StopMovingOrSizing()
    local scale = moveFrame:GetEffectiveScale()
    if not scale or scale < MIN_SCALE then
        scale = 1
    end
    left, bottom = left or 0, bottom or 0
    local cursorX, cursorY = GetCursorPosition()
    drag.manual = true
    drag.manualOffX, drag.manualOffY = left - cursorX / scale, bottom - cursorY / scale
    moveFrame:ClearAllPoints()
    moveFrame:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", left, bottom)
end

function Geometry:UpdateMove(moveFrame, drag)
    if not (drag and drag.manual) or InCombatLockdown() then
        return
    end
    local scale = moveFrame:GetEffectiveScale()
    if not scale or scale < MIN_SCALE then
        scale = 1
    end
    local cursorX, cursorY = GetCursorPosition()
    moveFrame:ClearAllPoints()
    moveFrame:SetPoint(
        "BOTTOMLEFT",
        UIParent,
        "BOTTOMLEFT",
        cursorX / scale + drag.manualOffX,
        cursorY / scale + drag.manualOffY
    )
end

function Geometry:EndMove(moveFrame, drag)
    moveFrame:StopMovingOrSizing()
    drag.manual = nil
end

table.freeze(Geometry)
