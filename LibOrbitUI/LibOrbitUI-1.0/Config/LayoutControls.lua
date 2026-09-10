local _, addon = ...
local Layout = addon.LibOrbitUI.Layout.Methods
local SPACER_DEFAULT_HEIGHT = 20
local LABEL_FALLBACK_WIDTH = 300
local LABEL_WIDTH_INSET = 20
local LABEL_MIN_HEIGHT = 20
local LABEL_HEIGHT_PAD = 4

local PICKER_ANCHOR_PADDING = 25

function Layout.GetPickerAnchor(frame)
    local owner = frame
    while owner:GetParent() and owner:GetParent() ~= UIParent do
        owner = owner:GetParent()
    end
    return { frame = owner, point = "TOPLEFT", relativePoint = "TOPRIGHT", x = PICKER_ANCHOR_PADDING, y = 0 }
end

function Layout:BuildDialogChrome(frame, titleText)
    local C = self.DialogChrome
    frame.NineSlice = CreateFrame("Frame", nil, frame, "NineSlicePanelTemplate")
    frame.NineSlice.layoutType = "ButtonFrameTemplateNoPortrait"
    NineSliceUtil.ApplyLayoutByName(frame.NineSlice, "ButtonFrameTemplateNoPortrait")
    frame.NineSlice:SetFrameLevel(frame:GetFrameLevel() + C.NINESLICE_LEVEL_OFFSET)
    frame.Bg = frame:CreateTexture(nil, "BACKGROUND", nil, -6)
    self.chrome:ApplyBackdrop(frame.Bg)
    frame.Bg:SetPoint("TOPLEFT", C.BG_INSET_LEFT, -C.BG_INSET_TOP)
    frame.Bg:SetPoint("BOTTOMRIGHT", -C.BG_INSET_RIGHT, C.BG_INSET_BOTTOM)
    frame.contentLevel = frame.NineSlice:GetFrameLevel() + C.CONTENT_LEVEL_OFFSET
    frame.TitleContainer = CreateFrame("Frame", nil, frame)
    frame.TitleContainer:SetFrameLevel(frame.contentLevel)
    frame.TitleContainer:SetPoint("TOPLEFT", C.BG_INSET_LEFT, -C.TITLE_OFFSET)
    frame.TitleContainer:SetPoint("TOPRIGHT", -C.BG_INSET_LEFT, -C.TITLE_OFFSET)
    frame.TitleContainer:SetHeight(C.BG_INSET_TOP)
    frame.title = frame.TitleContainer:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    frame.title:SetPoint("TOP", frame.TitleContainer, "TOP")
    frame.title:SetText(titleText)
end

-- A texture takes one linear gradient, so the end tapers are two mirrored halves meeting at the center
function Layout:CreateTaperedDivider(parent, color, height)
    local divider = CreateFrame("Frame", nil, parent)
    divider:SetHeight(height)
    local fadeIn = divider:CreateTexture(nil, "OVERLAY")
    fadeIn:SetColorTexture(1, 1, 1, 1)
    fadeIn:SetGradient(
        "HORIZONTAL",
        CreateColor(color.r, color.g, color.b, 0),
        CreateColor(color.r, color.g, color.b, 1)
    )
    fadeIn:SetPoint("TOPLEFT")
    fadeIn:SetPoint("BOTTOMLEFT")
    fadeIn:SetPoint("RIGHT", divider, "CENTER", 0, 0)
    local fadeOut = divider:CreateTexture(nil, "OVERLAY")
    fadeOut:SetColorTexture(1, 1, 1, 1)
    fadeOut:SetGradient(
        "HORIZONTAL",
        CreateColor(color.r, color.g, color.b, 1),
        CreateColor(color.r, color.g, color.b, 0)
    )
    fadeOut:SetPoint("TOPRIGHT")
    fadeOut:SetPoint("BOTTOMRIGHT")
    fadeOut:SetPoint("LEFT", divider, "CENTER", 0, 0)
    return divider
end

