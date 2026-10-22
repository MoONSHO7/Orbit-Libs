"""Verify addon windows consume Escape locally without joining Blizzard's shared close scan."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"

HARNESS = r'''
addon = {}
table.freeze = function(value) return value end
mock = {combat = false, timers = {}, inputs = {}}
UISpecialFrames = {}
function InCombatLockdown() return mock.combat end
function geterrorhandler() return function(err) error(err) end end
function hooksecurefunc(owner, method, callback)
    local original = owner[method]
    owner[method] = function(...)
        original(...)
        callback(...)
    end
end
C_Timer = {}
function C_Timer.After(_, callback) table.insert(mock.timers, callback) end
function RunTimers()
    local timers = mock.timers
    mock.timers = {}
    for _, callback in ipairs(timers) do callback() end
end
function NewFrame(parent)
    local frame = {shown = false, parent = parent, scripts = {}, hooks = {}, events = {}, keyboardCalls = 0,
        propagate = false, strata = "DIALOG", level = 10}
    function frame:EnableKeyboard(value)
        self.keyboard = value
        self.keyboardCalls = self.keyboardCalls + 1
    end
    function frame:SetPropagateKeyboardInput(value)
        assert(not mock.combat, "propagation write in combat")
        self.propagate = value
    end
    function frame:SetFrameStrata(value) self.strata = value end
    function frame:GetFrameStrata() return self.strata end
    function frame:SetFrameLevel(value) self.level = value end
    function frame:GetFrameLevel() return self.level end
    function frame:Raise() self.level = self.level + 10 end
    function frame:Lower() self.level = self.level - 10 end
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:SetScript(event, callback) self.scripts[event] = callback end
    function frame:HookScript(event, callback)
        self.hooks[event] = self.hooks[event] or {}
        table.insert(self.hooks[event], callback)
    end
    function frame:Fire(event, ...)
        if self.scripts[event] then self.scripts[event](self, ...) end
        for _, callback in ipairs(self.hooks[event] or {}) do callback(self, ...) end
    end
    function frame:Show()
        if not self.shown then
            self.shown = true
            self:Fire("OnShow")
        end
    end
    function frame:Hide()
        if self.shown then
            self.shown = false
            self:Fire("OnHide")
        end
    end
    function frame:IsShown() return self.shown end
    function frame:IsVisible() return self.shown and (not self.parent or self.parent:IsVisible()) end
    return frame
end
UIParent = NewFrame()
UIParent:Show()
function CreateFrame(kind, name, parent, template)
    assert(kind == "Frame" and name == nil and parent == UIParent)
    assert(template == "InsecureKeyboardInputPropagatorTemplate")
    local frame = NewFrame(parent)
    frame.propagate = true
    table.insert(mock.inputs, frame)
    return frame
end
function Combat(value, eventFirst)
    local event = value and "PLAYER_REGEN_DISABLED" or "PLAYER_REGEN_ENABLED"
    if not eventFirst then mock.combat = value end
    for _, frame in ipairs(mock.inputs) do
        if frame.events[event] then frame:Fire("OnEvent", event) end
    end
    mock.combat = value
end
function Key(input, key)
    if not input:IsVisible() or not input.keyboard then return true end
    input:Fire("OnKeyDown", key)
    return input.propagate
end
'''


class EscapeClose(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute(HARNESS)
        for source in ("Core/Bootstrap.lua", "Core/Callbacks.lua", "Core/EscapeClose.lua"):
            self.lua.execute("return function(...)\n" + (RUNTIME / source).read_text(encoding="utf-8") + "\nend")(
                "Host", self.lua.globals().addon
            )

    def test_default_close_consumes_only_escape_and_restores_propagation(self):
        self.lua.execute('''
            frame = NewFrame()
            local base = function(self) self.baseKeys = (self.baseKeys or 0) + 1 end
            frame:SetScript("OnKeyDown", base)
            addon.LibOrbitUI.EscapeClose:Attach(frame)
            addon.LibOrbitUI.EscapeClose:Attach(frame)
            assert(#mock.inputs == 1 and frame.keyboardCalls == 0 and frame.scripts.OnKeyDown == base)
            input = mock.inputs[1]
            assert(not input:IsShown() and not input.keyboard)
            frame:Show()
            assert(input.keyboard and input.keyboardCalls == 1 and input.propagate and input:IsVisible())
            assert(input.strata == frame.strata and input.level == frame.level + 1 and input.parent == UIParent)
            assert(Key(input, "TAB"))
            assert(frame:IsShown() and #mock.timers == 0)
            assert(not Key(input, "ESCAPE"))
            assert(not frame:IsShown() and not input:IsShown() and #mock.timers == 1)
            RunTimers()
            assert(not input:IsShown() and #UISpecialFrames == 0)
            frame:Show()
            assert(input.propagate and input:IsShown() and input.keyboardCalls == 1)
        ''')

    def test_combat_rejects_escape_and_custom_close_uses_normal_owner(self):
        self.lua.execute('''
            frame = NewFrame()
            closed = 0
            local close = function(self) closed = closed + 1 self:Hide() end
            addon.LibOrbitUI.EscapeClose:Attach(frame, close)
            addon.LibOrbitUI.EscapeClose:Attach(frame, close)
            frame:Show()
            input = mock.inputs[1]
            Combat(true)
            assert(Key(input, "ESCAPE"))
            assert(frame:IsShown() and closed == 0 and #mock.timers == 0)
            Combat(false)
            assert(not Key(input, "ESCAPE"))
            assert(not frame:IsShown() and closed == 1 and not input.propagate)
            RunTimers()
            assert(not input:IsShown() and #UISpecialFrames == 0)
        ''')

    def test_first_attachment_in_combat_never_arms_window_or_proxy(self):
        self.lua.execute('''
            mock.combat = true
            frame = NewFrame()
            frame:Show()
            addon.LibOrbitUI.EscapeClose:Attach(frame)
            input = mock.inputs[1]
            assert(frame.keyboardCalls == 0 and input.keyboardCalls == 0 and not input:IsShown())
            assert(Key(input, "W") and Key(input, "ESCAPE"))
            RunTimers()
            Combat(false)
            assert(input:IsShown() and input.propagate and input.keyboardCalls == 1)
            assert(not Key(input, "ESCAPE") and not frame:IsShown())
        ''')

    def test_consumed_escape_then_combat_cannot_trap_gameplay_keys(self):
        for event_first in (False, True):
            with self.subTest(event_first=event_first):
                self.setUp()
                self.lua.globals().eventFirst = event_first
                self.lua.execute('''
                    frame = NewFrame()
                    local closes = 0
                    addon.LibOrbitUI.EscapeClose:Attach(frame, function() closes = closes + 1 end)
                    frame:Show()
                    input = mock.inputs[1]
                    assert(not Key(input, "ESCAPE") and closes == 1 and input:IsShown())
                    Combat(true, eventFirst)
                    RunTimers()
                    assert(not input:IsShown() and Key(input, "W") and Key(input, "1"))
                    Combat(false)
                    assert(input:IsShown() and input.propagate and Key(input, "W"))
                ''')

    def test_close_reopen_during_combat_waits_for_regen_and_latest_visibility(self):
        self.lua.execute('''
            frame = NewFrame()
            addon.LibOrbitUI.EscapeClose:Attach(frame)
            frame:Show()
            input = mock.inputs[1]
            Key(input, "ESCAPE")
            Combat(true)
            frame:Show()
            RunTimers()
            assert(not input:IsShown() and frame:IsShown() and Key(input, "W"))
            frame:Hide()
            Combat(false)
            assert(not input:IsShown())
            frame:Show()
            assert(input:IsShown() and input.propagate and input.keyboardCalls == 1)
        ''')

    def test_inherited_hide_does_not_rearm_and_repeat_attach_stays_bounded(self):
        self.lua.execute('''
            parent = NewFrame(UIParent)
            parent:Show()
            frame = NewFrame(parent)
            local closed = 0
            local close = function() closed = closed + 1 end
            addon.LibOrbitUI.EscapeClose:Attach(frame, close)
            frame:Show()
            input = mock.inputs[1]
            for i = 1, 10 do
                addon.LibOrbitUI.EscapeClose:Attach(frame, close)
                Key(input, "ESCAPE")
            end
            assert(#mock.inputs == 1 and #mock.timers == 1 and closed == 10)
            assert(Key(input, "W") and #mock.timers == 1)
            parent:Hide()
            frame:Fire("OnHide")
            RunTimers()
            Combat(true)
            Combat(false)
            assert(not input:IsShown() and Key(input, "W"))
            parent:Show()
            frame:Fire("OnShow")
            assert(input:IsShown() and input.propagate and input.keyboardCalls == 1)
        ''')

    def test_runtime_has_no_taint_sensitive_global_close_registration(self):
        offenders = []
        for path in RUNTIME.rglob("*.lua"):
            source = path.read_text(encoding="utf-8")
            for symbol in ("UISpecialFrames", "RegisterGameMenuEscHandler"):
                if symbol in source:
                    offenders.append((path.relative_to(RUNTIME).as_posix(), symbol))
        self.assertEqual(offenders, [])

    def test_input_depth_follows_window_changes_without_rearming_consumed_key(self):
        self.lua.execute('''
            frame = NewFrame()
            addon.LibOrbitUI.EscapeClose:Attach(frame, function() end)
            frame:Show()
            input = mock.inputs[1]
            frame:Raise()
            assert(input.level == frame.level + 1)
            frame:Lower()
            assert(input.level == frame.level + 1)
            frame:SetFrameLevel(30)
            frame:SetFrameStrata("TOOLTIP")
            assert(input.level == 31 and input.strata == "TOOLTIP")
            Key(input, "ESCAPE")
            frame:Raise()
            assert(not input.propagate and input:IsShown())
            Combat(true)
            frame:SetFrameLevel(60)
            frame:SetFrameStrata("DIALOG")
            assert(not input:IsShown())
            RunTimers()
            Combat(false)
            assert(input:IsShown() and input.propagate and input.level == 61 and input.strata == "DIALOG")
        ''')


if __name__ == "__main__":
    unittest.main()
