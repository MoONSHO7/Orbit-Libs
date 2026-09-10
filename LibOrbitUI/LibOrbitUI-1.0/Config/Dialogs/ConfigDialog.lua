local _, addon = ...
local UI = addon.LibOrbitUI
local Config = UI.Config

local function ReleaseControls(dialog)
    dialog.context.tooltipHide()
    if dialog.layout.promptOptions then
        dialog.layout:HidePrompts()
    end
    dialog.renderer:Invalidate(dialog.OrbitPanel)
    dialog.layout:Reset(dialog.OrbitPanel.Header)
    dialog.layout:Reset(dialog.OrbitPanel.Content)
    dialog.layout:Reset(dialog.OrbitPanel.Footer)
    wipe(dialog.controls)
end

local function DialogConstants(spec)
    local constants = spec.constants or Config.Defaults
    if spec.width or spec.height then
        constants = CopyTable(constants)
        if spec.width then
            constants.Panel.Width = constants.Panel.Width + spec.width - constants.Panel.DialogWidth
            constants.Panel.DialogWidth = spec.width
        end
        if spec.height then
            constants.Panel.MaxHeight = spec.height - constants.Panel.TitlePadding
        end
    end
    return constants
end

function Config.CreateDialog(context, spec)
    assert(type(spec.title) == "string" and type(spec.closeLabel) == "string")
    assert(type(spec.tabs) == "table" and #spec.tabs > 0, "LibOrbitUI dialog needs tabs")
    local constants = DialogConstants(spec)
    local layoutContext = {
        owner = context.owner,
        pixel = context.pixel,
        tooltip = context.tooltip,
        tooltipHide = context.tooltipHide,
        chrome = context.chrome or UI.DialogChrome:Create(constants.DialogBackdrop),
    }
    local layout = UI.Layout:Create(layoutContext, constants)
    Config.Install(layout, {
        constants = constants,
        tooltip = context.tooltip,
        tooltipHide = context.tooltipHide,
        mergedLabel = spec.mergedLabel,
        isPreferredItem = spec.isPreferredItem,
        color = spec.color,
        media = spec.media,
    })
    layout:InitializeBaseWidgetTypes()
    if spec.prompts then
        Config.InstallPrompts(layout, {
            name = spec.name or context.name .. "Settings",
            labels = spec.prompts.labels,
            strata = spec.prompts.strata,
        })
    end
    if spec.registerWidgets then
        spec.registerWidgets(layout)
    end
    local dialog = UI.ConfigWindow:Create(layoutContext, {
        name = spec.name or context.name .. "Settings",
        title = spec.title,
        width = constants.Panel.DialogWidth,
        strata = constants.Strata.Dialog,
        onPositionChanged = spec.onPositionChanged,
    })
    dialog.context, dialog.spec, dialog.layout = context, spec, layout
    dialog.controls, dialog.tabs = {}, {}
    dialog.renderer = UI.ConfigPanel:Create(layoutContext, layout, constants, layout.scrollBar)
    dialog.OrbitPanel = dialog.renderer:CreateFrame(dialog)
    dialog.body, dialog.scroll = dialog.OrbitPanel.Content, dialog.OrbitPanel.ScrollFrame
    local labels, tabIDs = {}, {}
    for _, tab in ipairs(spec.tabs) do
        assert(type(tab.id) == "string" and not dialog.tabs[tab.id], "LibOrbitUI tab IDs must be unique")
        assert(type(tab.label) == "string" and not tabIDs[tab.label], "LibOrbitUI tab labels must be unique")
        dialog.tabs[tab.id] = { descriptor = tab }
        labels[#labels + 1] = tab.label
        tabIDs[tab.label] = tab.id
    end

    function dialog:Refresh()
        if not self:IsShown() then
            return
        end
        local descriptor = self.tabs[self.activeTab].descriptor
        local controls = type(descriptor.controls) == "function" and descriptor.controls() or descriptor.controls
        assert(type(controls) == "table", "LibOrbitUI tab needs controls")
        local schema = {
            {
                type = "tabs",
                tabs = labels,
                activeTab = descriptor.label,
                onTabSelected = function(label)
                    self:SelectTab(tabIDs[label])
                end,
            },
        }
        for _, control in ipairs(controls) do
            Config.ValidateControl(control, layout)
            schema[#schema + 1] = control
        end
        wipe(self.controls)
        self.renderer:Render(self.OrbitPanel, {
            controls = schema,
            cache = false,
            renderControl = function(container, control)
                local normalized = {}
                for key, value in pairs(control) do
                    normalized[key] = value
                end
                normalized.text = control.text or control.label
                local widget = self.renderer:RenderControl(container, normalized, function()
                    return Config.ResolveValue(spec, control)
                end, function(value)
                    Config.CommitValue(spec, control, value)
                end, function()
                    control.onClick(self, control)
                end)
                if control.type == "tabs" then
                    for index, button in ipairs(widget._tabButtons) do
                        self.tabs[spec.tabs[index].id].button = button
                    end
                else
                    self.controls[#self.controls + 1] = widget
                end
            end,
            renderFooter = function(footer)
                local buttons = {}
                local actions = spec.footerButtons
                if type(actions) == "function" then
                    actions = actions(self.activeTab)
                end
                for _, action in ipairs(actions or {}) do
                    buttons[#buttons + 1] = layout:CreateButton(footer, action.label, function()
                        action.onClick(self)
                    end)
                end
                buttons[#buttons + 1] = layout:CreateButton(footer, spec.closeLabel, function()
                    self:Hide()
                end)
                return self.renderer:LayoutFooter(footer, buttons)
            end,
        })
    end

    function dialog:SelectTab(id)
        assert(self.tabs[id], "Unknown LibOrbitUI settings tab")
        self.activeTab = id
        self.scroll:SetVerticalScroll(0)
        self:Refresh()
    end
    dialog:HookScript("OnShow", dialog.Refresh)
    dialog:HookScript("OnHide", ReleaseControls)
    dialog:SelectTab(spec.tabs[1].id)
    return dialog
end

table.freeze(Config)
