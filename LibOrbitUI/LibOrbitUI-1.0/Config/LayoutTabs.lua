local _, addon = ...
local Layout = addon.LibOrbitUI.Layout.Methods
local TAB_HEIGHT = 24
local TAB_SPACING = 4
local TAB_TEXT_PADDING = 30
local TAB_ACTIVE_COLOR = { r = 1, g = 0.82, b = 0 }
local TAB_INACTIVE_COLOR = { r = 0.6, g = 0.6, b = 0.6 }
local TAB_HOVER_COLOR = { r = 1, g = 1, b = 1 }
local TAB_DIVIDER_COLOR = { r = 0.3, g = 0.3, b = 0.3 }
local TAB_DIVIDER_HEIGHT = 1
local TAB_BOTTOM_PADDING = 4
local TAB_HIGHLIGHT_ATLAS = "housing-basic-panel-gradient-header-bg"
local TAB_HIGHLIGHT_HEIGHT = 21
local TAB_HIGHLIGHT_WIDTH_SCALE = 1.84
local TAB_SCROLL_STEP = 60
local TAB_SCROLL_ANIM_SPEED = 14
local TAB_SCROLL_SETTLE_EPSILON = 0.5
local TAB_OVERFLOW_LEFT_GLYPH = "\194\171"
local TAB_OVERFLOW_RIGHT_GLYPH = "\194\187"
local TAB_OVERFLOW_EPSILON = 0.5
local TAB_OVERFLOW_GAP = 4
local TAB_OVERFLOW_Y_OFFSET = 2
local TAB_OVERFLOW_FONT_REDUCTION = 1

local function ApplyTabState(btn, isActive)
    btn.active = isActive
    if isActive then
        btn.Text:SetTextColor(TAB_ACTIVE_COLOR.r, TAB_ACTIVE_COLOR.g, TAB_ACTIVE_COLOR.b)
        btn:Disable()
        btn.highlight:Show()
    else
        btn.Text:SetTextColor(TAB_INACTIVE_COLOR.r, TAB_INACTIVE_COLOR.g, TAB_INACTIVE_COLOR.b)
        btn:Enable()
        btn.highlight:Hide()
    end
end

local function SelectTab(button)
    if button.tabCallback then
        button.tabCallback(button.Text:GetText())
    end
end

local function EaseTowards(pixel, current, target, elapsed, scale)
    if math.abs(target - current) < TAB_SCROLL_SETTLE_EPSILON then
        return pixel:Snap(target, scale), true
    end
    return current + ((target - current) * math.min(1, elapsed * TAB_SCROLL_ANIM_SPEED)), false
end

local function CreateOverflowGlyph(parent, text)
    local glyph = parent:CreateFontString(nil, "OVERLAY", "NumberFontNormal")
    glyph:SetText(text)
    glyph:SetTextColor(NORMAL_FONT_COLOR:GetRGB())
    local fontPath, fontHeight, fontFlags = glyph:GetFont()
    glyph:SetFont(fontPath, fontHeight - TAB_OVERFLOW_FONT_REDUCTION, fontFlags)
    glyph:Hide()
    return glyph
end

local function UpdateTabOverflow(scroll)
    local range = scroll:GetHorizontalScrollRange()
    local current = scroll:GetHorizontalScroll()
    scroll.LeftOverflow:SetShown(current > TAB_OVERFLOW_EPSILON)
    scroll.RightOverflow:SetShown(range - current > TAB_OVERFLOW_EPSILON)
end

local function EnsureTabScroll(parent, pixel)
    if parent._tabScroll then
        return parent._tabScroll
    end
    local scroll = CreateFrame("ScrollFrame", nil, parent)
    scroll.buttons = {}
    scroll:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, 0)
    scroll:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, 0)
    scroll:SetHeight(TAB_HEIGHT + TAB_DIVIDER_HEIGHT)
    scroll.Content = CreateFrame("Frame", nil, scroll)
    scroll.Content:SetSize(1, TAB_HEIGHT + TAB_DIVIDER_HEIGHT)
    scroll:SetScrollChild(scroll.Content)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(self, delta)
        local from = self.scrollTarget or self:GetHorizontalScroll()
        local range = self:GetHorizontalScrollRange()
        self.scrollTarget = math.min(math.max(from - delta * TAB_SCROLL_STEP, 0), range)
        self.Animator:Show()
    end)
    scroll:SetScript("OnScrollRangeChanged", function(self)
        local range = self:GetHorizontalScrollRange()
        if self:GetHorizontalScroll() > range then
            self:SetHorizontalScroll(range)
        end
        if self.scrollTarget and self.scrollTarget > range then
            self.scrollTarget = range
        end
        UpdateTabOverflow(self)
    end)
    scroll.Animator = CreateFrame("Frame", nil, scroll)
    scroll.Animator:Hide()
    scroll.Animator:SetScript("OnUpdate", function(_, elapsed)
        local current = scroll:GetHorizontalScroll()
        local position, settled =
            EaseTowards(pixel, current, scroll.scrollTarget or current, elapsed, scroll:GetEffectiveScale())
        scroll:SetHorizontalScroll(position)
        UpdateTabOverflow(scroll)
        if settled then
            scroll.Animator:Hide()
        end
    end)
    scroll.LeftOverflow = CreateOverflowGlyph(parent, TAB_OVERFLOW_LEFT_GLYPH)
    scroll.LeftOverflow:SetPoint("RIGHT", scroll, "LEFT", -TAB_OVERFLOW_GAP, TAB_OVERFLOW_Y_OFFSET)
    scroll.RightOverflow = CreateOverflowGlyph(parent, TAB_OVERFLOW_RIGHT_GLYPH)
    scroll.RightOverflow:SetPoint("LEFT", scroll, "RIGHT", TAB_OVERFLOW_GAP, TAB_OVERFLOW_Y_OFFSET)
    parent._tabScroll = scroll
    return scroll
