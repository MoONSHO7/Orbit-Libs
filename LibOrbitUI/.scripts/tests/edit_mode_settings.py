"""Run settings exclusivity through shipped Lua 5.1 modules with mocked WoW boundaries."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
BOOT = r'''
mock = { combat = false, hooks = 0, clears = 0, errors = {}, frames = {}, timers = {}, writes = 0, categories = {} }
UIParent = {}
SlashCmdList = {}
C_InstanceEncounter = { IsEncounterInProgress = function() return false end }
table.freeze = function(value) return value end
function Mixin(target, mixin)
    for key, value in pairs(mixin) do target[key] = value end
    return target
end
function wipe(value) for key in pairs(value) do value[key] = nil end end
function InCombatLockdown() return mock.combat end
function geterrorhandler() return function(err) table.insert(mock.errors, err) end end
function securecallfunction(callback, ...) return callback(...) end
function hooksecurefunc(target, method, callback)
    mock.hooks = mock.hooks + 1
    local original = target[method]
    target[method] = function(...)
        original(...)
        callback(...)
    end
end
EventRegistry = { events = {} }
function EventRegistry:RegisterCallback(event, callback, owner)
    self.events[event] = self.events[event] or {}
    table.insert(self.events[event], { callback, owner })
end
function EventRegistry:TriggerEvent(event)
    local records = {}
    for _, record in ipairs(self.events[event] or {}) do table.insert(records, record) end
    for _, record in ipairs(records) do record[1](record[2]) end
end
function EventRegistry:UnregisterCallback(event, owner)
    local records = self.events[event] or {}
    for index = #records, 1, -1 do
        if records[index][2] == owner then table.remove(records, index) end
    end
end
function NewWindow()
    local frame = { shown = false, scripts = {}, hooks = {}, hides = 0, events = {} }
    table.insert(mock.frames, frame)
    function frame:IsShown() return self.shown end
    function frame:SetScript(event, callback) self.scripts[event] = callback end
    function frame:HookScript(event, callback)
        self.hooks[event] = self.hooks[event] or {}
        table.insert(self.hooks[event], callback)
    end
    function frame:Fire(event)
        if self.scripts[event] then self.scripts[event](self) end
        for _, callback in ipairs(self.hooks[event] or {}) do callback(self) end
    end
    function frame:Show()
        if not self.shown then self.shown = true self:Fire("OnShow") end
    end
    function frame:Hide()
        if self.shown then
            self.shown = false
            self.hides = self.hides + 1
            self:Fire("OnHide")
        end
    end
    function frame:SetVerticalScroll() end
    function frame:SetSize() end
    function frame:SetText(value) self.text = value end
    function frame:SetShown(value) if value then self:Show() else self:Hide() end end
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:UnregisterEvent(event) self.events[event] = nil end
    function frame:UnregisterAllEvents() wipe(self.events) end
    function frame:SetParent(parent) self.parent = parent end
    function frame:ClearAllPoints() end
    function frame:ClearFocus()
        self.focused = false
        if self.scripts.OnEditFocusLost then self.scripts.OnEditFocusLost(self) end
    end
    return frame
end
function CreateFrame() return NewWindow() end
function FireEvent(event, ...)
    for _, frame in ipairs(mock.frames) do
        if frame.events[event] and frame.scripts.OnEvent then frame.scripts.OnEvent(frame, event, ...) end
    end
end
function Tick()
    for _, frame in ipairs(mock.frames) do
        if frame:IsShown() and frame.scripts.OnUpdate then frame.scripts.OnUpdate(frame, 0.2) end
    end
end
C_Timer = { NewTimer = function(_, callback)
    local timer = { callback = callback }
    function timer:Cancel() self.cancelled = true end
    table.insert(mock.timers, timer)
    return timer
end }
C_Timer.NewTicker = C_Timer.NewTimer
Settings = {
    RegisterCanvasLayoutCategory = function(panel, title)
        local category = { panel = panel, title = title }
        table.insert(mock.categories, category)
        return category
    end,
    RegisterAddOnCategory = function() end,
}
EditModeManagerFrame = { active = false, shown = false }
function EditModeManagerFrame:IsShown() return self.shown end
function EditModeManagerFrame:IsEditModeActive() return self.active end
function EditModeManagerFrame:IsEditModeLocked() return self.locked end
function EditModeManagerFrame:ClearSelectedSystem()
    assert(not mock.combat, "Native selection was touched in combat")
    mock.clears = mock.clears + 1
    self.selected = nil
    EditModeSystemSettingsDialog:Hide()
end
function MakeNative() EditModeSystemSettingsDialog = NewWindow() end
MakeNative()
function SelectNative(id)
    if EditModeManagerFrame.selected ~= id then
        EditModeManagerFrame.selected = id
        EditModeSystemSettingsDialog:Show()
    end
end
function Enter()
    EditModeManagerFrame.active = true
    EditModeManagerFrame.shown = true
    EventRegistry:TriggerEvent("EditMode.Enter")
end
function Exit()
    EditModeManagerFrame.active = false
    EditModeManagerFrame.shown = false
    EventRegistry:TriggerEvent("EditMode.Exit")
end
function InstallPresentation(UI)
    local function Noop() end
    UI.Layout = { Create = function()
        local layout = { InitializeBaseWidgetTypes = Noop, resets = 0, HasWidgetType = function() return true end }
        function layout:Reset() self.resets = self.resets + 1 end
        function layout:CreateButton(_, _, callback) return { click = callback } end
        return layout
    end }
    UI.DialogChrome = { Create = function() return {} end }
    UI.Config = {
        Defaults = { Panel = { DialogWidth = 350 }, Strata = {} },
        Install = Noop, ValidateControl = Noop,
    }
    UI.ConfigWindow = { Create = function() return NewWindow() end }
    UI.ConfigPanel = { Create = function()
        local renderer = {}
        function renderer:CreateFrame()
            return { Content = {}, Header = {}, Footer = {}, ScrollFrame = NewWindow() }
        end
        function renderer:Render(panel, options)
            self.renders = (self.renders or 0) + 1
            self.widgets = {}
            for _, control in ipairs(options.controls) do options.renderControl({}, control) end
            options.renderFooter(panel.Footer)
        end
        function renderer:RenderControl(_, definition, getValue, change, click)
            local widget = { definition = definition, get = getValue, change = change, click = click, _tabButtons = {} }
            for index in ipairs(definition.tabs or {}) do widget._tabButtons[index] = {} end
            table.insert(self.widgets, widget)
            return widget
        end
        function renderer:LayoutFooter(_, buttons) self.buttons = buttons end
        function renderer:Invalidate() self.invalidates = (self.invalidates or 0) + 1 end
        function renderer:Release(panel) self:Invalidate(panel) end
        return renderer
    end }
end
function NewDialog(UI)
    return UI.Config.CreateDialog({ name = "Test", tooltipHide = function() end }, {
        title = "Settings", closeLabel = "Close", tabs = { { id = "main", label = "Main", controls = {} } },
    })
end
'''


class EditModeSettings(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BOOT)
        for name in ("first", "second"):
            self.lua.execute(f"{name} = {{}}")
            addon = self.lua.globals()[name]
            for relative in ("Core/Bootstrap.lua", "Core/Callbacks.lua", "Core/Runtime.lua", "Core/Context.lua",
                             "Movement/EditSession.lua", "Config/Dialogs/SettingsCoordinator.lua",
                             "Config/Dialogs/DialogLifecycle.lua"):
                self.load(relative, addon)
            self.lua.globals().InstallPresentation(addon.LibOrbitUI)
            self.load("Config/ConfigSchema.lua", addon)
            self.load("Config/Dialogs/ConfigDialog.lua", addon)
        self.lua.execute("a = NewDialog(first.LibOrbitUI); b = NewDialog(second.LibOrbitUI)")

    def load(self, relative, addon):
        self.lua.execute("return function(...)\n" + (RUNTIME / relative).read_text(encoding="utf-8") + "\nend")(
            "Consumer", addon
        )

    def tearDown(self):
        self.lua.execute("assert(#mock.errors == 0)")

    def test_private_embeddings_share_only_the_coordinator(self):
        self.lua.execute('''
            assert(first.LibOrbitUI ~= second.LibOrbitUI)
            assert(first.LibOrbitUI.SettingsCoordinator == second.LibOrbitUI.SettingsCoordinator)
            assert(mock.hooks == 1)
            Enter(); a:Show(); b:Show()
            assert(not a:IsShown() and b:IsShown())
            assert(a.renderer.invalidates == 1)
            a:Show()
            assert(a:IsShown() and not b:IsShown())
        ''')

    def test_native_handoffs_and_reselecting_the_same_native_frame(self):
        self.lua.execute('''
            Enter(); SelectNative("player"); a:Show()
            assert(not EditModeSystemSettingsDialog:IsShown() and mock.clears == 1)
            SelectNative("player")
            assert(EditModeSystemSettingsDialog:IsShown() and not a:IsShown())
            b:Show(); SelectNative("target")
            assert(EditModeSystemSettingsDialog:IsShown() and not b:IsShown())
        ''')

    def test_outside_edit_mode_and_unregistered_child_dialogs(self):
        self.lua.execute('''
            a:Show(); b:Show()
            assert(a:IsShown() and b:IsShown())
            Enter()
            assert(not a:IsShown() and b:IsShown())
            local prompt = NewWindow(); prompt:Show(); a:Show()
            assert(prompt:IsShown() and a:IsShown() and not b:IsShown())
        ''')

    def test_registration_is_idempotent_and_existing_windows_are_reconciled(self):
        self.lua.execute('''
            local coordinator = first.LibOrbitUI.SettingsCoordinator
            local hooks = #a.hooks.OnShow
            coordinator:Register(a); coordinator:Register(a)
            assert(#a.hooks.OnShow == hooks)
            Enter(); a:Show()
            local custom = NewWindow(); custom:Show(); coordinator:Register(custom)
            assert(custom:IsShown() and not a:IsShown())
            custom:Hide(); b:Show()
            assert(coordinator.current == b)
        ''')

    def test_newest_reentrant_open_wins(self):
        self.lua.execute('''
            local c = NewDialog(second.LibOrbitUI)
            a:HookScript("OnHide", function() c:Show() end)
            Enter(); a:Show(); b:Show()
            assert(c:IsShown() and not a:IsShown() and not b:IsShown())
            assert(first.LibOrbitUI.SettingsCoordinator.current == c)
        ''')

    def test_combat_never_clears_native_selection(self):
        self.lua.execute('''
            Enter(); SelectNative("player"); mock.combat = true; a:Show()
            assert(mock.clears == 0)
            b:Show()
            assert(mock.clears == 0)
            assert(not a:IsShown() and not b:IsShown())
            mock.combat = false; Enter()
            assert(EditModeSystemSettingsDialog:IsShown() and not a:IsShown() and not b:IsShown())
        ''')

    def test_hidden_session_retains_exclusivity_without_another_enter_event(self):
        self.lua.execute('''
            a = NewWindow(); b = NewWindow()
            first.LibOrbitUI.SettingsCoordinator:Register(a)
            second.LibOrbitUI.SettingsCoordinator:Register(b)
            Enter(); a:Show(); EditModeManagerFrame.shown = false; b:Show()
            assert(not a:IsShown() and b:IsShown())
            EditModeManagerFrame.shown = true
            assert(not a:IsShown() and b:IsShown())
            a:Show()
            assert(a:IsShown() and not b:IsShown())
        ''')

    def test_late_native_dialog_gets_one_observer(self):
        self.lua.execute('''
            EditModeSystemSettingsDialog = nil
            LibOrbitUISettingsCoordinator = nil
            late = {}
        ''')
        for relative in ("Core/Bootstrap.lua", "Core/Callbacks.lua", "Config/Dialogs/SettingsCoordinator.lua"):
            self.load(relative, self.lua.globals().late)
        self.lua.execute('''
            local custom = NewWindow()
            late.LibOrbitUI.SettingsCoordinator:Register(custom)
            MakeNative(); Enter(); custom:Show(); SelectNative("player")
            assert(not custom:IsShown() and EditModeSystemSettingsDialog:IsShown())
            assert(late.LibOrbitUI.SettingsCoordinator.native == EditModeSystemSettingsDialog)
        ''')

    def test_host_native_replacement_preserves_selection(self):
        self.lua.execute('''
            Enter(); SelectNative("hosted")
            EditModeSystemSettingsDialog:Hide()
            a:Show()
            assert(EditModeManagerFrame.selected == "hosted" and mock.clears == 0)
            SelectNative("other")
            assert(not a:IsShown() and EditModeSystemSettingsDialog:IsShown())
        ''')

    def test_indexed_addon_settings_use_exclusive_shared_dialogs(self):
        self.lua.execute("first.LibOrbitUI.AddonMixin = {}")
        self.load("Addon/AddonSettings.lua", self.lua.globals().first)
        self.lua.execute('''
            local app = Mixin({
                ready = true, dialogs = {}, context = { name = "App", tooltipHide = function() end },
                options = { name = "App", title = "Settings", labels = { close = "Close", enabled = "Enabled" },
                    isPreferredItem = function(name) return name == "Orbit UI" end,
                    tabs = function() return { { id = "main", label = "Main", controls = {} } } end },
            }, first.LibOrbitUI.AddonMixin)
            function app:IsEnabled() return true end
            function app:IsEditMode() return EditModeManagerFrame:IsEditModeActive() end
            Enter(); app:ShowSettings(1); app:ShowSettings(2)
            assert(#app.dialogs[2].controls == 1)
            assert(app.dialogs[2].controls[1].definition.label == "Enabled")
            assert(not app.dialogs[1]:IsShown() and app.dialogs[2]:IsShown())
            assert(app.dialogs[2].spec.isPreferredItem("Orbit UI"))
            assert(not app.dialogs[2].spec.isPreferredItem("Expressway"))
            app:ShowSettings(1)
            assert(app.dialogs[1]:IsShown() and not app.dialogs[2]:IsShown())
        ''')

    def test_hosted_addon_settings_omit_the_enabled_control(self):
        self.lua.execute("first.LibOrbitUI.AddonMixin = {}")
        self.load("Addon/AddonSettings.lua", self.lua.globals().first)
        self.lua.execute('''
            local app = Mixin({
                ready = true, dialogs = {}, context = { name = "App", tooltipHide = function() end },
                options = { name = "App", title = "Settings", bridge = {},
                    labels = { close = "Close", enabled = "Enabled" },
                    tabs = function()
                        return { { id = "main", label = "Main", controls = {
                            { type = "checkbox", label = "Product" },
                        } } }
                    end,
                },
            }, first.LibOrbitUI.AddonMixin)
            function app:IsEditMode() return false end
            app:ShowSettings(1)
            assert(#app.dialogs[1].controls == 1)
            assert(app.dialogs[1].controls[1].definition.label == "Product")
        ''')

    def test_always_enabled_addon_does_not_consult_an_enable_setting_or_render_controls(self):
        self.load("Addon/Addon.lua", self.lua.globals().first)
        self.load("Addon/AddonSettings.lua", self.lua.globals().first)
        self.lua.execute('''
            local reads, writes = 0, 0
            local app = Mixin({
                ready = true, dialogs = {}, context = { name = "App", tooltipHide = function() end },
                controller = {
                    GetSetting = function() reads = reads + 1 end,
                    SetSetting = function() writes = writes + 1 end,
                },
                options = { name = "App", title = "Compass", alwaysEnabled = true,
                    labels = { close = "Close" },
                    tabs = function()
                        return { { id = "main", label = "Main", controls = {
                            { type = "checkbox", label = "Product" },
                        } } }
                    end,
                },
            }, first.LibOrbitUI.AddonMixin)
            function app:IsEditMode() return false end
            assert(app:IsEnabled())
            app:SetEnabled(false)
            assert(reads == 0 and writes == 0)
            app:ShowSettings(1)
            app:ShowSettings(2)
            assert(#app.dialogs[1].controls == 1 and #app.dialogs[2].controls == 1)
            assert(app.dialogs[1].controls[1].definition.label == "Product")
            assert(app.dialogs[2].controls[1].definition.label == "Product")
        ''')

    def test_hosted_addon_boot_omits_the_blizzard_category(self):
        self.load("Addon/Addon.lua", self.lua.globals().first)
        self.lua.execute('''
            local function Options(name, bridge)
                return {
                    addonName = name,
                    name = name,
                    title = name,
                    bridge = bridge,
                    controller = {},
                    context = { pixel = { Point = function() end } },
                    store = { Initialize = function(_, data) return data end },
                    readStore = function() return {} end,
                    writeStore = function() end,
                    labels = { settings = "Settings" },
                    slashKey = string.upper(name),
                    slash = { "/" .. string.lower(name) },
                }
            end
            first.LibOrbitUI.Addon:Create(Options("Hosted", {}))
            first.LibOrbitUI.Addon:Create(Options("Standalone", nil))
            FireEvent("ADDON_LOADED", "Hosted")
            assert(#mock.categories == 0)
            FireEvent("ADDON_LOADED", "Standalone")
            assert(#mock.categories == 1 and mock.categories[1].title == "Standalone")
        ''')

    def test_edit_open_closes_on_exit_but_direct_open_survives(self):
        self.lua.execute('''
            Enter(); a:Show(); Exit()
            assert(not a:IsShown() and a.renderer.invalidates == 1)
            a:Show(); Enter(); Exit()
            assert(a:IsShown())
            assert(a.renderer.invalidates == 1)
        ''')

    def test_hidden_session_closes_bound_dialog_without_reopening_it(self):
        self.lua.execute('''
            Enter(); a:Show(); EditModeManagerFrame.shown = false; Tick()
            assert(not a:IsShown())
            EditModeManagerFrame.shown = true; Tick()
            assert(not a:IsShown())
            a:Show(); assert(a:IsShown())
        ''')

    def test_explicit_lifecycle_policies(self):
        self.lua.execute('''
            local required = NewWindow()
            first.LibOrbitUI.DialogLifecycle:Create({}, required, { editModePolicy = "required" })
            required:Show(); assert(not required:IsShown())
            Enter(); required:Show(); Exit(); assert(not required:IsShown())
            a.lifecycle.policy = "manual"
            Enter(); a:Show(); Exit(); assert(a:IsShown())
            mock.combat = true; FireEvent("PLAYER_REGEN_DISABLED")
            assert(not a:IsShown())
            a:Show(); assert(not a:IsShown())
        ''')

    def test_context_destroy_closes_dialogs_and_removes_lifecycle_callbacks(self):
        self.lua.execute('''
            local pixel = { Destroy = function() error("Borrowed pixel must survive") end }
            local context = first.LibOrbitUI.CreateContext({ owner = {}, name = "Owned", pixel = pixel,
                tooltip = {}, tooltipHide = function() end })
            local dialog = first.LibOrbitUI.Config.CreateDialog(context, {
                title = "Owned", closeLabel = "Close", tabs = { { id = "main", label = "Main", controls = {} } },
            })
            Enter(); dialog:Show()
            local lifecycle = dialog.lifecycle
            context:Destroy(); context:Destroy()
            assert(not dialog:IsShown() and lifecycle.destroyed and not next(context.dialogLifecycles))
            for _, records in pairs(EventRegistry.events) do
                for _, record in ipairs(records) do
                    assert(record[2] ~= lifecycle and record[2] ~= lifecycle.editSession)
                end
            end
            assert(not next(lifecycle.events.events) and not next(lifecycle.editSession.poll.events))
            dialog:Show(); assert(not dialog:IsShown())
            assert(dialog.renderer.invalidates == 1)
        ''')

    def test_same_shell_cannot_reopen_during_close_cleanup(self):
        self.lua.execute('''
            local dialog = NewWindow()
            local closes = 0
            local lifecycle = first.LibOrbitUI.DialogLifecycle:Create({}, dialog, {
                onClose = function(window) closes = closes + 1; window:Show() end,
            })
            dialog:Show(); dialog:Hide()
            assert(closes == 1 and not dialog:IsShown() and not lifecycle:IsOpen())
            dialog:Show(); assert(dialog:IsShown() and lifecycle:IsOpen())
            lifecycle:Destroy(); lifecycle:Destroy()
            assert(closes == 2 and not dialog:IsShown())
        ''')

    def test_refresh_close_and_reopen_invalidate_writers_actions_and_child_controls(self):
        self.lua.execute('''
            local function Write() mock.writes = mock.writes + 1 end
            local original = { type = "dropdown", label = "Value", key = "value", default = 0,
                valueColor = { callback = Write }, options = function() return { { action = Write } } end }
            local dialog = first.LibOrbitUI.Config.CreateDialog({ name = "Leases", tooltipHide = function() end }, {
                title = "Leases", closeLabel = "Close", set = Write,
                tabs = { { id = "main", label = "Main", controls = { original,
                    { type = "button", label = "Action", onClick = Write } } } },
                footerButtons = { { label = "Footer", onClick = Write } },
            })
            dialog:Show()
            local old = dialog.renderer.widgets[2]
            local action = dialog.renderer.widgets[3].click
            local footer = dialog.renderer.buttons[1].click
            local close = dialog.renderer.buttons[2].click
            local tab = dialog.renderer.widgets[1].definition.onTabSelected
            old.change(1); old.definition.valueColor.callback(); old.definition.options()[1].action()
            assert(mock.writes == 3)
            dialog:Refresh()
            old.change(2); action(); footer(); close(); tab("Main")
            old.definition.valueColor.callback(); old.definition.options()[1].action()
            assert(mock.writes == 3 and dialog:IsShown())
            local current = dialog.renderer.widgets[2]
            current.change(3); assert(mock.writes == 4)
            dialog:Hide(); dialog:Show(); current.change(4)
            assert(mock.writes == 4)
            assert(original.valueColor.callback == Write, "Caller schema must not be mutated")
        ''')

    def test_real_panel_release_invalidates_sizing_and_releases_cached_tabs(self):
        self.load("Config/Dialogs/ConfigPanel.lua", self.lua.globals().first)
        self.lua.execute('''
            local layout = { promptOptions = {}, released = {} }
            function layout:HidePrompts() self.promptsHidden = true end
            function layout:Reset(container) self.released[container] = true end
            local renderer = first.LibOrbitUI.ConfigPanel:Create({ tooltipHide = function() end }, layout, {}, {})
            local panel = NewWindow()
            panel.Header = {}; panel.Content = { OrbitRendered = true }; panel.Footer = {}
            panel.Tabs = { one = { OrbitRendered = true }, two = { OrbitRendered = true } }
            panel.configSizingGeneration = 4; panel:Show(); renderer:Release(panel)
            assert(panel.configSizingGeneration == 5 and not panel:IsShown())
            assert(not panel.Content.OrbitRendered and not panel.Tabs.one.OrbitRendered)
            assert(layout.released[panel.Header] and layout.released[panel.Content] and layout.released[panel.Footer])
            assert(layout.released[panel.Tabs.one] and layout.released[panel.Tabs.two] and layout.promptsHidden)
        ''')

    def test_text_release_clears_focus_without_committing(self):
        self.load("Config/Layout.lua", self.lua.globals().first)
        self.lua.execute('''
            first.LibOrbitUI.Config.ReleaseValueControls = function() end
            local control = NewWindow(); control.OrbitType = "EditBox"; control.EditBox = NewWindow()
            control.EditBox.focused = true
            control.EditBox:SetScript("OnEditFocusLost", function() error("Discarded editor committed") end)
            first.LibOrbitUI.Layout.Methods.ReleaseControl({ controlPools = {} }, control)
            assert(not control.EditBox.focused and not control.EditBox.scripts.OnEditFocusLost)
        ''')


if __name__ == "__main__":
    unittest.main()
