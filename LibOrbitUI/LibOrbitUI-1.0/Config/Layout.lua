local _, addon = ...
local UI = addon.LibOrbitUI
UI.Layout = {}
UI.Layout.Methods = {}
local Layout = UI.Layout.Methods
local BASE_POOLS = {
    Checkbox = "checkboxPool",
    Slider = "sliderPool",
    Dropdown = "dropdownPool",
    Button = "buttonPool",
    Header = "headerPool",
    Spacer = "spacerPool",
    Label = "labelPool",
    Description = "descriptionPool",
    Tabs = "tabsPool",
}
local LAYOUT_PADDING = 10
local HALF_ROW_GAP = 6

function Layout:RegisterControlPool(typeName, poolName, cleanup)
    self[poolName] = self[poolName] or {}
    self.controlPools[typeName] = { name = poolName, cleanup = cleanup }
end

function Layout:ReleaseControl(control)
    if control.OrbitType == "EditBox" then
        control.EditBox:SetScript("OnEditFocusLost", nil)
        control.EditBox:SetScript("OnEnterPressed", nil)
        control.EditBox:SetScript("OnEscapePressed", nil)
        control.EditBox:SetScript("OnTextChanged", nil)
        control.EditBox:ClearFocus()
    end
    UI.Config.ReleaseValueControls(control)
    control:Hide()
    control:SetParent(nil)
    control:ClearAllPoints()
    if control.OrbitType == "Button" then
        control:SetScript("OnClick", nil)
    elseif control.OrbitType == "Checkbox" and control._cb then
        control._cb:SetScript("OnClick", nil)
        control._cb:SetScript("OnEnter", nil)
        control._cb:SetScript("OnLeave", nil)
    end
    local hover = control._tooltipHover
    if hover then
        hover._label, hover._tooltip = nil, nil
        hover:SetScript("OnEnter", nil)
        hover:SetScript("OnLeave", nil)
        hover:Hide()
    end
    local rule = self.controlPools[control.OrbitType]
    if rule then
        if rule.cleanup then
            rule.cleanup(control)
        end
        local poolName = control.OrbitType == "Checkbox" and control._compact and "compactCheckboxPool" or rule.name
        table.insert(self[poolName], control)
    elseif self.controlPoolFallback then
        local pool = self.controlPoolFallback(control)
        if pool then
            table.insert(pool, control)
        end
    end
end

function Layout:RecycleControls(controls)
    if not controls then
        return
    end
    for _, control in ipairs(controls) do
        self:ReleaseControl(control)
    end
end

function Layout:Reset(container)
    local controls = self.containerControls[container]
    if controls then
        self:RecycleControls(controls)
        self.containerControls[container] = nil
    end

    if container and container.OrbitPanel then
        container.OrbitPanel:Hide()
    end

    if container and container.Buttons then
        container.Buttons:Show()
    end
    if container and container.Settings then
        container.Settings:Show()
    end

    if container and container.Layout and container.Settings and container.Settings:IsShown() then
        container:Layout()
    end
end

function Layout:AddControl(container, frame)
    frame:SetParent(container)
    frame:ClearAllPoints()
    frame:Show()

    self.containerControls[container] = self.containerControls[container] or {}
    table.insert(self.containerControls[container], frame)
end

