local _, addon = ...
local UI = addon.LibOrbitUI
local DIVIDER_COLOR = { r = 0.3, g = 0.3, b = 0.3 }
local DIVIDER_HEIGHT = 1
local PLACEHOLDER_HEIGHT = 1
local DISABLED_ALPHA = 0.4
local DISABLED_LEVEL_OFFSET = 10
local FOOTER_COLUMNS = 2

UI.ConfigPanel = {}
local PanelMixin = {}

local function CreateContent(renderer, panel)
    local constants = renderer.constants
    local content = CreateFrame("Frame", nil, panel.ScrollFrame)
    content:SetWidth(constants.Panel.Width - constants.Panel.ScrollbarWidth - constants.Panel.ContentPadding * 2)
    content:SetHeight(PLACEHOLDER_HEIGHT)
    return content
end

function PanelMixin:CreateFrame(dialog)
    local constants, layout = self.constants, self.layout
    local footerHeight = constants.Footer.TopPadding + constants.Footer.ButtonHeight + constants.Footer.BottomPadding
    local panel = CreateFrame("Frame", nil, dialog, "BackdropTemplate")
    panel.configPanelOwner = self
    panel:SetWidth(constants.Panel.Width)
    panel:SetPoint("TOP", dialog.Title, "BOTTOM", 0, -constants.Panel.TitleGap)
    local header = CreateFrame("Frame", nil, panel)
    header:SetHeight(constants.Panel.ContentPadding)
    header:SetPoint("TOPLEFT", panel, "TOPLEFT", 0, 0)
    header:SetPoint("TOPRIGHT", panel, "TOPRIGHT", 0, 0)
    panel.Header = header
    panel.HeaderDivider = layout:CreateTaperedDivider(header, DIVIDER_COLOR, DIVIDER_HEIGHT)
    panel.HeaderDivider:SetPoint("BOTTOMLEFT", header, "BOTTOMLEFT", 0, layout.TabBottomPadding)
    panel.HeaderDivider:SetPoint("BOTTOMRIGHT", header, "BOTTOMRIGHT", 0, layout.TabBottomPadding)
    panel.ScrollFrame = CreateFrame("ScrollFrame", nil, panel)
    panel.ScrollFrame:SetClipsChildren(true)
    panel.ScrollFrame:SetPoint(
        "TOPLEFT",
        panel,
        "TOPLEFT",
        constants.Panel.ContentPadding,
        -constants.Panel.ContentPadding
    )
    panel.ScrollFrame:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", -constants.Panel.ScrollbarWidth, footerHeight)
    self.scrollBar:Attach(panel.ScrollFrame, {
        rightOffset = constants.Panel.ScrollbarWidth + constants.Panel.ScrollbarReach,
    })
    panel.Content = CreateContent(self, panel)
    panel.ScrollFrame:SetScrollChild(panel.Content)
    panel.Tabs = {}
    panel.Footer = CreateFrame("Frame", nil, panel)
    panel.Footer:SetHeight(footerHeight)
    panel.Footer:SetPoint("BOTTOMLEFT", panel, "BOTTOMLEFT", 0, 0)
    panel.Footer:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", 0, 0)
    local divider = layout:CreateTaperedDivider(panel.Footer, DIVIDER_COLOR, DIVIDER_HEIGHT)
    divider:SetPoint("TOPLEFT", panel.Footer, "TOPLEFT", 0, 0)
    divider:SetPoint("TOPRIGHT", panel.Footer, "TOPRIGHT", 0, 0)
    return panel
end

function PanelMixin:SelectContent(panel, tabKey)
    local content
    if tabKey then
        panel.Content:Hide()
        for key, tab in pairs(panel.Tabs) do
            if key ~= tabKey then
                tab:Hide()
            end
        end
        if not panel.Tabs[tabKey] then
            panel.Tabs[tabKey] = CreateContent(self, panel)
        end
        content = panel.Tabs[tabKey]
    else
        content = panel.Content
        for _, tab in pairs(panel.Tabs) do
            tab:Hide()
        end
    end
    panel.CurrentTabKey = tabKey
    content:Show()
    panel.ScrollFrame:SetScrollChild(content)
    return content
end

function PanelMixin:Invalidate(panel, tabKey)
    panel.configSizingGeneration = (panel.configSizingGeneration or 0) + 1
    if tabKey then
        local content = panel.Tabs[tabKey]
        if content then
            content.OrbitRendered = nil
        end
    else
        panel.Content.OrbitRendered = nil
        for _, content in pairs(panel.Tabs) do
            content.OrbitRendered = nil
        end
    end
end

function PanelMixin:RenderControl(container, definition, getValue, onChange, onClick)
    local layout = self.layout
    local control
    if definition.type == "button" then
        control = layout:CreateButton(container, definition.text or definition.label, onClick, definition.width)
    else
        control = layout:CreateWidget(container, definition, getValue, onChange)
    end
    if not control then
        return nil
    end
    local disabled = definition.disabled
    if type(disabled) == "function" then
        disabled = disabled()
    end
    local enabled = not disabled and not control.configUnavailable and UI.Config.IsControlEnabled(definition)
    control:SetAlpha(enabled and 1 or DISABLED_ALPHA)
    if control.SetEnabled then
        control:SetEnabled(enabled)
    end
    if control.Slider and control.Slider.SetEnabled then
        control.Slider:SetEnabled(enabled)
    end
    if not enabled then
        if not control._disabledOverlay then
            local overlay = CreateFrame("Frame", nil, control)
            overlay:SetAllPoints()
            overlay:SetFrameLevel(control:GetFrameLevel() + DISABLED_LEVEL_OFFSET)
            overlay:EnableMouse(true)
            control._disabledOverlay = overlay
        end
        control._disabledOverlay:Show()
    elseif control._disabledOverlay then
        control._disabledOverlay:Hide()
    end
    layout:AddControl(container, control)
    return control
