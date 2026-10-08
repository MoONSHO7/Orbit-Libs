local _, addon = ...
local UI = addon.LibOrbitUI
local DIVIDER_COLOR = { r = 0.3, g = 0.3, b = 0.3 }
local DIVIDER_HEIGHT = 1
local PLACEHOLDER_HEIGHT = 1
local DISABLED_ALPHA = 0.55
local DISABLED_LEVEL_OFFSET = 10
local FOOTER_COLUMNS = 2
local PASSIVE_CONTROLS = { header = true, spacer = true, description = true, tabs = true }

UI.ConfigPanel = {}
local PanelMixin = {}

local function CreateContent(renderer, panel)
    local constants = renderer.constants
    local content = CreateFrame("Frame", nil, panel.ScrollFrame)
    content:SetWidth(constants.Panel.Width - constants.Panel.ContentPadding * 2)
    content:SetHeight(PLACEHOLDER_HEIGHT)
    return content
end

local function SizePanel(renderer, panel, content, headerHeight, footerHeight)
    local constants = renderer.constants
    local height = content.OrbitContentHeight or content:GetHeight()
    panel.ScrollFrame:SetPoint("TOPLEFT", panel, "TOPLEFT", constants.Panel.ContentPadding, -headerHeight)
    panel.ScrollFrame:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", -constants.Panel.ContentPadding, footerHeight)
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
    panel.ScrollFrame:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", -constants.Panel.ContentPadding, footerHeight)
    self.scrollBar:Attach(panel.ScrollFrame, {
        rightOffset = constants.Panel.ContentPadding + constants.Panel.ScrollbarReach,
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

local function ControlTooltip(control, definition)
    local presentation = control and control.configPresentation or definition
    local lines, seen = {}, {}
    local function Add(text)
        if text and text ~= "" and not seen[text] then
            lines[#lines + 1] = text
            seen[text] = true
        end
    end
    local unavailable = control and control.configUnavailable
    if not UI.Config.CanInteract(definition, unavailable) or not UI.Config.CanInteract(presentation, unavailable) then
        Add(UI.Config.GetDisabledReason(presentation) or UI.Config.GetDisabledReason(definition))
    end
    local help = presentation.tooltip or definition.tooltip
    if type(help) == "function" then
        help = help(control)
    end
    Add(help)
    for _, line in ipairs(presentation.tooltipLines or definition.tooltipLines or {}) do
        if line.title or line.hint then
            Add(line.title or line.hint)
        elseif line.key and line.value then
            Add(tostring(line.key) .. "  " .. tostring(line.value))
        end
    end
    local parent = control and control:GetParent()
    Add(UI.Config.ResolveText(presentation.scopeText or definition.scopeText or (parent and parent.configScopeText)))
    Add(UI.Config.ResolveText(presentation.sourceText or definition.sourceText))
    return #lines > 0 and table.concat(lines, "\n") or nil
end

local function ApplyControlTooltip(renderer, control, definition)
    if PASSIVE_CONTROLS[definition.type] then
        return
    end
    local presentation = control.configPresentation or definition
    local parent = control:GetParent()
    local hasTooltip = definition.tooltip
        or definition.disabledReason
        or definition.tooltipLines
        or definition.sourceText
        or definition.scopeText
        or presentation.tooltip
        or presentation.disabledReason
        or presentation.tooltipLines
        or presentation.sourceText
        or presentation.scopeText
        or (parent and parent.configScopeText)
    renderer.layout:AttachLabelTooltip(control, definition.label or definition.text, hasTooltip and function()
        return ControlTooltip(control, definition)
    end or nil)
    local hover = control._tooltipHover
    if hover and hasTooltip then
        hover:ClearAllPoints()
        if control.configInlineSourceState then
            hover:SetPoint("TOPLEFT", control.Label, "TOPLEFT")
            hover:SetPoint("BOTTOMRIGHT", control, "BOTTOMRIGHT")
        else
            hover:SetAllPoints(control.Label or control)
        end
        hover:SetPropagateMouseClicks(true)
    end
end

function PanelMixin:ApplyControlState(control, definition)
    control.configStateApplied = true
    local enabled = UI.Config.CanInteract(definition, control.configUnavailable)
    control:SetAlpha(enabled and 1 or DISABLED_ALPHA)
    if control.Label then
        control.Label:SetIgnoreParentAlpha(true)
    end
    if control.SetEnabled then
        control:SetEnabled(enabled)
    end
    if control.Slider and control.Slider.SetEnabled then
        control.Slider:SetEnabled(enabled)
    end
    if control.Control and control.Control.SetEnabled then
        control.Control:SetEnabled(enabled)
    end
    if control.EditBox and control.EditBox.SetEnabled then
        control.EditBox:SetEnabled(enabled)
    end
    local function ApplyCheckboxState(checkbox)
        checkbox.configParentEnabled = enabled
        local config = checkbox.valueCheckboxDefinition
        checkbox:SetEnabled(enabled and config ~= nil and UI.Config.CanInteract(config))
    end
    if control.ValueCheckbox then
        ApplyCheckboxState(control.ValueCheckbox)
    end
    for _, checkbox in pairs(control.ValueCheckboxes or {}) do
        ApplyCheckboxState(checkbox)
    end
    if not enabled then
        if control.Dropdown then
            control.Dropdown:Hide()
        end
        if not control._disabledOverlay then
            local overlay = CreateFrame("Frame", nil, control)
            overlay:SetAllPoints()
            overlay:SetFrameLevel(control:GetFrameLevel() + DISABLED_LEVEL_OFFSET)
            overlay:EnableMouse(true)
            control._disabledOverlay = overlay
        end
        local tooltip = self.context.tooltip
        control._disabledOverlay:SetScript("OnEnter", function(overlay)
            local text = ControlTooltip(control, definition)
            if not text then
                return
            end
            tooltip:SetOwner(overlay, "ANCHOR_RIGHT")
            tooltip:SetText(definition.label or definition.text or "", 1, 1, 1)
            tooltip:AddLine(text, 1, 1, 1, true)
            tooltip:Show()
        end)
        control._disabledOverlay:SetScript("OnLeave", self.context.tooltipHide)
        control._disabledOverlay:Show()
    elseif control._disabledOverlay then
        control._disabledOverlay:Hide()
    end
    ApplyControlTooltip(self, control, definition)
    return enabled
end

local function ClearMixed(control)
    if not control.configMixed then
        return
    end
    control.configMixed = nil
    if control.configMixedMark then
        control.configMixedMark:Hide()
    end
    if control.configMixedLabel then
        control.Label:SetText(control.configMixedLabel)
        control.configMixedLabel = nil
    end
end

function PanelMixin:RenderControl(container, definition, getValue, onChange, onClick)
    local layout = self.layout
    local control
    local binding = {}
    local metadataControls = {}
    local presentationGeneration = 0
    local function CanInteract()
        return control
            and control.configBinding == binding
            and control:IsVisible()
            and UI.Config.CanInteract(definition, control.configUnavailable)
    end
    local function RefreshPresentation()
        if not control or control.configBinding ~= binding then
            return
        end
        presentationGeneration = presentationGeneration + 1
        local generation = presentationGeneration
        local presentation = definition.refreshPresentation and definition.refreshPresentation() or definition
        control.configPresentation = presentation
        local inlineChanged = false
        local inlineSource = presentation.inlineSource
        if inlineSource == nil then
            inlineSource = definition.inlineSource
        end
        if inlineSource or control.configInlineSourceState then
            inlineChanged = layout:ApplyInlineSource(control, {
                inlineSource = inlineSource,
                sourceText = presentation.sourceText or definition.sourceText,
            })
        end
        ApplyControlTooltip(self, control, definition)
        local current = UI.Config.BindDefinition(presentation, function()
            return generation == presentationGeneration and CanInteract()
        end, RefreshPresentation)
        local action = current.onAction or current.onInherit
        local actionText = action and UI.Config.ResolveText(presentation.actionText or presentation.inheritText)
        local enabled = UI.Config.CanInteract(definition, control.configUnavailable)
            and UI.Config.CanInteract(presentation, control.configUnavailable)
        local count, changed = 0, inlineChanged
        local function Row(text, label, callback, active)
            count = count + 1
            local previous = metadataControls[count]
            local oldHeight = previous and previous:IsShown() and previous:GetHeight() or 0
            local metadata = layout:CreateControlMetadata(container, text, label, callback, previous)
            metadata.Action:SetEnabled(enabled and active ~= false)
            if not previous then
                layout:AddControl(container, metadata, metadataControls[count - 1] or control)
                metadataControls[count] = metadata
            else
                metadata:Show()
            end
            changed = changed or oldHeight ~= metadata:GetHeight()
        end
        if actionText then
            Row(nil, actionText, action)
        end
        for _, extra in ipairs(current.metadataActions or {}) do
            if UI.Config.IsControlVisible(extra) then
                local text = UI.Config.ResolveText(extra.text)
                if text then
                    Row(nil, text, extra.callback, UI.Config.IsControlEnabled(extra))
                end
            end
        end
        for index = count + 1, #metadataControls do
            local metadata = metadataControls[index]
            changed = changed or metadata:IsShown()
            metadata.onAction = nil
            metadata:Hide()
        end
        if changed and container.configRelayout then
            container.configRelayout()
        end
    end
    local bound = UI.Config.BindDefinition(definition, CanInteract, RefreshPresentation)
    bound.tooltip = function()
        return ControlTooltip(control, definition)
    end
    local function Commit(value)
        if CanInteract() then
            ClearMixed(control)
            if onChange then
                local result = onChange(value)
                RefreshPresentation()
                return result
            end
        elseif control and control.configBinding == binding and control.configMixed and definition.type == "slider" then
            control.Value:SetText(definition.mixedText)
        end
    end
    if definition.type == "button" then
        control = layout:CreateButton(container, definition.text or definition.label, function(...)
            if CanInteract() and onClick then
                local result = onClick(...)
                RefreshPresentation()
                return result
            end
        end, definition.width)
    else
        control = layout:CreateWidget(container, bound, getValue, Commit)
    end
    if not control then
        return nil
    end
    control.configBinding = binding
    if definition.mixed then
        assert(type(definition.mixedText) == "string", "LibOrbitUI mixed controls need a localized label")
        control.configMixed = true
        control.configMixedText = definition.mixedText
        if definition.type == "slider" then
            control.Value:SetText(definition.mixedText)
        elseif definition.type == "dropdown" then
            control.Control.Text:SetText(definition.mixedText)
        elseif definition.type == "checkbox" then
            control:SetChecked(false)
            if not control.configMixedMark then
                control.configMixedMark = control._cb:CreateFontString(nil, "OVERLAY", self.constants.UI.ValueFont)
                control.configMixedMark:SetPoint("CENTER")
                control.configMixedMark:SetText("–")
            end
            control.configMixedMark:Show()
            control.configMixedLabel = definition.label
            control.Label:SetText(definition.label .. " (" .. definition.mixedText .. ")")
        end
    end
    self:ApplyControlState(control, definition)
    layout:AddControl(container, control)
    RefreshPresentation()
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
    content.configScopeText = options.scopeText
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
        local count = 0
        for _, definition in ipairs(options.controls) do
            local visible = definition ~= tabsDefinition and UI.Config.IsControlVisible(definition)
            if visible then
                count = count + 1
                options.renderControl(content, definition)
            end
        end
        if count == 0 and options.emptyText then
            self:RenderControl(content, { type = "description", text = options.emptyText })
        end
    else
        layout:Reset(panel.Footer)
    end
    local footerHeight = options.renderFooter(panel.Footer)
    content.configRelayout = function()
        local height = layout:Stack(content, 0, constants.Panel.ContentPadding)
        content:SetHeight(height)
        content.OrbitContentHeight = height
        SizePanel(self, panel, content, headerHeight, footerHeight)
    end
    if cached then
        SizePanel(self, panel, content, headerHeight, footerHeight)
    else
        content.configRelayout()
        content.OrbitRendered = true
    end
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
