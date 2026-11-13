"""Verify the colour area's own HSV conversion, hue retention, class-pin demotion and unsized-bar refresh."""
import unittest

from single_color_drops import load_picker

HUE_STOPS = (
    ((1, 0, 0), 0 / 6),
    ((1, 1, 0), 1 / 6),
    ((0, 1, 0), 2 / 6),
    ((0, 1, 1), 3 / 6),
    ((0, 0, 1), 4 / 6),
    ((1, 0, 1), 5 / 6),
)
ROUND_TRIP = ((0.2, 0.4, 0.6), (0.9, 0.1, 0.3), (0.05, 0.8, 0.2), (0.6, 0.6, 0.1), (1, 0, 0.5), (0.3, 0.3, 0.9))


class ColorArea(unittest.TestCase):
    def open(self):
        lua = load_picker()
        lua.execute("OpenPicker(true, RED)")
        return lua

    def hsv(self, lua):
        return lua.eval("lib.ui.colorSelect.h"), lua.eval("lib.ui.colorSelect.s"), lua.eval("lib.ui.colorSelect.v")

    def rgb(self, lua):
        return lua.eval("lib.ui.colorSelect.r"), lua.eval("lib.ui.colorSelect.g"), lua.eval("lib.ui.colorSelect.b")

    def assertTriple(self, actual, expected):
        for got, want in zip(actual, expected):
            self.assertAlmostEqual(got, want, places=6)

    def test_rgb_entry_derives_hue_saturation_and_value_for_every_sector(self):
        lua = self.open()
        for (r, g, b), hue in HUE_STOPS:
            lua.execute(f"lib.ui.colorSelect:SetColorRGBA({r}, {g}, {b}, 1)")
            self.assertTriple(self.hsv(lua), (hue, 1, 1))
        lua.execute("lib.ui.colorSelect:SetColorRGBA(1, 0, 0.5, 1)")
        self.assertTriple(self.hsv(lua), (11 / 12, 1, 1))
        lua.execute("lib.ui.colorSelect:SetColorRGBA(0.5, 0.25, 0, 1)")
        self.assertTriple(self.hsv(lua), (1 / 12, 1, 0.5))
        lua.execute("lib.ui.colorSelect:SetColorRGBA(0.2, 0.5, 0.4, 1)")
        self.assertTriple(self.hsv(lua), ((2 + (0.4 - 0.2) / 0.3) / 6, 0.6, 0.5))

    def test_achromatic_colours_keep_the_last_real_hue(self):
        lua = self.open()
        lua.execute("lib.ui.colorSelect:SetColorRGBA(0, 0, 1, 1)")
        for grey in ("0.5, 0.5, 0.5", "0, 0, 0", "1, 1, 1"):
            lua.execute(f"lib.ui.colorSelect:SetColorRGBA({grey}, 1)")
            hue, saturation, _ = self.hsv(lua)
            self.assertAlmostEqual(hue, 4 / 6)
            self.assertEqual(saturation, 0)
        self.assertEqual(lua.eval("lib.ui.colorSelect.v"), 1)
        lua.execute("lib.ui.colorSelect:SetColorRGBA(0, 0, 0, 1)")
        self.assertEqual(lua.eval("lib.ui.colorSelect.v"), 0)

    def test_hsv_entry_interpolates_between_stops_and_wraps_at_the_rail_end(self):
        lua = self.open()
        for (r, g, b), hue in HUE_STOPS:
            lua.execute(f"lib.ui.colorSelect:SetColorHSV({hue}, 1, 1)")
            self.assertTriple(self.rgb(lua), (r, g, b))
        lua.execute("lib.ui.colorSelect:SetColorHSV(1, 1, 1)")
        self.assertTriple(self.rgb(lua), (1, 0, 0))
        lua.execute("lib.ui.colorSelect:SetColorHSV(1 / 12, 1, 1)")
        self.assertTriple(self.rgb(lua), (1, 0.5, 0))
        lua.execute("lib.ui.colorSelect:SetColorHSV(0, 0.5, 0.5)")
        self.assertTriple(self.rgb(lua), (0.5, 0.25, 0.25))
        lua.execute("lib.ui.colorSelect:SetColorHSV(0.3, 0, 0.75)")
        self.assertTriple(self.rgb(lua), (0.75, 0.75, 0.75))

    def test_rgb_and_hsv_entry_round_trip(self):
        lua = self.open()
        for r, g, b in ROUND_TRIP:
            lua.execute(f"lib.ui.colorSelect:SetColorRGBA({r}, {g}, {b}, 1)")
            h, s, v = self.hsv(lua)
            lua.execute(f"lib.ui.colorSelect:SetColorHSV({h!r}, {s!r}, {v!r})")
            self.assertTriple(self.rgb(lua), (r, g, b))

    def test_opacity_only_change_keeps_a_class_pin(self):
        lua = self.open()
        self.assertTrue(lua.eval("TryDrag(lib.ui.classSwatch, true, 80)"))
        lua.execute("lib.ui.colorSelect:SetColorAlpha(0.5)")
        self.assertEqual(lua.eval("lib.pins[1].type"), "class")
        self.assertAlmostEqual(lua.eval("lib.pins[1].color.a"), 0.5)
        lua.execute("lib.ui.colorSelect:SetColorRGB(0.25, 0.5, 0.92)")
        self.assertIsNone(lua.eval("lib.pins[1].type"))

    def test_many_pins_at_one_position_sort_and_paint(self):
        lua = load_picker()
        lua.execute("OpenPicker(false, nil)")
        lua.execute('''
            lib:ClearPins()
            for i = 1, 16 do lib:AddPin(0.5, {r = i / 16, g = 0, b = 0, a = 1}) end
            lib:AddPin(0.1, {r = 0, g = 1, b = 0, a = 1})
            lib.ui.gradientBar:Refresh()
        ''')
        self.assertEqual(lua.eval("#lib.pins"), 17)
        positions = [lua.eval(f"lib.pins[{i}].position") for i in range(1, 18)]
        self.assertEqual(sorted(positions), [0.1] + [0.5] * 16)
        self.assertIsNotNone(lua.eval("lib:GetColorCurve()"))

    def test_unsized_bar_refresh_paints_nothing(self):
        lua = self.open()
        lua.execute('''
            local bar = lib.ui.gradientBar
            bar.SolidTexture.shown = "untouched"
            bar.SegmentContainer.GetWidth = function() return 0 end
            bar:Refresh()
        ''')
        self.assertEqual(lua.eval("lib.ui.gradientBar.SolidTexture.shown"), "untouched")
        lua.execute('''
            local bar = lib.ui.gradientBar
            bar.SegmentContainer.GetWidth = function() return 100 end
            bar.SegmentContainer.GetHeight = function() return 0 end
            bar:Refresh()
        ''')
        self.assertEqual(lua.eval("lib.ui.gradientBar.SolidTexture.shown"), "untouched")
        lua.execute("lib.ui.gradientBar.SegmentContainer.GetHeight = function() return 24 end; lib.ui.gradientBar:Refresh()")
        self.assertIs(lua.eval("lib.ui.gradientBar.SolidTexture.shown"), True)


if __name__ == "__main__":
    unittest.main()