end

function PanelMixin:Release(panel)
    self:Invalidate(panel)
    self.context.tooltipHide()
    local layout = self.layout
    if layout.promptOptions then
        layout:HidePrompts()
    end
    layout:Reset(panel.Header)
    layout:Reset(panel.Content)
    for _, content in pairs(panel.Tabs) do
        layout:Reset(content)
    end
    layout:Reset(panel.Footer)
    panel:Hide()
end

function PanelMixin:Render(panel, options)
    assert(panel.configPanelOwner == self, "LibOrbitUI panel belongs to another renderer")
    local layout, constants = self.layout, self.constants
    panel:Show()
    local content = self:SelectContent(panel, options.tabKey)
    local tabsDefinition
    for _, definition in ipairs(options.controls) do
        if definition.type == "tabs" then
            tabsDefinition = definition
            break
        end
    end
    layout:Reset(panel.Header)
    if tabsDefinition then
        options.renderControl(panel.Header, tabsDefinition)
    end
    local headerHeight = math.max(layout:Stack(panel.Header, 0, 0), constants.Panel.ContentPadding)
    panel.Header:SetHeight(headerHeight)
    panel.HeaderDivider:SetShown(tabsDefinition ~= nil)
    local cached = options.tabKey and options.cache ~= false and content.OrbitRendered
    if not cached then
        layout:Reset(content)
        layout:Reset(panel.Footer)
        for _, definition in ipairs(options.controls) do
            local visible = definition ~= tabsDefinition and UI.Config.IsControlVisible(definition)
            if visible then
                options.renderControl(content, definition)
            end
        end
    else
        layout:Reset(panel.Footer)
    end
    local footerHeight = options.renderFooter(panel.Footer)
    if not cached then
        local height = layout:Stack(content, 0, constants.Panel.ContentPadding)
        content:SetHeight(height)
        content.OrbitContentHeight = height
        content.OrbitRendered = true
    end
    local height = content.OrbitContentHeight or content:GetHeight()
    panel.ScrollFrame:SetPoint("TOPLEFT", panel, "TOPLEFT", constants.Panel.ContentPadding, -headerHeight)
    panel.ScrollFrame:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", -constants.Panel.ScrollbarWidth, footerHeight)
    local panelHeight = math.min(height + footerHeight + headerHeight, constants.Panel.MaxHeight)
    panel:SetHeight(panelHeight)
    local dialog = panel:GetParent()
    local dialogHeight = panelHeight + constants.Panel.TitlePadding
    dialog:SetHeight(dialogHeight)
    dialog:SetWidth(constants.Panel.DialogWidth)
    panel.configSizingGeneration = (panel.configSizingGeneration or 0) + 1
    local generation = panel.configSizingGeneration
    RunNextFrame(function()
        if panel.configSizingGeneration == generation and dialog:IsShown() and panel:IsShown() then
            dialog:SetHeight(dialogHeight)
        end
    end)
    return content
end

function PanelMixin:LayoutFooter(footer, buttons, width)
    local constants, layout = self.constants, self.layout
    local count = #buttons
    local rows = math.ceil(count / FOOTER_COLUMNS)
    local padding = constants.Footer.SidePadding
    local spacing = constants.Footer.ButtonSpacing
    local panelWidth = width or footer:GetParent():GetWidth()
    local availableWidth = panelWidth - padding * 2
    local top = constants.Footer.TopPadding
    local height = constants.Footer.ButtonHeight
    local rowSpacing = constants.Footer.RowSpacing
    local bottom = constants.Footer.BottomPadding
    local currentY = -top
    for row = 1, rows do
        local first = (row - 1) * FOOTER_COLUMNS + 1
        local last = math.min(row * FOOTER_COLUMNS, count)
        local rowCount = last - first + 1
        local buttonWidth = (availableWidth - spacing * (rowCount - 1)) / rowCount
        local currentX = padding
        for index = first, last do
            local button = buttons[index]
            layout:AddControl(footer, button)
            button:ClearAllPoints()
            button:SetPoint("TOPLEFT", footer, "TOPLEFT", currentX, currentY)
            button:SetWidth(buttonWidth)
            button:SetHeight(height)
            currentX = currentX + buttonWidth + spacing
        end
        currentY = currentY - height - rowSpacing
    end
    local totalHeight = top + rows * height + math.max(0, rows - 1) * rowSpacing + bottom
    footer:SetHeight(totalHeight)
    return totalHeight
end

table.freeze(PanelMixin)

function UI.ConfigPanel:Create(context, layout, constants, scrollBar)
    return Mixin({ context = context, layout = layout, constants = constants, scrollBar = scrollBar }, PanelMixin)
end
