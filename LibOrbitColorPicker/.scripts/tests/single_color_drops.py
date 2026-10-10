"""Verify which swatch drags single-color mode accepts and how a drop changes its pin."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitColorPicker-1.0"
MAGE = (0.25, 0.78, 0.92)

ENVIRONMENT = '''
    local noOp = function() end
    local methods = {}
    function NewObject()
        return setmetatable({shown = true, scripts = {}}, {__index = function(_, key)
            return methods[key] or noOp
        end})
    end
    function methods:SetScript(name, handler) self.scripts[name] = handler end
    function methods:CreateTexture() return NewObject() end
    function methods:CreateFontString() return NewObject() end
    function methods:Show() self.shown = true end
    function methods:Hide()
        local wasShown = self.shown
        self.shown = false
        if wasShown and self.scripts.OnHide then self.scripts.OnHide(self) end
    end
    function methods:IsShown() return self.shown end
    function methods:IsMouseOver() return self == mouseFocus end
    function methods:GetWidth() return 100 end
    function methods:GetHeight() return 24 end
    function methods:GetLeft() return 0 end
    function methods:GetEffectiveScale() return 1 end
    function methods:GetFrameLevel() return 0 end
    function methods:SetAtlas(atlas) self.atlas = atlas end

    function CreateFrame(_, _, _, template)
        local frame = NewObject()
        if template == "UICheckButtonTemplate" then frame.text = NewObject() end
        return frame
    end
    function Mixin(object, ...)
        for i = 1, select("#", ...) do
            for key, value in pairs((select(i, ...))) do object[key] = value end
        end
        return object
    end
    function wipe(t)
        for key in pairs(t) do t[key] = nil end
        return t
    end
    function CreateColor(r, g, b, a) return {r = r, g = g, b = b, a = a} end
    C_CurveUtil = {CreateColorCurve = function() return {AddPoint = noOp} end}
    C_Timer = {After = function(_, callback) callback() end}
    PixelUtil = {GetNearestPixelSize = function(_, _, size) return size end}
    RAID_CLASS_COLORS = {MAGE = {r = 0.25, g = 0.78, b = 0.92}}
    UIParent = NewObject()
    cursorX = 0
    function GetCursorPosition() return cursorX, 0 end
    function UnitClass() return "Mage", "MAGE" end
    function GetClassAtlas(class) return "classicon-" .. class end
    function issecretvalue() return false end
    function InCombatLockdown() return false end
    function debugstack() return "Interface/AddOns/Test/LibOrbitColorPicker-1.0/LibOrbitColorPicker-1.0.lua:1" end
    function GetLocale() return "enUS" end

    lib = {}; table.freeze = function(t) return t end
    LibStub = {NewLibrary = function() return lib end}
'''

SCENARIO = '''
    function OpenPicker(singleColor, initialData)
        closed = nil
        lib:Open({
            initialData = initialData,
            forceSingleColor = singleColor,
            recentColorsDb = {{r = 0, g = 0, b = 1, a = 1}},
            callback = function(result, wasCancelled) closed = {result = result, cancelled = wasCancelled} end,
        })
    end
    function TryDrag(source, overBar, dropX)
        source.scripts.OnDragStart(source)
        local started = lib.drag.active == true
        mouseFocus = overBar and lib.ui.gradientBar or nil
        cursorX = dropX or 0
        source.scripts.OnDragStop(source)
        mouseFocus = nil
        return started
    end
    RED = {r = 1, g = 0, b = 0, a = 1}
'''


def load_picker():
    lua = LuaRuntime()
    lua.execute(ENVIRONMENT)
    lua.execute((RUNTIME / "LibOrbitColorPicker-1.0.lua").read_text(encoding="utf-8"))
    lua.execute(SCENARIO)
    return lua


class SingleColorDrops(unittest.TestCase):
    def assertColor(self, lua, expression, expected):
        for channel, value in zip("rgb", expected):
            self.assertAlmostEqual(lua.eval(f"{expression}.{channel}"), value)

    def test_class_drop_replaces_the_single_pin(self):
        lua = load_picker()
        lua.execute("OpenPicker(true, RED)")
        self.assertFalse(lua.eval("TryDrag(lib.ui.currentSwatch, true, 20)"))
        self.assertFalse(lua.eval("TryDrag(lib.ui.recentColorsBar.swatches[1], true, 20)"))
        self.assertEqual(lua.eval("#lib.pins"), 1)
        self.assertIsNone(lua.eval("lib.pins[1].type"))

        self.assertTrue(lua.eval("TryDrag(lib.ui.classSwatch, true, 80)"))
        self.assertEqual(lua.eval("#lib.pins"), 1)
        self.assertEqual(lua.eval("lib.pins[1].type"), "class")
        self.assertAlmostEqual(lua.eval("lib.pins[1].position"), 0.8)
        self.assertEqual(lua.eval("lib.ui.gradientBar.pinHandles[1].ClassIcon.atlas"), "classicon-MAGE")
        self.assertTrue(lua.eval("lib.ui.gradientBar.pinHandles[1].ClassIcon.shown"))
        self.assertColor(lua, "lib.ui.colorSelect", MAGE)

        lua.execute("lib.ui.applyButton.scripts.OnClick(lib.ui.applyButton)")
        self.assertFalse(lua.eval("closed.cancelled"))
        self.assertEqual(lua.eval("#closed.result.pins"), 1)
        self.assertEqual(lua.eval("closed.result.pins[1].type"), "class")
        self.assertColor(lua, "closed.result.pins[1].color", MAGE)

    def test_class_drop_off_the_bar_keeps_the_pin(self):
        lua = load_picker()
        lua.execute("OpenPicker(true, RED)")
        self.assertTrue(lua.eval("TryDrag(lib.ui.classSwatch, false, 80)"))
        self.assertEqual(lua.eval("#lib.pins"), 1)
        self.assertIsNone(lua.eval("lib.pins[1].type"))
        self.assertColor(lua, "lib.pins[1].color", (1, 0, 0))

    def test_manual_edit_after_class_drop_demotes_the_pin(self):
        lua = load_picker()
        lua.execute("OpenPicker(true, RED)")
        self.assertTrue(lua.eval("TryDrag(lib.ui.classSwatch, true, 80)"))
        self.assertEqual(lua.eval("lib.pins[1].type"), "class")
        lua.execute("lib.ui.colorSelect:SetColorRGB(0, 1, 0)")
        self.assertIsNone(lua.eval("lib.pins[1].type"))
        self.assertColor(lua, "lib.pins[1].color", (0, 1, 0))

    def test_cancel_restores_the_replaced_pin(self):
        lua = load_picker()
        lua.execute("OpenPicker(true, RED)")
        self.assertTrue(lua.eval("TryDrag(lib.ui.classSwatch, true, 80)"))
        self.assertEqual(lua.eval("lib.pins[1].type"), "class")
        lua.execute("lib.ui.closeButton.scripts.OnClick(lib.ui.closeButton)")
        self.assertTrue(lua.eval("closed.cancelled"))
        self.assertEqual(lua.eval("#closed.result.pins"), 1)
        self.assertIsNone(lua.eval("closed.result.pins[1].type"))
        self.assertColor(lua, "closed.result.pins[1].color", (1, 0, 0))

    def test_multi_color_drops_still_add_pins(self):
        lua = load_picker()
        lua.execute("OpenPicker(false, {pins = {{position = 0, color = RED}}})")
        self.assertTrue(lua.eval("TryDrag(lib.ui.classSwatch, true, 80)"))
        self.assertTrue(lua.eval("TryDrag(lib.ui.currentSwatch, true, 40)"))
        self.assertEqual(lua.eval("#lib.pins"), 3)
        self.assertEqual(lua.eval("lib.pins[2].type"), "class")


if __name__ == "__main__":
    unittest.main()
