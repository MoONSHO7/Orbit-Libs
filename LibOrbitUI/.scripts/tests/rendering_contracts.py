"""Check shipped text anchoring and immutable rendering/movement namespaces under Lua 5.1."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
SOURCES = ("Core/Bootstrap.lua", "Rendering/TextPosition.lua", "Rendering/GridMath.lua", "Rendering/ColorCurve.lua",
           "Movement/Geometry.lua")
HARNESS = r'''
frozen = {}
table.freeze = function(value) frozen[value] = true; return value end
function issecretvalue() return false end
function Mixin(target, mixin)
    for key, value in pairs(mixin) do target[key] = value end
    return target
end
addon = {}
'''


class RenderingContracts(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(HARNESS)
        for relative in SOURCES:
            self.lua.execute("return assert(loadstring(...))", (RUNTIME / relative).read_text(encoding="utf-8"))(
                "Consumer", self.lua.globals().addon
            )
        self.lua.execute("UI = addon.LibOrbitUI")

    def test_anchor_points_compose_each_axis(self):
        self.lua.execute('''
            local Build = UI.TextPosition.BuildAnchorPoint
            assert(Build("CENTER", "CENTER") == "CENTER")
            assert(Build("LEFT", "CENTER") == "LEFT" and Build("RIGHT", "CENTER") == "RIGHT")
            assert(Build("CENTER", "TOP") == "TOP" and Build("CENTER", "BOTTOM") == "BOTTOM")
            assert(Build("LEFT", "TOP") == "TOPLEFT" and Build("RIGHT", "BOTTOM") == "BOTTOMRIGHT")
        ''')

    def test_setter_places_authored_offsets_or_the_caller_anchor(self):
        self.lua.execute('''
            local placed
            local pixel = { Point = function(_, region, point, parent, relativePoint, x, y)
                placed = { region = region, point = point, parent = parent, relativePoint = relativePoint,
                    x = x, y = y }
            end }
            local region = { cleared = 0 }
            function region:ClearAllPoints() self.cleared = self.cleared + 1 end
            function region:SetJustifyH(value) self.justifyH = value end
            local parent = {}
            local set = UI.TextPosition.CreateSetter(pixel)
            set(region, parent, { anchorX = "LEFT", anchorY = "TOP", offsetX = 5, offsetY = -3, justifyH = "LEFT" },
                "CENTER", 9, 9)
            assert(placed.region == region and placed.parent == parent and region.cleared == 1)
            assert(placed.point == "TOPLEFT" and placed.relativePoint == "TOPLEFT")
            assert(placed.x == 5 and placed.y == -3 and region.justifyH == "LEFT")
            set(region, parent, { anchorX = "CENTER", anchorY = "BOTTOM" }, "CENTER", 9, 9)
            assert(placed.point == "BOTTOM" and placed.x == 0 and placed.y == 0 and region.justifyH == "CENTER")
            set(region, parent, nil, "RIGHT", 2, 4)
            assert(placed.point == "RIGHT" and placed.relativePoint == "RIGHT" and placed.x == 2 and placed.y == 4)
            assert(region.cleared == 3)
        ''')

    def test_shared_namespaces_and_sampler_methods_are_frozen(self):
        self.lua.execute('''
            assert(frozen[UI.TextPosition] and frozen[UI.GridMath] and frozen[UI.Geometry])
            local sampler = UI.ColorCurve:Create()
            local methods
            for value in pairs(frozen) do
                if value.SampleColorCurve == sampler.SampleColorCurve then methods = value end
            end
            assert(methods and methods ~= sampler and not frozen[sampler])
        ''')


if __name__ == "__main__":
    unittest.main()
