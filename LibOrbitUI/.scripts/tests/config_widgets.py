"""Exercise shipped widget constructors, layout, panel, tab, prompt, picker-session and window owners in Lua 5.1."""

import unittest

import control_states
from lupa.lua51 import LuaRuntime
from picker_menus import BOOT

RUNTIME = control_states.RUNTIME
EXTRA = r'''
local BaseFrame = Frame
function Frame(parent, kind, template)
    local frame = BaseFrame(parent, kind, template)
    function frame:SetAutoFocus(value) self.autoFocus = value end
    function frame:IsAutoFocus() return self.autoFocus == true end
    function frame:SetMultiLine(value) self.multiLine = value end
    function frame:IsMultiLine() return self.multiLine == true end
    function frame:HighlightText() self.highlighted = true end
    function frame:IsMouseEnabled() return self.mouse == true end
    function frame:SetToplevel(value) self.toplevel = value end
    function frame:IsToplevel() return self.toplevel == true end
    function frame:SetMovable(value) self.movable = value end
    function frame:IsMovable() return self.movable == true end
    function frame:StartMoving() self.moving = true end
    function frame:StopMovingOrSizing() self.moving = false end
    function frame:SetJustifyV(value) self.justifyV = value end
    function frame:SetNonSpaceWrap(value) self.nonSpaceWrap = value end
    function frame:SetSpacing(value) self.spacing = value end
    return frame
end
NineSliceUtil = {ApplyLayoutByName = noop}
function strtrim(text) return (text:gsub("^%s+", ""):gsub("%s+$", "")) end
'''
TABS = r'''
local BaseFrame = Frame
function Frame(parent, kind, template)
    local frame = BaseFrame(parent, kind, template)
    function frame:GetFont() return "font", 12, "" end
    function frame:GetHorizontalScroll() return self.horizontal or 0 end
    function frame:GetHorizontalScrollRange()
        return math.max(0, (self.child and self.child:GetWidth() or 0) - self:GetWidth())
    end
    function frame:SetHorizontalScroll(value) self.horizontal = value end
    return frame
end
NORMAL_FONT_COLOR = {GetRGB = function() return 1, 1, 1 end}
'''


