"""Verify gradient segments, recent colours, apply/cancel results, deferred-show sessions and desaturation."""
import unittest

from lupa.lua51 import LuaRuntime
from single_color_drops import ENVIRONMENT, RUNTIME, SCENARIO

RECORDERS = '''
    function methods:SetSize(w, h) self.size = {w, h} end
    function methods:SetPoint(point, relative, relativePoint, x, y) self.point = {point, x or 0, y or 0} end
    function methods:SetGradient(_, left, right) self.gradient = {left, right} end
    function methods:SetText(text) self.text = text end
    function methods:SetChecked(value) self.checked = value end
    function methods:GetChecked() return self.checked end
    function methods:SetEnabled(value) self.enabled = value end
    timers = {}
    C_Timer = {After = function(_, callback) timers[#timers + 1] = callback end}
    function RunTimers()
        local queue = timers
        timers = {}
        for _, callback in ipairs(queue) do callback() end
    end
    C_CurveUtil = {CreateColorCurve = function()
        local curve = {points = {}}
        function curve:AddPoint(x, color) self.points[#self.points + 1] = {x = x, color = color} end
        return curve
    end}
    BLUE = {r = 0, g = 0, b = 1, a = 1}
    GREEN = {r = 0, g = 1, b = 0, a = 1}
    function Shown(bar)
        local list = {}
        for i, seg in ipairs(bar.segments) do if seg.shown then list[#list + 1] = seg end end
        return list
    end
'''


def load_picker():
    lua = LuaRuntime()
    lua.execute(ENVIRONMENT.replace("local methods = {}", "methods = {}") + RECORDERS)
    lua.execute((RUNTIME / "LibOrbitColorPicker-1.0.lua").read_text(encoding="utf-8"))
    lua.execute(SCENARIO)
    return lua


