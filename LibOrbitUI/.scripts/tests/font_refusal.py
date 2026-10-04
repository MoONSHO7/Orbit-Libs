"""Verify refused cold-start font requests cannot overwrite a region's latest font after the client replays them."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"

HARNESS = r'''
addon = {}
table.freeze = function(value) return value end
mock = {now = 0, ready = false, replays = {}, frames = {}, errors = {}}
BACKING = {path = "Fonts/FRIZQT__.TTF", size = 12, flags = ""}
UIParent = {GetEffectiveScale = function() return 1 end}
function GetTime() return mock.now end
function geterrorhandler() return function(err) table.insert(mock.errors, err) end end
function CreateFrame()
    local frame = {scripts = {}}
    function frame:SetScript(event, callback) self.scripts[event] = callback end
    table.insert(mock.frames, frame)
    return frame
end
function CreateFont(name)
    local font = {name = name}
    function font:SetFont(path, size, flags) self.path, self.size, self.flags = path, size, flags end
    function font:SetShadowColor() end
    function font:SetShadowOffset() end
    return font
end
function NewRegion(silentSetFont)
    local region = {color = {1, 1, 1, 1}, justifyH = "LEFT", justifyV = "MIDDLE", shadow = {0, 0, 0, 1}, offset = {1, -1}}
    region.font = {path = BACKING.path, size = BACKING.size, flags = BACKING.flags}
    function region:SetFontObject(object)
        self.fontObject = object
        if type(object) == "table" then
            self.font = {path = object.path, size = object.size, flags = object.flags}
        else
            self.font = {path = BACKING.path, size = BACKING.size, flags = BACKING.flags}
        end
        self.color, self.justifyH, self.justifyV = {1, 0.82, 0, 1}, "CENTER", "MIDDLE"
        self.shadow, self.offset = {0, 0, 0, 1}, {1, -1}
    end
    function region:SetFont(path, size, flags)
        if not mock.ready then
            table.insert(mock.replays, {region = self, path = path, size = size, flags = flags})
            if silentSetFont then return end
            return false
        end
        self.font = {path = path, size = size, flags = flags}
        if silentSetFont then return end
        return true
    end
    function region:GetFont() return self.font.path, self.font.size, self.font.flags end
    function region:GetTextColor() return unpack(self.color) end
    function region:SetTextColor(r, g, b, a) self.color = {r, g, b, a} end
    function region:GetJustifyH() return self.justifyH end
    function region:SetJustifyH(value) self.justifyH = value end
    function region:GetJustifyV() return self.justifyV end
    function region:SetJustifyV(value) self.justifyV = value end
    function region:GetShadowColor() return unpack(self.shadow) end
    function region:SetShadowColor(r, g, b, a) self.shadow = {r, g, b, a} end
    function region:GetShadowOffset() return unpack(self.offset) end
    function region:SetShadowOffset(x, y) self.offset = {x, y} end
    return region
end
-- Once the file loads, the client replays each refused request on a frame before addon OnUpdate scripts run.
function Frame(elapsed)
    mock.now = mock.now + (elapsed or 0.016)
    local replays = mock.ready and mock.replays or {}
    if mock.ready then
        mock.replays = {}
    end
    for _, replay in ipairs(replays) do
        replay.region.font = {path = replay.path, size = replay.size, flags = replay.flags}
    end
    for _, frame in ipairs(mock.frames) do
        if frame.scripts.OnUpdate then frame.scripts.OnUpdate(frame, elapsed or 0.016) end
    end
end
function Updating()
    for _, frame in ipairs(mock.frames) do
        if frame.scripts.OnUpdate then return true end
    end
    return false
end
'''

ORBIT_FONT = "Interface/AddOns/Orbit/Core/assets/Fonts/OrbitSansCondensedUI-ExtraBold.ttf"


class FontRefusal(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute(HARNESS)
        for source in ("Core/Bootstrap.lua", "Core/Callbacks.lua", "Rendering/Text.lua"):
            self.lua.execute("return function(...)\n" + (RUNTIME / source).read_text(encoding="utf-8") + "\nend")(
                "Host", self.lua.globals().addon
            )
        self.lua.globals().ORBIT_FONT = ORBIT_FONT

    def test_latest_request_survives_the_replay_of_a_refused_cold_request(self):
        self.lua.execute('''
            local Text = addon.LibOrbitUI.Text
            local region = NewRegion()
            Text.ApplyFont(region, ORBIT_FONT, 12.6, "OUTLINE")
            assert(region.font.path == BACKING.path and region.font.size == 12)
            mock.ready = true
            Text.ApplyFont(region, ORBIT_FONT, 9.02, "OUTLINE")
            Text.ApplyShadow(region, false)
            region:SetTextColor(0.5, 0.6, 0.7, 0.8)
            region:SetJustifyH("RIGHT")
            assert(region.font.size == 9.02 and Updating())
            Frame()
            assert(region.font.path == ORBIT_FONT and region.font.size == 9.02 and region.font.flags == "OUTLINE")
            assert(region.offset[1] == 0 and region.offset[2] == 0)
            assert(region.color[1] == 0.5 and region.color[4] == 0.8 and region.justifyH == "RIGHT")
            assert(Updating())
            Frame()
            assert(region.font.size == 9.02 and not Updating() and #mock.errors == 0)
        ''')

    def test_refused_request_alone_is_reapplied_once_the_font_loads(self):
        self.lua.execute('''
            local Text = addon.LibOrbitUI.Text
            local region = NewRegion()
            Text.ApplyFont(region, ORBIT_FONT, 9.02, "OUTLINE")
            Frame()
            assert(region.font.path == BACKING.path and Updating())
            mock.ready = true
            Frame()
            Frame()
            assert(region.font.path == ORBIT_FONT and region.font.size == 9.02 and not Updating())
        ''')

    def test_permanently_refused_font_stops_repairing_after_the_timeout(self):
        self.lua.execute('''
            local Text = addon.LibOrbitUI.Text
            local region = NewRegion()
            Text.ApplyFont(region, "Interface/AddOns/Missing/Font.ttf", 10, "")
            Frame()
            assert(Updating())
            Frame(5)
            assert(Updating())
            Frame(6)
            assert(not Updating() and #mock.errors == 0)
        ''')

    def test_accepted_requests_start_no_repair(self):
        self.lua.execute('''
            mock.ready = true
            local Text = addon.LibOrbitUI.Text
            local region = NewRegion()
            Text.ApplyFont(region, ORBIT_FONT, 9.02, "OUTLINE")
            assert(region.font.size == 9.02 and #mock.frames == 0)
            local silent = NewRegion(true)
            mock.ready = false
            Text.ApplyFont(silent, ORBIT_FONT, 9.02, "OUTLINE")
            assert(#mock.frames == 0)
        ''')

    def test_font_object_setter_takes_ownership_from_a_pending_repair(self):
        self.lua.execute('''
            local Text = addon.LibOrbitUI.Text
            local region = NewRegion()
            Text.ApplyFont(region, ORBIT_FONT, 12.6, "OUTLINE")
            mock.ready = true
            local setter = Text.CreateFontSetter({Multiple = function(_, value) return value end}, "Probe", 1, -1)
            setter(region, ORBIT_FONT, 14, "OUTLINE")
            mock.replays = {}
            Frame()
            assert(type(region.fontObject) == "table" and region.font.size == 14 and not Updating())
        ''')


if __name__ == "__main__":
    unittest.main()