function Layout:CreateSectionHeader(parent, text, frame)
    frame = frame or CreateFrame("Frame", nil, parent)
    frame:SetParent(parent)
    frame:SetHeight(20)
    if not frame.text then
        frame.text = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
        frame.text:SetPoint("TOPLEFT")
        frame.text:SetPoint("TOPRIGHT")
        frame.text:SetJustifyH("LEFT")
    end
    frame.text:SetText(text)
    frame.OrbitType = "Header"
    return frame
end

-- [ DESCRIPTION ]------------------------------------------------------------------------------------------------------
function Layout:CreateDescription(parent, text, color, frame)
    frame = frame or CreateFrame("Frame", nil, parent)
    frame:SetParent(parent)
    frame:SetHeight(20)
    if not frame.text then
        frame.text = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
        frame.text:SetPoint("TOPLEFT")
        frame.text:SetPoint("TOPRIGHT")
        frame.text:SetJustifyH("LEFT")
        frame.text:SetWordWrap(true)
        frame.text:SetNonSpaceWrap(true)
        frame:SetScript("OnSizeChanged", function(self, w)
            if w > 1 then
                self.text:SetWidth(w)
                self:SetHeight(math.max(16, self.text:GetStringHeight() + 4))
            end
        end)
    end
    frame.text:SetText(text)
    color = color or self.Advanced.MUTED
    frame.text:SetTextColor(color.r, color.g, color.b, color.a or 1)
    frame.OrbitType = "Description"
    return frame
end

-- [ ACCORDION ]--------------------------------------------------------------------------------------------------------
local ACCORDION_BAR_HEIGHT = 30
local ACCORDION_ART_SHADE = 0.75
function Layout:CreateAccordion(parent, name)
    local pixel = self.pixel
    local GameTooltip, GameTooltip_Hide = self.tooltip, self.tooltipHide
    local section = CreateFrame("Frame", nil, parent)
    section:SetHeight(ACCORDION_BAR_HEIGHT)
    section._expanded = false
    section._contentHeight = 1
    local bar = CreateFrame("Button", nil, section)
    bar:SetHeight(ACCORDION_BAR_HEIGHT)
    bar:SetPoint("TOPLEFT")
    bar:SetPoint("TOPRIGHT", -20, 0)
    local background = bar:CreateTexture(nil, "BACKGROUND")
    background:SetAtlas("common-button-list-collapseExpand")
    background:SetAllPoints()
    background:SetVertexColor(ACCORDION_ART_SHADE, ACCORDION_ART_SHADE, ACCORDION_ART_SHADE)
    local highlight = bar:CreateTexture(nil, "HIGHLIGHT")
    highlight:SetAtlas("common-button-list-collapseExpand")
    highlight:SetAllPoints()
    highlight:SetVertexColor(ACCORDION_ART_SHADE, ACCORDION_ART_SHADE, ACCORDION_ART_SHADE)
    highlight:SetBlendMode("ADD")
    highlight:SetAlpha(0.4)
    bar:SetHighlightTexture(highlight)
    local collapseIcon = bar:CreateTexture(nil, "ARTWORK")
    collapseIcon:SetPoint("RIGHT", -6, 0) -- px-ok: matches Blizzard's ListHeaderVisualTemplate
    local label = bar:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    label:SetPoint("LEFT", 8, 1) -- px-ok: matches Blizzard's ListHeaderVisualTemplate
    label:SetPoint("RIGHT", collapseIcon, "LEFT", -4, 1) -- px-ok: matches Blizzard's ListHeaderVisualTemplate
    label:SetJustifyH("LEFT")
    label:SetText(name)
    local status = bar:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    pixel:Point(status, "RIGHT", collapseIcon, "LEFT", -14, 1)
    status:SetJustifyH("RIGHT")
    local body = CreateFrame("Frame", nil, section)
    body:SetPoint("TOPLEFT", bar, "BOTTOMLEFT", 0, -4)
    body:SetPoint("TOPRIGHT", bar, "BOTTOMRIGHT", 0, -4)
    body:SetHeight(1) -- px-ok: placeholder, grows with content
    body:Hide()
    local function UpdateVisual()
        collapseIcon:SetAtlas(section._expanded and "common-button-list-minus" or "common-button-list-plus", true)
        body:SetShown(section._expanded)
        section:SetHeight(
            section._expanded
                    and pixel:Snap(ACCORDION_BAR_HEIGHT + section._contentHeight + 4, section:GetEffectiveScale())
                or ACCORDION_BAR_HEIGHT
        )
    end
    bar:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    bar:SetScript("OnClick", function(_, button)
        if button == "RightButton" then
            if section._onRightClick then
                section._onRightClick()
            end
            return
        end
        section._expanded = not section._expanded
        UpdateVisual()
        if section._onToggle then
            section._onToggle()
        end
    end)
    bar:SetScript("OnEnter", function(self)
        if not section._rightClickTip then
            return
        end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText(section._rightClickTip, 1, 1, 1)
        GameTooltip:Show()
    end)
    bar:SetScript("OnLeave", GameTooltip_Hide)
    function section:GetBody()
        return body
    end
    function section:GetBar()
        return bar
    end
    function section:SetStatus(text)
        status:SetText(text or "")
    end
    function section:SetContentHeight(h)
        self._contentHeight = h
        body:SetHeight(h)
        UpdateVisual()
    end
    function section:IsExpanded()
        return self._expanded
    end
    function section:SetExpanded(state)
        self._expanded = state
        UpdateVisual()
        if self._onToggle then
            self._onToggle()
        end
    end
    function section:Reset(name)
        label:SetText(name)
        status:SetText("")
        self._expanded = false
        self._contentHeight = 1
        self._onToggle = nil
        self._profileId = nil
        self._onRightClick = nil
        self._rightClickTip = nil
        UpdateVisual()
    end
    section.OrbitType = "Accordion"
    return section