class WidgetContracts(unittest.TestCase):
    def setUp(self):
        control_states.ControlStates.setUp(self)
        self.lua.execute(EXTRA)

    def load(self, *sources):
        for source in sources:
            self.lua.execute((RUNTIME / source).read_text(encoding="utf-8"), "Test", self.lua.globals().addon)

    def test_buttons_reuse_pooled_frames_under_the_new_parent_and_fit_their_text(self):
        self.lua.execute(r'''
            local first, second = Frame(), Frame()
            local button = layout:CreateButton(first, "A long button caption", Write)
            assert(button:GetParent() == first and button:GetWidth() == 21 * 7 + 30)
            layout:AddControl(first, button); layout:Reset(first)
            local reused = layout:CreateButton(second, "Short", Write)
            assert(reused == button and reused:GetParent() == second and reused:GetWidth() == 100)
            assert(layout:CreateButton(second, "Sized", Write, 77):GetWidth() == 77)
        ''')

    def test_plain_checkboxes_start_from_their_initial_value(self):
        self.lua.execute(r'''
            assert(not layout:CreateCheckbox(Frame(), "Off", nil, false, Write):GetChecked())
            assert(not layout:CreateCheckbox(Frame(), "Unset", nil, nil, Write):GetChecked())
            assert(layout:CreateCheckbox(Frame(), "On", nil, true, Write):GetChecked())
        ''')

    def test_edit_boxes_size_by_line_mode_and_focus_only_on_request(self):
        self.lua.execute(r'''
            local single = layout:CreateEditBox(Frame(), "Name", "x", Write)
            assert(single:GetHeight() == 30 and not single.EditBox:IsMultiLine())
            assert(not single.EditBox:IsAutoFocus() and single.InputContainer:IsMouseEnabled())
            single.InputContainer:Fire("OnMouseDown")
            assert(single.EditBox:HasFocus())
            local multi = layout:CreateEditBox(Frame(), "Notes", "", Write, nil, nil, true)
            assert(multi:GetHeight() == 100 and multi.EditBox:IsMultiLine() and not multi.EditBox:IsAutoFocus())
            assert(layout:CreateEditBox(Frame(), nil, "", Write, 50, 44):GetHeight() == 44)
        ''')

    def test_read_only_text_reverts_edits_to_the_frozen_value(self):
        self.lua.execute(r'''
            local box = layout:CreateEditBox(Frame(), nil, "frozen", nil, nil, 140, true,
                {readOnly = true, hideScrollBar = true})
            box.EditBox:SetText("typed")
            assert(box.EditBox:GetText() == "frozen")
            box:SetFrozenText("next")
            box.EditBox:SetText("x")
            assert(box.EditBox:GetText() == "next")
        ''')

    def test_format_input_hover_requires_preview_or_help_lines(self):
        self.lua.execute(r'''
            local plain = layout:CreateFormatInput(Frame(), "Format", "%d", Write, {})
            assert(plain:GetScript("OnEnter") == nil and plain.EditBox:GetScript("OnEnter") == nil)
            local helped = layout:CreateFormatInput(Frame(), "Format", "%d", Write, {{title = "Tokens"}})
            assert(helped:GetScript("OnEnter") and helped.EditBox:GetScript("OnEnter"))
        ''')

    def test_metadata_text_wraps(self):
        self.lua.execute(r'''
            local metadata = layout:CreateControlMetadata(Frame(), "A long inherited source explanation")
            assert(metadata.text:CanWordWrap())
        ''')

    def test_stack_positions_every_shown_control(self):
        self.lua.execute(r'''
            local box, frames = Frame(), {}
            for index, height in ipairs({20, 30, 40}) do
                local frame = Frame(box)
                frame:SetHeight(height)
                layout:AddControl(box, frame)
                frames[index] = frame
            end
            assert(layout:Stack(box, -10, 10) == 130)
            assert(frames[3].points.TOPLEFT[5] == -80 and frames[3].points.TOPRIGHT[5] == -80)
        ''')

    def test_released_disabled_controls_return_enabled_and_parent_faded(self):
        self.lua.execute(r'''
            local control = Render({type = "checkbox", label = "Locked", default = true, disabled = true})
            assert(not control._cb:IsEnabled() and control.Label.ignoreParentAlpha == true)
            layout:Reset(container)
            local reused = layout:CreateCheckbox(container, "Open", nil, true, Write)
            assert(reused == control and reused._cb:IsEnabled() and reused.alpha == 1)
            assert(reused.Label.ignoreParentAlpha == false)
        ''')

    def test_schema_guards_change_callbacks_and_rejects_empty_slider_ranges(self):
        self.lua.execute(r'''
            local Config = addon.LibOrbitUI.Config
            local calls, current = 0, true
            local bound = Config.BindDefinition({type = "checkbox", label = "X",
                onChange = function() calls = calls + 1 end}, function() return current end)
            bound.onChange(true)
            current = false
            bound.onChange(true)
            assert(calls == 1)
            assert(pcall(Config.ValidateControl, {type = "slider", label = "S", min = 0, max = 1, step = 1}))
            assert(not pcall(Config.ValidateControl, {type = "slider", label = "S", min = 1, max = 1, step = 1}))
        ''')

    def test_panel_scope_help_skips_passive_rows_and_empty_help_shows_nothing(self):
        self.lua.execute(r'''
            container.configScopeText = "This layout"
            local header = Render({type = "header", text = "Section"})
            assert(not (header._tooltipHover and header._tooltipHover:IsShown()))
            local row = Render({type = "checkbox", label = "Row", default = true})
            assert(row._tooltipHover and row._tooltipHover:IsShown())
            container.configScopeText = nil
            local locked = Render({type = "checkbox", label = "Locked", default = true, disabled = true})
            local shown = state.tooltips
            locked._disabledOverlay:Fire("OnEnter")
            assert(state.tooltips == shown)
        ''')

    def test_unchanged_presentation_refresh_does_not_relayout(self):
        self.lua.execute(r'''
            local relayouts = 0
            local control = Render({type = "test", label = "Value", default = 1})
            container.configRelayout = function() relayouts = relayouts + 1 end
            control.change(2)
            assert(state.writes == 1 and relayouts == 0)
        ''')

    def test_tab_bars_return_ordered_buttons_hint_only_with_text_and_rebuild_new_signatures(self):
        self.lua.execute(TABS + r'''
            context.tabScrollHint = function() return state.hint end
        ''')
        self.load("Config/LayoutTabs.lua")
        self.lua.execute(r'''
            Mixin(layout, addon.LibOrbitUI.Layout.Methods)
            local parent = Frame()
            local buttons = layout:CreateTabBar(parent, {"A very long first tab", "Another long second tab"},
                "Another long second tab", noop, true)
            assert(#buttons == 2 and buttons[1].Text:GetText() == "A very long first tab" and buttons[2].active)
            local hover = parent._tabScroll.RightOverflow.hover
            assert(hover:IsMouseEnabled())
            state.hint = ""
            hover:Fire("OnEnter")
            assert(Tooltip.owner ~= hover)
            state.hint = "Scroll tabs"
            hover:Fire("OnEnter")
            assert(Tooltip.owner == hover and Tooltip.title == "Scroll tabs")
            layout:RegisterTabsWidgetType()
            local tabs = layout:CreateWidget(container, {type = "tabs", tabs = {"One", "Two"}, activeTab = "One",
                onTabSelected = noop})
            layout:AddControl(container, tabs)
            layout:Reset(container)
            local reused = layout:CreateWidget(container, {type = "tabs", tabs = {"Three", "Four"}, activeTab = "Four",
                onTabSelected = noop})
            assert(reused == tabs and #reused._tabButtons == 2)
            assert(reused._tabButtons[1].Text:GetText() == "Three" and reused._tabButtons[2].active)
        ''')

    def test_prompts_validate_installation_and_show_one_transfer_box(self):
        self.load("Config/Dialogs/ConfigConfirmPopup.lua", "Config/Dialogs/ConfigInputPopup.lua")
        self.lua.execute(r'''
            local Config = addon.LibOrbitUI.Config
            layout.chrome = {ApplyBackdrop = noop}
            assert(not pcall(Config.InstallPrompts, {}, {name = "", labels = {}}))
            assert(not pcall(Config.InstallPrompts, {}, {labels = {}}))
            local labels = {cancel = "Cancel", import = "Import", close = "Close"}
            assert(Config.InstallPrompts(layout, {name = "OrbitTestPrompts", labels = labels}) == layout)
            local confirm = layout:ShowConfirm({text = "Sure?", acceptText = "Yes"})
            assert(confirm:IsShown() and confirm:IsToplevel())
            local export = layout:ShowTextTransfer({mode = "export", value = "data"})
            assert(export.transferExport:IsShown() and not export.transferImport:IsShown())
            assert(export.transferExport.EditBox:GetText() == "data")
            export:Hide()
            local import = layout:ShowTextTransfer({mode = "import", onAccept = function() return true end})
            assert(import.transferImport:IsShown() and not import.transferExport:IsShown())
            import:Hide()
            assert(not pcall(layout.ShowTextTransfer, layout, {mode = "copy"}))
        ''')


