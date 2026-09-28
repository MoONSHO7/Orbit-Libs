"""Verify addon windows consume Escape locally without joining Blizzard's shared close scan."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"

HARNESS = r'''
addon = {}
mock = {combat = false, timers = {}}
UISpecialFrames = {}
function InCombatLockdown() return mock.combat end
C_Timer = {}
function C_Timer.After(_, callback) table.insert(mock.timers, callback) end
function RunTimers()
    local timers = mock.timers
    mock.timers = {}
    for _, callback in ipairs(timers) do callback() end
end
function NewFrame()
    local frame = {shown = false, scripts = {}, hooks = {}, keyboardCalls = 0}
    function frame:EnableKeyboard(value)
        self.keyboard = value
        self.keyboardCalls = self.keyboardCalls + 1
    end
    function frame:SetPropagateKeyboardInput(value) self.propagate = value end
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
    return frame
end
'''


class EscapeClose(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute(HARNESS)
        for source in ("Core/Bootstrap.lua", "Core/EscapeClose.lua"):
            self.lua.execute("return function(...)\n" + (RUNTIME / source).read_text(encoding="utf-8") + "\nend")(
                "Host", self.lua.globals().addon
            )

    def test_default_close_consumes_only_escape_and_restores_propagation(self):
        self.lua.execute('''
            frame = NewFrame()
            frame:SetScript("OnKeyDown", function(self) self.baseKeys = (self.baseKeys or 0) + 1 end)
            addon.LibOrbitUI.EscapeClose:Attach(frame)
            addon.LibOrbitUI.EscapeClose:Attach(frame)
            assert(frame.keyboard and frame.keyboardCalls == 1 and frame.propagate)
            frame:Show()
            frame:Fire("OnKeyDown", "TAB")
            assert(frame:IsShown() and frame.propagate and #mock.timers == 0)
            frame:Fire("OnKeyDown", "ESCAPE")
            assert(not frame:IsShown() and not frame.propagate and #mock.timers == 1)
            RunTimers()
            assert(frame.propagate and frame.baseKeys == 2 and #UISpecialFrames == 0)
        ''')

    def test_combat_rejects_escape_and_custom_close_uses_normal_owner(self):
        self.lua.execute('''
            frame = NewFrame()
            closed = 0
            local close = function(self) closed = closed + 1 self:Hide() end
            addon.LibOrbitUI.EscapeClose:Attach(frame, close)
            addon.LibOrbitUI.EscapeClose:Attach(frame, close)
            frame:Show()
            mock.combat = true
            frame:Fire("OnKeyDown", "ESCAPE")
            assert(frame:IsShown() and closed == 0 and #mock.timers == 0)
            mock.combat = false
            frame:Fire("OnKeyDown", "ESCAPE")
            assert(not frame:IsShown() and closed == 1 and not frame.propagate)
            RunTimers()
            assert(frame.propagate and #UISpecialFrames == 0)
        ''')

    def test_runtime_has_no_taint_sensitive_global_close_registration(self):
        offenders = []
        for path in RUNTIME.rglob("*.lua"):
            source = path.read_text(encoding="utf-8")
            for symbol in ("UISpecialFrames", "RegisterGameMenuEscHandler"):
                if symbol in source:
                    offenders.append((path.relative_to(RUNTIME).as_posix(), symbol))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