end

-- [ SCROLL AREA ]------------------------------------------------------------------------------------------------------
function Layout:CreateScrollArea(parent, topY, bottomPad)
    local A = self.Advanced
    topY = topY or A.CONTENT_START_Y
    bottomPad = bottomPad or A.PADDING
    local scrollFrame = CreateFrame("ScrollFrame", nil, parent)
    scrollFrame:SetPoint("TOPLEFT", A.PADDING, topY)
    scrollFrame:SetPoint("BOTTOMRIGHT", -A.PADDING - A.SCROLLBAR_WIDTH, bottomPad)
    local scrollChild = CreateFrame("Frame", nil, scrollFrame)
    scrollChild:SetWidth(scrollFrame:GetWidth())
    scrollFrame:SetScrollChild(scrollChild)
    self.scrollBar:Attach(scrollFrame, {
        rightOffset = A.SCROLLBAR_WIDTH,
        rightOffsetPixels = A.SCROLLBAR_RIGHT_SHIFT_PIXELS,
    })
    scrollFrame:HookScript("OnSizeChanged", function(_, w)
        scrollChild:SetWidth(w)
    end)
    function scrollFrame:UpdateContentHeight(h)
        scrollChild:SetHeight(h)
    end
    return scrollFrame, scrollChild
end

function Layout:AttachLabelTooltip(control, label, tooltip)
    local Constants = self.constants
    local GameTooltip, GameTooltip_Hide = self.tooltip, self.tooltipHide
    if not control then
        return
    end
    local hover = control._tooltipHover
    if not tooltip then
        if hover then
            hover:Hide()
        end
        return
    end
    if not hover then
        hover = CreateFrame("Frame", nil, control)
        hover:SetPoint("TOPLEFT", control, "TOPLEFT", 0, 0)
        hover:SetPoint("BOTTOMLEFT", control, "BOTTOMLEFT", 0, 0)
        hover:SetWidth(Constants.Widget.LabelWidth + Constants.Widget.LabelGap)
        hover:EnableMouse(true)
        control._tooltipHover = hover
    end
    hover._label, hover._tooltip = label, tooltip
    hover:Show()
    hover:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText(self._label or "", 1, 1, 1)
        local tt = self._tooltip
        GameTooltip:AddLine(type(tt) == "function" and tt(control) or tt, nil, nil, nil, true)
        GameTooltip:Show()
    end)
    hover:SetScript("OnLeave", GameTooltip_Hide)
