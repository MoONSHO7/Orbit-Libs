local _, addon = ...
local UI = addon.LibOrbitUI
UI.ScrollBar = {}
-- [ MINIMAL SCROLLBAR ]------------------------------------------------------------------------------------------------
local ANIM_SPEED = 14
local SETTLE_EPSILON = 0.5
local BAR_PIXELS = 2
local GRAB_WIDTH = 5
local MIN_THUMB = 16
local BAR_COLOR = { r = 0.72, g = 0.72, b = 0.72 }
local TRACK_ALPHA = 0.12
local WHEEL_STEP = 60

local ScrollBarMixin = {}

local function EaseTowards(pixel, current, target, elapsed, scale)
    if math.abs(target - current) < SETTLE_EPSILON then
        return pixel:Snap(target, scale), true
    end
    return current + ((target - current) * math.min(1, elapsed * ANIM_SPEED)), false
end

function ScrollBarMixin:Attach(scrollFrame, opts)
    local Pixel = self.pixel
    local rightOffset = (opts and opts.rightOffset) or 0
    local rightOffsetPixels = (opts and opts.rightOffsetPixels) or 0
    local bar = CreateFrame("Frame", nil, scrollFrame:GetParent())
    bar:EnableMouse(true)
    bar:EnableMouseWheel(true)
    bar:RegisterForDrag("LeftButton")
    bar.Track = bar:CreateTexture(nil, "ARTWORK")
    bar.Track:SetColorTexture(BAR_COLOR.r, BAR_COLOR.g, BAR_COLOR.b, 1)
    bar.Track:SetAlpha(TRACK_ALPHA)
    bar.Thumb = bar:CreateTexture(nil, "OVERLAY")
    bar.Thumb:SetColorTexture(BAR_COLOR.r, BAR_COLOR.g, BAR_COLOR.b, 1)

    local animator = CreateFrame("Frame", nil, scrollFrame)
    animator:Hide()

    local function Update()
        local range = scrollFrame:GetVerticalScrollRange()
        if bar.scrollTarget then
            bar.scrollTarget = math.min(bar.scrollTarget, range)
        end
        if range <= SETTLE_EPSILON then
            animator:Hide()
            bar.scrollTarget = nil
            if scrollFrame:GetVerticalScroll() > range then
                scrollFrame:SetVerticalScroll(0)
            end
            bar:Hide()
            return
        end
        bar:Show()
        local scroll = scrollFrame:GetVerticalScroll()
        if scroll > range then
            scroll = range
            scrollFrame:SetVerticalScroll(range)
        end
        local scale = bar:GetEffectiveScale()
        local trackHeight = bar:GetHeight()
        local viewport = scrollFrame:GetHeight()
        local thumbHeight = math.max(MIN_THUMB, trackHeight * viewport / (viewport + range))
        thumbHeight = math.min(trackHeight, Pixel:Snap(thumbHeight, scale))
        local travel = trackHeight - thumbHeight
        local offset = travel * math.min(1, math.max(0, scroll / range))
        bar.Thumb:SetHeight(thumbHeight)
        bar.Thumb:ClearAllPoints()
        bar.Thumb:SetPoint("TOPRIGHT", bar, "TOPRIGHT", 0, -Pixel:Snap(offset, scale))
    end

    local function LayoutBar()
        local scale = bar:GetEffectiveScale()
        bar:SetWidth(Pixel:Snap(GRAB_WIDTH, scale))
        local shift = Pixel:Snap(rightOffset, scale) + Pixel:Multiple(rightOffsetPixels, scale)
        bar:ClearAllPoints()
        bar:SetPoint("TOPRIGHT", scrollFrame, "TOPRIGHT", shift, 0)
        bar:SetPoint("BOTTOMRIGHT", scrollFrame, "BOTTOMRIGHT", shift, 0)
        local barWidth = Pixel:Multiple(BAR_PIXELS, scale)
        bar.Track:ClearAllPoints()
        bar.Track:SetWidth(barWidth)
        bar.Track:SetPoint("TOPRIGHT", bar, "TOPRIGHT", 0, 0)
        bar.Track:SetPoint("BOTTOMRIGHT", bar, "BOTTOMRIGHT", 0, 0)
        bar.Thumb:SetWidth(barWidth)
        Update()
    end

    local function StartScrollTo(position)
        local range = scrollFrame:GetVerticalScrollRange()
        bar.scrollTarget = math.min(math.max(position, 0), range)
        animator:Show()
    end

    function bar:StopScrolling()
        animator:Hide()
        self.scrollTarget, self.dragY = nil, nil
        self:SetScript("OnUpdate", nil)
    end

    function bar:SetScrollPosition(position)
        self:StopScrolling()
        scrollFrame:SetVerticalScroll(math.max(0, math.min(position, scrollFrame:GetVerticalScrollRange())))
        Update()
    end

    local function OnWheel(_, delta)
        local current = scrollFrame:GetVerticalScroll()
        local from = bar.scrollTarget or current
        if (from - current) * delta > 0 then
            from = current
        end
        StartScrollTo(from - delta * WHEEL_STEP)
    end

    local function DragStep()
        local range = scrollFrame:GetVerticalScrollRange()
        local travel = bar:GetHeight() - bar.Thumb:GetHeight()
        if range <= 0 or travel <= 0 then
            return
        end
        local _, cursorY = GetCursorPosition()
        local delta = (bar.dragY - cursorY) / bar:GetEffectiveScale()
        bar.dragY = cursorY
        local position = math.min(range, math.max(0, scrollFrame:GetVerticalScroll() + delta * range / travel))
        animator:Hide()
        bar.scrollTarget = position
        scrollFrame:SetVerticalScroll(position)
        Update()
    end

    animator:SetScript("OnUpdate", function(_, elapsed)
        local current = scrollFrame:GetVerticalScroll()
        local target = bar.scrollTarget or current
        local position, settled = EaseTowards(Pixel, current, target, elapsed, scrollFrame:GetEffectiveScale())
        scrollFrame:SetVerticalScroll(position)
        Update()
        if settled then
            animator:Hide()
            bar.scrollTarget = nil
        end
    end)

    scrollFrame:EnableMouseWheel(true)
    scrollFrame:SetScript("OnMouseWheel", OnWheel)
    scrollFrame:SetScript("OnScrollRangeChanged", Update)
    scrollFrame:SetScript("OnSizeChanged", LayoutBar)
    scrollFrame:HookScript("OnHide", function()
        bar:StopScrolling()
    end)
    bar:SetScript("OnMouseWheel", OnWheel)
    bar:SetScript("OnDragStart", function(self)
        local _, cursorY = GetCursorPosition()
        self.dragY = cursorY
        self:SetScript("OnUpdate", DragStep)
    end)
    bar:SetScript("OnDragStop", function(self)
        self:SetScript("OnUpdate", nil)
        self.dragY = nil
    end)

    LayoutBar()
    scrollFrame.OrbitScrollBar = bar
    return bar
end

table.freeze(ScrollBarMixin)

function UI.ScrollBar:Create(pixel)
    return Mixin({ pixel = pixel }, ScrollBarMixin)
end