class PickerSession(unittest.TestCase):
    def open(self, single, data="nil", extra=""):
        lua = load_picker()
        lua.execute(f'''
            closed = nil
            lib:Open({{ initialData = {data}, forceSingleColor = {str(single).lower()}, recentColorsDb = recents or {{}},
                callback = function(result, cancelled) closed = {{ result = result, cancelled = cancelled }} end, {extra} }})
            RunTimers()
        ''')
        return lua

    def segments(self, lua):
        out = []
        for seg in lua.eval("Shown(lib.ui.gradientBar)").values():
            left, right = seg.gradient[1], seg.gradient[2]
            out.append((round(seg.point[2], 6), round(seg.size[1], 6),
                        (left.r, left.g, left.b), (right.r, right.g, right.b)))
        return out

    def test_gradient_paints_edge_fills_and_sorted_spans(self):
        lua = self.open(False, "{ pins = { { position = 0.8, color = BLUE }, { position = 0.2, color = RED } } }")
        self.assertEqual(self.segments(lua), [
            (0, 20, (1, 0, 0), (1, 0, 0)),
            (20, 60, (1, 0, 0), (0, 0, 1)),
            (80, 20, (0, 0, 1), (0, 0, 1)),
        ])
        points = lua.eval("lib:GetColorCurve().points")
        self.assertEqual([points[i].x for i in (1, 2)], [0.2, 0.8])
        lua.execute("lib:LoadFromCurve({ pins = { { position = 1, color = BLUE }, { position = 0.5, color = GREEN }, { position = 0, color = RED } } })")
        self.assertEqual(self.segments(lua), [
            (0, 50, (1, 0, 0), (0, 1, 0)),
            (50, 50, (0, 1, 0), (0, 0, 1)),
        ])

    def test_apply_button_names_apply_or_clear(self):
        lua = self.open(False, "{ pins = { { position = 0, color = RED } } }")
        self.assertEqual(lua.eval("lib.ui.applyButton.text"), "Apply Color")
        lua.execute("lib:ClearPins()")
        self.assertEqual(lua.eval("lib.ui.applyButton.text"), "Clear Color")
        self.assertEqual(lua.eval("lib.ui.modeTitle.text"), "Multi-Color Mode")
        self.assertEqual(self.open(True, "RED").eval("lib.ui.modeTitle.text"), "Single Color Mode")

    def test_recent_colours_dedupe_by_hex_and_alpha_and_skip_class_pins(self):
        lua = self.open(False, "{ pins = {} }")
        lua.execute('''
            lib:AddPin(0.1, RED); lib:AddPin(0.2, BLUE)
            lib:AddPin(0.3, {r = 1.001, g = 0, b = 0, a = 0.98})
            lib:AddPin(0.4, {r = 0, g = 0, b = 1, a = 0.5})
            lib:AddClassColorPin(0.5)
            lib:AddPin(0.6, {r = 0, g = 1, b = 0, a = 1})
            lib:AddRecentColor({type = "class", color = BLUE})
        ''')
        recents = [(c.r, c.g, c.b, c.a) for c in lua.eval("lib.recentColors").values()]
        self.assertEqual(recents, [(0, 1, 0, 1), (0, 0, 1, 0.5), (1.001, 0, 0, 0.98), (0, 0, 1, 1)])
        lua.execute("for i = 1, 12 do lib:AddPin(i / 20, {r = i / 12, g = 0, b = 0, a = 1}) end")
        self.assertEqual(len(lua.eval("lib.recentColors")), 8)
        self.assertAlmostEqual(lua.eval("lib.recentColors[1].r"), 1)
        self.assertTrue(lua.eval("lib.ui.recentColorsBar.swatches[8].ColorModel ~= nil"))

    def test_cancel_restores_snapshot_pins_and_recents(self):
        lua = load_picker()
        lua.execute("recents = { BLUE }")
        lua.execute('''
            lib:Open({ initialData = { pins = { { position = 0.25, color = RED } } }, recentColorsDb = recents,
                callback = function(result, cancelled) closed = { result = result, cancelled = cancelled } end })
            RunTimers()
            lib:AddPin(0.75, GREEN)
            lib.ui.closeButton.scripts.OnClick(lib.ui.closeButton)
        ''')
        self.assertTrue(lua.eval("closed.cancelled"))
        self.assertEqual(lua.eval("#closed.result.pins"), 1)
        self.assertEqual(lua.eval("closed.result.pins[1].position"), 0.25)
        self.assertEqual([(c.r, c.g, c.b) for c in lua.eval("recents").values()], [(0, 0, 1)])
        self.assertEqual(lua.eval("#closed.result.curve.points"), 1)

    def test_apply_with_no_pins_returns_no_result_and_single_apply_records_recent(self):
        lua = self.open(False, "{ pins = { { position = 0, color = RED } } }")
        lua.execute("lib:ClearPins(); lib.ui.applyButton.scripts.OnClick(lib.ui.applyButton)")
        self.assertFalse(lua.eval("closed.cancelled"))
        self.assertIsNone(lua.eval("closed.result"))
        lua = load_picker()
        lua.execute('''
            recents = {}
            lib:Open({ initialData = RED, forceSingleColor = true, recentColorsDb = recents,
                callback = function(result, cancelled) closed = { result = result, cancelled = cancelled } end })
            RunTimers()
            lib.ui.colorSelect:SetColorRGB(0, 0, 1)
            lib.ui.applyButton.scripts.OnClick(lib.ui.applyButton)
        ''')
        self.assertEqual((lua.eval("closed.result.pins[1].color.b"), lua.eval("closed.result.pins[1].color.r")), (1, 0))
        self.assertEqual([(c.r, c.g, c.b) for c in lua.eval("recents").values()], [(0, 0, 1)])
        self.assertEqual(lua.eval("closed.result.curve.points[1].color.b"), 1)

    def test_single_colour_edits_rebuild_the_curve_but_multi_mode_leaves_pins(self):
        lua = self.open(True, "RED")
        lua.execute("before = lib:GetColorCurve(); lib.ui.colorSelect:SetColorRGB(0, 1, 0)")
        self.assertFalse(lua.eval("rawequal(before, lib:GetColorCurve())"))
        self.assertEqual(lua.eval("lib:GetColorCurve().points[1].color.g"), 1)
        lua = self.open(False, "{ pins = { { position = 0, color = RED }, { position = 1, color = BLUE } } }")
        lua.execute("lib.ui.colorSelect:SetColorRGB(0, 1, 0)")
        self.assertEqual([lua.eval(f"lib.pins[{i}].color.g") for i in (1, 2)], [0, 0])
        lua = self.open(True, "nil")
        lua.execute("lib:ClearPins(); lib.ui.colorSelect:SetColorRGB(0, 1, 0)")
        self.assertEqual(lua.eval("#lib.pins"), 0)

    def test_open_shows_the_class_icon_and_single_pins_carry_alpha_into_the_area(self):
        lua = self.open(True, "RED")
        self.assertEqual(lua.eval("lib.ui.classSwatch.ClassIcon.atlas"), "classicon-MAGE")
        self.assertTrue(lua.eval("lib.ui.classSwatch.ClassIcon.shown"))
        lua.execute("lib:ClearPins(); lib:AddPin(0.3, {r = 0, g = 0, b = 1, a = 0.5})")
        self.assertEqual(lua.eval("lib.ui.colorSelect:GetColorAlpha()"), 0.5)
        self.assertEqual(lua.eval("lib.ui.colorSelect.b"), 1)

    def test_a_reopen_invalidates_the_previous_deferred_show(self):
        lua = load_picker()
        lua.execute('''
            opened = {}
            lib:Open({ initialData = { pins = {} }, onOpen = function() opened[#opened + 1] = "first" end })
            lib:Open({ initialData = { pins = {} }, onOpen = function() opened[#opened + 1] = "second" end })
            RunTimers()
        ''')
        self.assertEqual(list(lua.eval("opened").values()), ["second"])
        lua.execute('''
            lib:Open({ initialData = { pins = {} }, onOpen = function() opened[#opened + 1] = "closed" end })
            lib:CloseFrame(); RunTimers()
        ''')
        self.assertEqual(list(lua.eval("opened").values()), ["second"])

    def test_desaturation_round_trips_only_when_offered(self):
        lua = self.open(False, "{ pins = { { position = 0, color = RED } }, desaturated = true }", "hasDesaturation = true")
        self.assertTrue(lua.eval("lib.ui.desatCheckbox.checked"))
        self.assertTrue(lua.eval("lib.ui.desatCheckbox.shown"))
        lua.execute('''
            lib.ui.desatCheckbox.checked = false
            lib.ui.desatCheckbox.scripts.OnClick(lib.ui.desatCheckbox)
            lib.ui.applyButton.scripts.OnClick(lib.ui.applyButton)
        ''')
        self.assertIs(lua.eval("closed.result.desaturated"), False)
        lua = self.open(False, "{ pins = { { position = 0, color = RED } }, desaturated = true }")
        self.assertFalse(lua.eval("lib.ui.desatCheckbox.shown"))
        lua.execute("lib.ui.applyButton.scripts.OnClick(lib.ui.applyButton)")
        self.assertIsNone(lua.eval("closed.result.desaturated"))

    def test_close_hides_the_private_tooltip_unless_the_host_supplies_one(self):
        lua = self.open(False, "{ pins = {} }")
        lua.execute("tip = lib.privateTooltip; tip.shown = true; lib:CloseFrame()")
        self.assertFalse(lua.eval("tip.shown"))
        lua = self.open(False, "{ pins = {} }", "tooltipHide = function() hostHidden = true end")
        lua.execute("tip = lib.privateTooltip; tip.shown = true; lib:CloseFrame()")
        self.assertTrue(lua.eval("hostHidden"))
        self.assertTrue(lua.eval("tip.shown"))


if __name__ == "__main__":
    unittest.main()