end

function Layout:InitializeBaseWidgetTypes()
    local Constants = self.constants
    local pixel = self.pixel
    self:RegisterWidgetType("checkbox", function(container, def, getValue, callback)
        local opts
        if def.valueText ~= nil then
            opts = { valueText = type(def.valueText) == "function" and def.valueText() or def.valueText }
        end
        return self:CreateCheckbox(container, def.label, def.tooltip, getValue(), callback, opts)
    end)

    self:RegisterWidgetType("slider", function(container, def, getValue, callback)
        local slider = self:CreateSlider(
            container,
            def.label,
            def.min,
            def.max,
            def.step,
            def.formatter,
            getValue(),
            callback,
            def
        )
        if slider then
            slider.SettingKey = def.key
        end
        self:AttachLabelTooltip(slider, def.label, def.tooltip)
        return slider
    end)

    self:RegisterWidgetType("dropdown", function(container, def, getValue, callback)
        local options = def.options
        if type(options) == "function" then
            options = options()
        end
        local dropdown = self:CreateDropdown(
            container,
            def.label,
            options,
            getValue(),
            callback,
            def.valueCheckbox,
            def.valueColor,
            def.multiSelect
        )
        self:AttachLabelTooltip(dropdown, def.label, def.tooltip)
        return dropdown
    end)

    self:RegisterWidgetType("button", function(container, def, getValue, callback)
        return self:CreateButton(container, def.text, callback, def.width)
    end)

    self:RegisterWidgetType("editbox", function(container, def, getValue, callback)
        return self:CreateEditBox(container, def.label, getValue(), callback, def.width, def.height, def.multiline, def)
    end)

    self:RegisterWidgetType("formatinput", function(container, def, getValue, callback)
        return self:CreateFormatInput(
            container,
            def.label,
            getValue(),
            callback,
            def.tooltipLines,
            def.validate,
            def.preview
        )
    end)

    self:RegisterWidgetType("header", function(container, def)
        return self:CreateSectionHeader(container, def.text or def.label, table.remove(self.headerPool))
    end)

    self:RegisterWidgetType("spacer", function(container, def)
        local frame = table.remove(self.spacerPool)
        if not frame then
            frame = CreateFrame("Frame", nil, container)
            frame.OrbitType = "Spacer"
        end
        frame:SetParent(container)
        frame:SetHeight(def.height or SPACER_DEFAULT_HEIGHT)
        return frame
    end)

    self:RegisterWidgetType("label", function(container, def)
        local frame = table.remove(self.labelPool)
        if not frame then
            frame = CreateFrame("Frame", nil, container)
            frame.text = frame:CreateFontString(nil, "ARTWORK", Constants.UI.LabelFont)
            frame.text:SetPoint("TOPLEFT", 0, 0)
            frame.text:SetJustifyH("LEFT")
            frame.text:SetWordWrap(true)
            frame.text:SetNonSpaceWrap(true)
            frame.OrbitType = "Label"
        end
        frame:SetParent(container)
        local scale = frame:GetEffectiveScale()
        local containerWidth = container:GetWidth() or LABEL_FALLBACK_WIDTH
        frame.text:SetWidth(pixel:Snap(containerWidth - LABEL_WIDTH_INSET, scale))
        frame.text:SetText(def.text or "")
        local textHeight = frame.text:GetStringHeight()
        frame:SetHeight(math.max(LABEL_MIN_HEIGHT, pixel:Snap(textHeight + LABEL_HEIGHT_PAD, scale)))
        return frame
    end)

    self:RegisterTabsWidgetType()
    self:RegisterWidgetType("description", function(container, def)
        local frame = self:CreateDescription(container, def.text or "", def.color, table.remove(self.descriptionPool))

        local C = self.constants
        local width = C.Panel.Width - (C.Panel.ContentPadding * 2) - C.Panel.ScrollbarWidth - 10

        frame.text:SetWidth(width)
        local textHeight = frame.text:GetStringHeight()
        frame:SetHeight(math.max(20, pixel:Snap(textHeight + 8, frame:GetEffectiveScale())))
        return frame
    end)
end