function Layout:Stack(container, startY, spacing)
    local y = startY or -LAYOUT_PADDING
    local gap = spacing or LAYOUT_PADDING

    local controls = self.containerControls[container]
    if not controls then
        return 0
    end

    local shown = {}
    for _, child in ipairs(controls) do
        if child:IsShown() and child:GetParent() == container then
            shown[#shown + 1] = child
        end
    end

    local i = 1
    while i <= #shown do
        local child = shown[i]
        local partner = shown[i + 1]
        if child.OrbitHalfWidth and partner and partner.OrbitHalfWidth then
            child:SetPoint("TOPLEFT", container, "TOPLEFT", LAYOUT_PADDING, y)
            child:SetPoint("TOPRIGHT", container, "TOP", -HALF_ROW_GAP / 2, y)
            partner:SetPoint("TOPLEFT", container, "TOP", HALF_ROW_GAP / 2, y)
            partner:SetPoint("TOPRIGHT", container, "TOPRIGHT", -LAYOUT_PADDING, y)
            y = y - math.max(child:GetHeight(), partner:GetHeight()) - gap
            i = i + 2
        else
            child:SetPoint("TOPLEFT", container, "TOPLEFT", LAYOUT_PADDING, y)
            child:SetPoint("TOPRIGHT", container, "TOPRIGHT", -LAYOUT_PADDING, y)
            y = y - child:GetHeight() - gap
            i = i + 1
        end
    end

    return math.abs(y)
end

function Layout:RegisterWidgetType(typeName, creator)
    local normalizedType = string.lower(typeName)
    self.creators[normalizedType] = creator
end

function Layout:HasWidgetType(typeName)
    local normalizedType = string.lower(typeName)
    return self.creators[normalizedType] ~= nil
end

function Layout:CreateWidget(container, def, getValue, callback)
    if not def or not def.type then
        return nil
    end

    local normalizedType = string.lower(def.type)
    local creator = self.creators[normalizedType]

    if not creator then
        error("LibOrbitUI Layout: Unknown widget type: " .. tostring(def.type))
    end

    return creator(container, def, getValue, callback)
end

function UI.Layout:Create(context, constants)
    local layout = Mixin({
        context = context,
        constants = constants,
        pixel = context.pixel,
        tooltip = context.tooltip,
        tooltipHide = context.tooltipHide,
        chrome = context.chrome,
        scrollBar = context.scrollBar or UI.ScrollBar:Create(context.pixel),
        creators = {},
        containerControls = {},
        controlPools = {},
        compactCheckboxPool = {},
    }, self.Methods)
    for typeName, poolName in pairs(BASE_POOLS) do
        layout:RegisterControlPool(typeName, poolName)
    end
    layout:RegisterControlPool("Slider", "sliderPool", function(control)
        if control.Slider and control.Slider.UnregisterCallback then
            control.Slider:UnregisterCallback("OnValueChanged", control)
        end
        control.OnOrbitChange = nil
        control._callbackRegistered = nil
        control._updateOnRelease = false
        if control.Slider and control.Slider.Slider then
            control.Slider.Slider:SetScript("OnMouseUp", nil)
        end
        if control._stepperTimer then
            control._stepperTimer:Cancel()
            control._stepperTimer = nil
        end
    end)
    layout:RegisterControlPool("Dropdown", "dropdownPool", function(control)
        if control.Dropdown then
            control.Dropdown:Hide()
        end
        control.dropCallback = nil
    end)
    layout:RegisterControlPool("Tabs", "tabsPool", function(control)
        for _, button in ipairs(control._tabButtons or {}) do
            button.tabCallback = nil
            button:SetScript("OnClick", nil)
        end
        local scroll = control._tabScroll
        if scroll then
            scroll.Animator:Hide()
            scroll.scrollTarget = nil
        end
    end)
    for _, typeName in ipairs({ "Header", "Label", "Description" }) do
        layout:RegisterControlPool(typeName, BASE_POOLS[typeName], function(control)
            control.text:SetText("")
        end)
    end
    layout.ORBIT_INPUT_BACKDROP = {
        bgFile = constants.Texture.ChatBackground,
        edgeFile = constants.Texture.TooltipBorder,
        tile = true,
        tileSize = 16,
        edgeSize = 16,
        insets = { left = 3, right = 3, top = 3, bottom = 3 },
    }
    layout.Advanced = {
        PADDING = 16,
        HEADER_HEIGHT = 40,
        TITLE_Y = -70,
        CONTENT_START_Y = -120,
        SCROLLBAR_WIDTH = 14,
        SCROLLBAR_RIGHT_SHIFT_PIXELS = 32,
        SECTION_SPACING = 2,
        MUTED = { r = 0.53, g = 0.53, b = 0.53 },
        TAB_EXTRA_WIDTH = 16,
    }

    layout.DialogChrome = {
        BG_INSET_LEFT = 6,
        BG_INSET_TOP = 21,
        BG_INSET_RIGHT = 2,
        BG_INSET_BOTTOM = 2,
        TITLE_OFFSET = 6,
        NINESLICE_LEVEL_OFFSET = 1,
        CONTENT_LEVEL_OFFSET = 10,
    }

    return layout
end
