"""Exercise native settings chrome and its missing-atlas fallback without replacing the window design."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"


class ChromeAssets(unittest.TestCase):
    def test_native_and_missing_atlas(self):
        for available in (True, False):
            with self.subTest(available=available):
                lua = LuaRuntime()
                lua.execute('''
                    addon={LibOrbitUI={}}
                    table.freeze=function(t) return t end
                    function Mixin(t,m) for k,v in pairs(m) do t[k]=v end return t end
                    background={SetAtlas=function(self,a) self.atlas=a end,
                        SetColorTexture=function(self,...) self.color={...} end, SetAllPoints=function() end}
                    frame={CreateTexture=function() return background end}
                ''')
                lua.globals().available = available
                lua.execute('C_Texture={GetAtlasInfo=function() return available and {} end}')
                lua.execute('return function(...) ' + (RUNTIME / "Config/Dialogs/DialogChrome.lua").read_text() + '\nend')("Host", lua.globals().addon)
                lua.execute('''
                    local chrome=addon.LibOrbitUI.DialogChrome:Create({r=.1,g=.2,b=.3,a=.9})
                    local result=chrome:ApplyChrome(frame)
                    assert(result.Background==background)
                    if available then assert(background.atlas=="housing-basic-container" and not background.color)
                    else assert(not background.atlas and background.color[4]==.9) end
                ''')


if __name__ == "__main__":
    unittest.main()
