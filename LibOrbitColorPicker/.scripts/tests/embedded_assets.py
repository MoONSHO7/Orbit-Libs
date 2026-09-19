"""Verify the unchanged picker loads from materialized consumer paths and keeps its winning asset owner."""
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
                            LibStub={NewLibrary=function() if loaded then return nil end loaded=true; return lib end}
                            function debugstack() return mockPath end
                            function GetLocale() return mockLocale end
                        ''')
                        lua.globals().mockLocale = locale
                        path = str(dest.relative_to(root)).replace("\\", separator).replace("/", separator) + separator
                        lua.globals().mockPath = path + "LibOrbitColorPicker-1.0.lua:1"
                        source = (dest / "LibOrbitColorPicker-1.0.lua").read_text(encoding="utf-8")
                        lua.execute(source)
                        self.assertEqual(lua.eval("lib:GetCheckerboardTexture()"), path + "checkerboard.tga")
                        lua.globals().mockPath = "Interface/AddOns/Later/Libs/LibOrbitColorPicker-1.0/file.lua:1"
                        lua.execute(source)
                        self.assertEqual(lua.eval("lib:GetCheckerboardTexture()"), path + "checkerboard.tga")


if __name__ == "__main__":
    unittest.main()
