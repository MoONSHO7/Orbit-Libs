"""Verify picker embedding, asset ownership and class-pin visuals."""
from pathlib import Path
import shutil
import tempfile
import unittest
from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitColorPicker-1.0"


class EmbeddedAssets(unittest.TestCase):
    def test_materialized_paths_locales_and_shared_copy_owner(self):
        with tempfile.TemporaryDirectory(prefix="orbit-picker-contract-") as directory:
            root = Path(directory)
            for addon, parent in (("Orbit", "Core/Libs"), ("Orbit_StatusWidget", "Libs"), ("RenamedHost", "Nested/Libs")):
                dest = root / "Interface/AddOns" / addon / parent / RUNTIME.name
                shutil.copytree(RUNTIME, dest)
                self.assertEqual((dest / "checkerboard.tga").read_bytes(), (RUNTIME / "checkerboard.tga").read_bytes())
                self.assertTrue((dest / "LICENSE").is_file())
                for locale in ("enUS", "koKR"):
                    for separator in ("/", "\\"):
                        lua = LuaRuntime()
                        lua.execute('''
                            lib={}; table.freeze=function(t) return t end
                            local loaded=false
                            LibStub={NewLibrary=function(_, _, minor) if loaded then return nil end loaded=true; loadedMinor=minor; return lib end}
                            function debugstack() return mockPath end
                            function GetLocale() return mockLocale end
                        ''')
                        lua.globals().mockLocale = locale
                        path = str(dest.relative_to(root)).replace("\\", separator).replace("/", separator) + separator
                        lua.globals().mockPath = path + "LibOrbitColorPicker-1.0.lua:1"
                        source = (dest / "LibOrbitColorPicker-1.0.lua").read_text(encoding="utf-8")
                        lua.execute(source)
                        self.assertEqual(lua.globals().loadedMinor, 11)
                        self.assertEqual(lua.eval("lib:GetCheckerboardTexture()"), path + "checkerboard.tga")
                        lua.globals().mockPath = "Interface/AddOns/Later/Libs/LibOrbitColorPicker-1.0/file.lua:1"
                        lua.execute(source)
                        self.assertEqual(lua.eval("lib:GetCheckerboardTexture()"), path + "checkerboard.tga")

    def test_class_pins_use_the_native_class_atlas(self):
        lua = LuaRuntime()
        lua.execute('''
            local function noOp() end
            local objectMethods = {}
            function objectMethods:SetSize() end
            function objectMethods:SetPoint() end
            function objectMethods:SetAllPoints() end
            function objectMethods:SetTexture() end
            function objectMethods:SetColorTexture(r, g, b, a) self.color = {r, g, b, a} end
            function objectMethods:SetAtlas(atlas) self.atlas = atlas end
            function objectMethods:SetAlpha() end
            function objectMethods:Hide() self.shown = false end
            function objectMethods:Show() self.shown = true end
            function objectMethods:ClearAllPoints() end
            function objectMethods:GetEffectiveScale() return 1 end
            function objectMethods:GetLeft() return 0 end
            function objectMethods:GetWidth() return 100 end
            function objectMethods:CreateTexture()
                return setmetatable({shown = true}, {__index = objectMethods})
            end
            function NewObject()
                return setmetatable({shown = true}, {__index = function(self, key)
                    return objectMethods[key] or noOp
                end})
            end

            lib={}; table.freeze=function(t) return t end
            LibStub={NewLibrary=function(_, _, minor) loadedMinor=minor; return lib end}
            function debugstack() return "Interface/AddOns/Test/LibOrbitColorPicker-1.0/LibOrbitColorPicker-1.0.lua:1" end
            function GetLocale() return "enUS" end
            function UnitClass() return "Mage", "MAGE" end
            function issecretvalue() return false end
            function GetClassAtlas(class) return "classicon-" .. class end
            function CreateFrame() return NewObject() end
            function GetCursorPosition() return 50, 50 end
        ''')
        source = (RUNTIME / "LibOrbitColorPicker-1.0.lua").read_text(encoding="utf-8")
        lua.execute(source)
        lua.execute('''
            local gradientBar = NewObject()
            gradientBar.PinsContainer = NewObject()
            gradientBar.SegmentContainer = NewObject()
            lib.ui.gradientBar = gradientBar
            lib.drag.color = {r = 0.2, g = 0.4, b = 0.6, a = 1}
            lib.drag.type = "class"
            lib:ShowGhostPin()
            classAtlas = lib.ui.ghostPin.ClassIcon.atlas
            classIconShown = lib.ui.ghostPin.ClassIcon.shown
            classColorShown = lib.ui.ghostPin.Circle.shown
            lib.drag.type = nil
            lib:ShowGhostPin()
            plainIconShown = lib.ui.ghostPin.ClassIcon.shown
            plainColorShown = lib.ui.ghostPin.Circle.shown
        ''')
        self.assertEqual(lua.globals().loadedMinor, 11)
        self.assertEqual(lua.globals().classAtlas, "classicon-MAGE")
        self.assertTrue(lua.globals().classIconShown)
        self.assertFalse(lua.globals().classColorShown)
        self.assertFalse(lua.globals().plainIconShown)
        self.assertTrue(lua.globals().plainColorShown)


if __name__ == "__main__":
    unittest.main()