class PickerSessions(unittest.TestCase):
    def setUp(self):
        control_states.TextureSwatchStates.setUp(self)
        self.lua.execute((RUNTIME / "Config/Pickers/ConfigColorPicker.lua").read_text(encoding="utf-8"), "Test",
                         self.lua.globals().addon)
        self.lua.execute("Mixin(layout, addon.LibOrbitUI.Config)")

    def test_released_colour_controls_reject_callbacks_from_their_previous_binding(self):
        self.lua.execute(r'''
            local pick = {pins = {{color = {r = 0, g = 1, b = 0, a = 1}}}}
            local function Rebind(create, open)
                local first, second = 0, 0
                local control = create(function() first = first + 1 end)
                open(control)
                local stale = state.opens[#state.opens].options.callback
                layout:AddControl(container, control)
                layout:Reset(container)
                local reused = create(function() second = second + 1 end)
                assert(reused == control)
                open(reused)
                local current = state.opens[#state.opens].options.callback
                stale(pick, false)
                assert(first == 0 and second == 0, "a released binding wrote through the reused control")
                current(pick, false)
                assert(second == 1)
            end
            Rebind(function(callback)
                return layout:CreateColorPicker(container, "Tint", {r = 1, g = 0, b = 0, a = 1}, callback)
            end, function(control) control.Swatch:Fire("OnClick") end)
            Rebind(function(callback)
                return layout:CreateColorCurvePicker(container, "Curve", Curve(1, 1), callback)
            end, function(control) control:Fire("OnClick") end)
        ''')

    def test_disabled_swatches_stay_hidden_and_empty_curve_results_are_ignored(self):
        self.lua.execute(r'''
            local definition = TextureDefinition()
            definition.valueColors, definition.valueCheckbox = nil, nil
            definition.valueColor = Swatch("Tint", Curve(1, 1))
            definition.valueColor.enabled = false
            local control = Render(definition)
            assert(not (control.ValueColorSwatch and control.ValueColorSwatch:IsShown()))
            layout:Reset(container)
            definition.valueColor.enabled = function() return true end
            control = Render(definition)
            assert(control.ValueColorSwatch:IsShown())
            control.ValueColorSwatch:Fire("OnClick", "LeftButton")
            state.opens[#state.opens].options.callback({pins = {}}, false)
            assert(state.writes == 0)
        ''')

    def test_curve_preview_accepts_coincident_pins(self):
        self.lua.execute(r'''
            local flat = {pins = {}}
            for index = 1, 8 do flat.pins[index] = {position = 0.5, color = {r = index / 8, g = 0, b = 0, a = 1}} end
            local control = Render({type = "colorcurve", label = "Flat", default = flat})
            assert(control.GradientTexture.gradient[1] == "HORIZONTAL")
        ''')