end

function Layout:CreateTabBar(parent, tabNames, activeTab, onTabSelected, omitDivider)
    local pixel = self.pixel
    local buttons = {}
    local lastBtn = nil
    local scroll = EnsureTabScroll(parent, pixel)
    local rowWidth = 0
    for index, tabName in ipairs(tabNames) do
        local btn = scroll.buttons[index]
        if not btn then
            btn = CreateFrame("Button", nil, scroll.Content)
            btn.Text = btn:CreateFontString(nil, "OVERLAY", "GameFontNormal")
            btn.Text:SetPoint("CENTER")
            btn.highlight = btn:CreateTexture(nil, "BACKGROUND")
            btn.highlight:SetAtlas(TAB_HIGHLIGHT_ATLAS)
            pixel:Point(btn.highlight, "BOTTOM", btn, "BOTTOM", 0, -1)
            scroll.buttons[index] = btn
        end
        btn:ClearAllPoints()
        btn:SetHeight(TAB_HEIGHT)
        btn.Text:SetText(tabName)
        btn:SetWidth(btn.Text:GetStringWidth() + TAB_TEXT_PADDING)

        if lastBtn then
            btn:SetPoint("LEFT", lastBtn, "RIGHT", TAB_SPACING, 0)
            rowWidth = rowWidth + TAB_SPACING
        else
            btn:SetPoint("TOPLEFT", scroll.Content, "TOPLEFT", 0, 0)
        end
        rowWidth = rowWidth + btn:GetWidth()

        btn.highlight:SetSize(btn:GetWidth() * TAB_HIGHLIGHT_WIDTH_SCALE, TAB_HIGHLIGHT_HEIGHT)

        ApplyTabState(btn, tabName == activeTab)

        btn:SetScript("OnEnter", function(self)
            if not self.active then
                self.Text:SetTextColor(TAB_HOVER_COLOR.r, TAB_HOVER_COLOR.g, TAB_HOVER_COLOR.b)
            end
        end)
        btn:SetScript("OnLeave", function(self)
            if not self.active then
                self.Text:SetTextColor(TAB_INACTIVE_COLOR.r, TAB_INACTIVE_COLOR.g, TAB_INACTIVE_COLOR.b)
            end
        end)
        btn.tabCallback = onTabSelected
        btn:SetScript("OnClick", SelectTab)
        btn:Show()

        buttons[#buttons + 1] = btn
        lastBtn = btn
    end
    for index = #tabNames + 1, #scroll.buttons do
        local btn = scroll.buttons[index]
        btn.tabCallback = nil
        btn:SetScript("OnClick", nil)
        btn:SetScript("OnEnter", nil)
        btn:SetScript("OnLeave", nil)
        btn:Hide()
    end

    scroll.Content:SetWidth(math.max(rowWidth, 1))
    scroll.scrollTarget = nil
    scroll.Animator:Hide()
    scroll:SetHorizontalScroll(0)
    UpdateTabOverflow(scroll)

    local divider
    if not omitDivider then
        divider = scroll.divider or self:CreateTaperedDivider(scroll.Content, TAB_DIVIDER_COLOR, TAB_DIVIDER_HEIGHT)
        scroll.divider = divider
        divider:SetFrameLevel(scroll.Content:GetFrameLevel())
        divider:SetPoint("TOPLEFT", scroll.Content, "TOPLEFT", 0, -TAB_HEIGHT)
        divider:SetPoint("TOPRIGHT", scroll.Content, "TOPRIGHT", 0, -TAB_HEIGHT)
        divider:Show()
    elseif scroll.divider then
        scroll.divider:Hide()
    end

    return buttons, divider
end

function Layout:UpdateTabBar(buttons, activeTab)
    for _, btn in ipairs(buttons) do
        ApplyTabState(btn, btn.Text:GetText() == activeTab)
    end
end

function Layout:RegisterTabsWidgetType()
    self.TabBottomPadding = TAB_BOTTOM_PADDING
    self:RegisterWidgetType("tabs", function(container, def)
        local signature = table.concat(def.tabs, "|")
        local frame = table.remove(self.tabsPool)
        if not frame then
            frame = CreateFrame("Frame", nil, container)
            frame.OrbitType = "Tabs"
        end
        frame:SetParent(container)
        frame:SetHeight(TAB_HEIGHT + TAB_DIVIDER_HEIGHT + TAB_BOTTOM_PADDING)
        if frame._tabSignature == signature and frame._tabButtons then
            for _, btn in ipairs(frame._tabButtons) do
                btn.tabCallback = def.onTabSelected
                btn:SetScript("OnClick", SelectTab)
            end
            self:UpdateTabBar(frame._tabButtons, def.activeTab)
        else
            if frame._tabButtons then
                for _, btn in ipairs(frame._tabButtons) do
                    btn:Hide()
                end
            end
            frame._tabButtons = self:CreateTabBar(frame, def.tabs, def.activeTab, def.onTabSelected, true)
            frame._tabSignature = signature
        end

        return frame
    end)
end

table.freeze(Layout)
