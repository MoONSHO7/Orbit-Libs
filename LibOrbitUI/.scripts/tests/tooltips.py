"""Exercise private tooltip styling, borrowing and embed-owned mouse artwork in Lua 5.1."""
from pathlib import Path
import hashlib
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
HARNESS = r'''
table.freeze = function(value) return value end
SHIFT_KEY_TEXT = "Shift"
function issecretvalue(value) return value == "secret" end
function debugstack() return embeddedPath end
function CreateSimpleTextureMarkup(path, w, h, x, y)
    assert(w == 18 and h == 18 and x == 0 and y == -1)
    return "<" .. path .. ">"
end
function Surface()
    local region = {shown = true, hooks = {}, width = 250, scale = 0.9, textures = {}}
    function region:Show() self.shown = true; if self.hooks.OnShow then self.hooks.OnShow(self) end end
    function region:Hide() self.shown = false end
    function region:SetScale(value) self.scale = value end
    function region:GetEffectiveScale() return self.scale end
    function region:SetClampedToScreen(value) self.clamped = value end
    function region:SetAllPoints(value) self.parent = value end
    function region:SetColorTexture(...) self.color = {...} end
    function region:SetPoint(...) self.point = {...} end
    function region:SetWidth(value) self.width = value end
    function region:SetHeight(value) self.height = value end
    function region:GetWidth() return self.width end
    function region:HookScript(event, callback) self.hooks[event] = callback end
    function region:CreateTexture()
        local texture = Surface(); table.insert(self.textures, texture); return texture
    end
    return region
end
UIParent = Surface()
GameTooltip = Surface()
function CreateFrame(kind, name, parent, template)
    assert(kind == "GameTooltip" and parent == UIParent and template == "GameTooltipTemplate")
    local frame = Surface(); frame.NineSlice = Surface(); _G[name] = frame; return frame
end
pixel = {Multiple = function(_, size, scale) return size / scale end, Destroy = function() error("borrowed pixel") end}
'''


class Tooltips(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute(HARNESS)
        self.first = self.embedding("First")

    def embedding(self, name):
        self.lua.globals().embeddedPath = f"Interface/AddOns/{name}/Libs/LibOrbitUI-1.0/Rendering/TooltipClick.lua:1"
        addon = self.lua.table()
        for relative in ("Core/Bootstrap.lua", "Rendering/TooltipClick.lua", "Rendering/Tooltip.lua", "Core/Context.lua"):
            self.lua.execute("return assert(loadstring(...))", (RUNTIME / relative).read_text())("Consumer", addon)
        self.lua.globals().UI = addon.LibOrbitUI
        self.lua.execute("UI.Runtime={Create=function() return {Destroy=function() end} end}")
        return addon

    def test_private_tooltip_preserves_native_anchor_and_uses_flat_pixel_border(self):
        self.lua.execute('''
            local tip = UI.Tooltip:Create("Private", pixel)
            assert(tip.clamped and tip.scale == 0.9 and tip.SetOwner == nil)
            tip:Show()
            assert(not tip.NineSlice.shown and #tip.textures == 5)
            assert(tip.textures[1].color[4] == 0.75)
            assert(tip.textures[2].height == 2 / 0.9)
            assert(GameTooltip.shown and #GameTooltip.textures == 0 and not next(GameTooltip.hooks))
        ''')

    def test_restricted_geometry_restores_native_chrome_without_geometry_arithmetic(self):
        self.lua.execute('''
            local tip = UI.Tooltip:Create("Restricted", pixel); tip:Show()
            tip.width = "secret"; tip:Show()
            assert(tip.NineSlice.shown)
            for _, texture in ipairs(tip.textures) do assert(not texture.shown) end
            tip.width = 250; tip.scale = "secret"; tip:Show()
            assert(tip.NineSlice.shown)
            tip.scale = 0.9; tip:Show(); assert(not tip.NineSlice.shown)
            assert(tip.textures[1].shown and #tip.textures == 5)
        ''')

    def test_borrowed_tooltip_retains_host_style_and_ownership(self):
        self.lua.execute('''
            local borrowed = Surface()
            local context = UI.CreateContext({name="Borrowed",owner={},pixel=pixel,
                tooltip=borrowed,tooltipHide=function() borrowed:Hide() end})
            context:Destroy(); context:Destroy()
            assert(borrowed.shown and not next(borrowed.hooks) and #borrowed.textures == 0)
        ''')

    def test_owned_context_shuts_down_its_tooltip(self):
        self.lua.execute('''
            local context = UI.CreateContext({name="Owned",owner={},pixel=pixel})
            context.tooltip:Show(); context:Destroy()
            assert(not context.tooltip.shown)
        ''')

    def test_mouse_art_stays_with_each_embedding_and_localized_modifiers(self):
        first = self.first.LibOrbitUI.TooltipClick.Create(self.first.LibOrbitUI.TooltipClick)
        other = self.embedding("Second")
        second = other.LibOrbitUI.TooltipClick.Create(other.LibOrbitUI.TooltipClick)
        self.assertIn("AddOns/First/Libs/", first.Left(first, "Action"))
        self.assertIn("AddOns/Second/Libs/", second.Right(second, "Action"))
        self.lua.execute('''
            local labels={left="Left",right="Right",shift="Shift click",control="Strg"}
            local clicks=UI.TooltipClick:Create(function(key) return labels[key] end)
            assert(clicks:Left("Left")==clicks:Left())
            assert(clicks:Right("Right")==clicks:Right())
            assert(clicks:Left("Shift click")=="Shift + "..clicks:Left())
            assert(clicks:ControlScroll("Zoom")=="Strg + "..clicks:Middle("Zoom"))
            labels.left="Gauche"; assert(clicks:Left("Gauche")==clicks:Left())
        ''')

    def test_moved_art_preserves_original_bytes(self):
        hashes = {
            "left": "aadfa250ae4ecf04d10c841e5d0aa5fa0ea605755754771de92919417e1327d9",
            "middle": "e1abf167884110dbe68c549e5dd0147c4dd1117029dedb501b443f8c63ba5a93",
            "right": "559698a306f261c91b91a70af600bea154d7dc53e688aa0a31229504430ae408",
        }
        for button, expected in hashes.items():
            moved = (RUNTIME / f"Rendering/Assets/orbit-click-{button}.tga").read_bytes()
            self.assertEqual(hashlib.sha256(moved).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