class InstalledConfig(unittest.TestCase):
    SOURCES = (
        "Core/Callbacks.lua", "Core/EscapeClose.lua", "Config/Config.lua", "Config/ConfigSchema.lua",
        "Config/Layout.lua", "Config/LayoutControls.lua", "Config/Widgets/ScrollBar.lua",
        "Config/ConfigPickerWidgets.lua", "Config/Widgets/ConfigValueSwatch.lua", "Config/Pickers/MediaMenu.lua",
        "Config/Pickers/ConfigPickerControl.lua", "Config/ConfigColorProvider.lua", "Config/Dialogs/ConfigWindow.lua",
    )

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BOOT + EXTRA)
        self.lua.execute("frozen = {}; table.freeze = function(value) frozen[value] = true; return value end")
        for source in self.SOURCES:
            self.lua.execute((RUNTIME / source).read_text(encoding="utf-8"), "Test", self.lua.globals().addon)
        self.lua.execute("UI = addon.LibOrbitUI; Defaults = UI.Config.Defaults")

    def test_defaults_are_frozen_and_install_needs_a_private_tooltip(self):
        self.lua.execute(r'''
            for _, section in ipairs({"UI", "Panel", "Footer", "Widget", "Texture", "Strata", "DialogBackdrop"}) do
                assert(frozen[Defaults[section]], section)
            end
            assert(frozen[Defaults])
            local rejected = UI.Layout:Create({pixel = Pixel, scrollBar = {}}, Defaults)
            assert(not pcall(UI.Config.Install, rejected, {tooltip = Tooltip}))
            assert(rejected.configOptions == nil)
            local target = UI.Layout:Create({pixel = Pixel, scrollBar = {}}, Defaults)
            assert(UI.Config.Install(target, {tooltip = Tooltip, tooltipHide = noop, color = {}}) == target)
            assert(target.configOptions.constants == Defaults and target.CreateButton == UI.Config.CreateButton)
        ''')

    def test_default_colour_provider_requires_a_compatible_optional_picker(self):
        self.lua.execute(r'''
            local context = {tooltip = Tooltip, tooltipHide = noop}
            LibStub = nil
            local provider = UI.Config.CreateColorProvider(context)
            assert(not provider.isAvailable() and provider.checkerboard == nil and provider.open({}, {}) == false)
            local libraries = {}
            -- Mirrors LibStub:GetLibrary: a missing library errors unless the lookup is silent.
            LibStub = setmetatable({}, {__call = function(_, major, silent)
                if not libraries[major] and not silent then
                    error(("Cannot find a library instance of %q."):format(tostring(major)), 2)
                end
                return libraries[major]
            end})
            provider = UI.Config.CreateColorProvider(context)
            assert(not provider.isAvailable())
            libraries["LibOrbitColorPicker-1.0"] = {}
            assert(not provider.isAvailable())
            local picker = {sessionId = 7}
            function picker:GetCheckerboardTexture() return "checker" end
            function picker:Open(request) self.request = request; return self.sessionId end
            function picker:IsOpen() return true end
            function picker:CloseFrame() self.closed = true end
            libraries["LibOrbitColorPicker-1.0"] = picker
            provider = UI.Config.CreateColorProvider(context)
            assert(provider.isAvailable() and provider.checkerboard == "checker")
            local owner = {}
            assert(provider.open(owner, {initialData = 1}) == true and picker.request.tooltip == Tooltip)
            provider.close(owner)
            assert(picker.closed and picker.wasCancelled)
        ''')

    def test_windows_claim_unused_names_move_and_hide_in_combat_unless_exempt(self):
        self.lua.execute(r'''
            local context = {owner = {}, chrome = {ApplyChrome = function() return {} end}}
            OrbitTakenWindow = {}
            local taken = {name = "OrbitTakenWindow", title = "T"}
            assert(not pcall(UI.ConfigWindow.Create, UI.ConfigWindow, context, taken))
            local window = UI.ConfigWindow:Create(context, {name = "OrbitWindowA", title = "Settings"})
            assert(window:IsMovable() and window.events.PLAYER_REGEN_DISABLED)
            window:Show()
            window:Fire("OnEvent", "PLAYER_REGEN_DISABLED")
            assert(not window:IsShown())
            local kept = UI.ConfigWindow:Create(context,
                {name = "OrbitWindowB", title = "Settings", hideInCombat = false})
            assert(not kept.events.PLAYER_REGEN_DISABLED and kept:GetScript("OnEvent") == nil)
        ''')


if __name__ == "__main__":
    unittest.main()
