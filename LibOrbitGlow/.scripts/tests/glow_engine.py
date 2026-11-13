"""Exercise LibOrbitGlow's registries, flipbook/button engines, proc lifecycle and status-bar resolver in Lua 5.1."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitGlow-1.0"
LIB_PATH = "Interface\\AddOns\\Host\\Libs\\LibOrbitGlow-1.0\\"
TRACER = LIB_PATH + "Textures\\dispel-tracer-25.tga"

# Widget double: Blizzard's Pools.lua contract (reset on create, inactive release is an assertsafe fault) on both
# branches; regions record anchors, tint, art and animation state so assertions read behaviour, not source.
HARNESS = r'''
faults, messages, created = {}, {}, { frames = 0, textures = 0 }
missingTextures, atlasInfo = {}, {
    ["UI-HUD-ActionBar-Proc-Loop-Flipbook"] = { flipBookRows = 6, flipBookColumns = 5, flipBookFrames = 30 },
    ["RotationHelper_Ants_Flipbook_2x"] = { flipBookRows = 8, flipBookColumns = 4, flipBookFrames = 32 },
    ["RotationHelper-ProcLoopBlue-Flipbook-2x"] = { flipBookRows = 4, flipBookColumns = 4, flipBookFrames = 16 },
}
table.wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
wipe = table.wipe
tinsert = table.insert
function issecretvalue(value) return type(value) == "table" and rawget(value, "secret") == true end
function debugstack() return "Interface\\AddOns\\Host\\Libs\\LibOrbitGlow-1.0\\LibOrbitGlow-1.0.lua:32: in main chunk" end
DEFAULT_CHAT_FRAME = { AddMessage = function(_, text) messages[#messages + 1] = text end }

local libs, minors = {}, {}
LibStub = setmetatable({
    NewLibrary = function(_, major, minor)
        if minors[major] and minors[major] >= minor then return nil end
        minors[major] = minor
        libs[major] = libs[major] or {}
        return libs[major]
    end,
}, { __call = function(_, major) return libs[major] end })

local Animation = {}
Animation.__index = Animation
for _, field in ipairs({ "Order", "Duration", "FlipBookRows", "FlipBookColumns", "FlipBookFrames", "FlipBookFrameWidth",
    "FlipBookFrameHeight", "ChildKey", "StartDelay", "FromAlpha", "ToAlpha" }) do
    Animation["Set" .. field] = function(self, value) self[field] = value end
end
function Animation:SetScale(x, y) self.scaleX, self.scaleY = x, y end

local Group = {}
Group.__index = Group
function Group:CreateAnimation(kind)
    local animation = setmetatable({ kind = kind }, Animation)
    self.animations[#self.animations + 1] = animation
    return animation
end
function Group:SetLooping(mode) self.looping = mode end
function Group:SetScript(name, handler) self.scripts[name] = handler end
function Group:GetScript(name) return self.scripts[name] end
function Group:GetParent() return self.parent end
function Group:IsPlaying() return self.playing end
function Group:Play()
    self.playing, self.plays = true, self.plays + 1
    if self.scripts.OnPlay then self.scripts.OnPlay(self) end
end
function Group:Stop()
    local was = self.playing
    self.playing = false
    if was and self.scripts.OnStop then self.scripts.OnStop(self) end
end
function Group:Finish()
    self.playing = false
    if self.scripts.OnFinished then self.scripts.OnFinished(self) end
end

local Region = {}
Region.__index = Region
function NewRegion(kind, parent)
    local region = setmetatable({ kind = kind, parent = parent, shown = true, points = {}, scripts = {}, level = 0,
        width = 40, height = 20, groups = {} }, Region)
    return region
end
function Region:SetPoint(point, relative, relativePoint, x, y)
    self.points[point] = { relative = relative, relativePoint = relativePoint, x = x or 0, y = y or 0 }
end
function Region:ClearAllPoints() self.points = {} end
function Region:SetAllPoints(target) self.allPoints = target or self.parent end
function Region:GetWidth() return self.width end
function Region:GetHeight() return self.height end
function Region:GetSize() return self.width, self.height end
function Region:SetSize(w, h) self.width, self.height = w, h end
function Region:Show() self.shown = true end
function Region:Hide()
    local was = self.shown
    self.shown = false
    if was and self.scripts.OnHide then self.scripts.OnHide(self) end
end
function Region:IsShown()
    if self.secretShown then error("secret Shown aspect read") end
    return self.shown
end
function Region:IsVisible()
    local region = self
    while region do
        if not region.shown then return false end
        region = region.parent
    end
    return true
end
function Region:SetParent(parent) self.parent = parent end
function Region:GetParent() return self.parent end
function Region:SetFrameLevel(level) self.level = level end
function Region:GetFrameLevel() return self.level end
function Region:SetScript(name, handler) self.scripts[name] = handler end
function Region:GetScript(name) return self.scripts[name] end
function Region:SetAlpha(alpha) self.alpha = alpha end
function Region:CreateAnimationGroup()
    local group = setmetatable({ parent = self, animations = {}, scripts = {}, playing = false, plays = 0 }, Group)
    self.groups[#self.groups + 1] = group
    return group
end
function Region:CreateTexture(_, layer, _, sublevel)
    created.textures = created.textures + 1
    local texture = NewRegion("Texture", self)
    texture.layer, texture.sublevel = layer, sublevel
    return texture
end
function Region:SetTexture(path)
    self.texture, self.atlas = path, nil
    if path ~= nil and missingTextures[path] then return false end
    return true
end
function Region:SetAtlas(atlas) self.atlas, self.texture = atlas, nil end
function Region:SetTexCoord(...) self.texCoord = { ... } end
function Region:SetDesaturated(value) self.desaturated = value end
function Region:SetVertexColor(r, g, b, a) self.color = { r, g, b, a } end
function Region:SetBlendMode(mode) self.blend = mode end
function Region:SetDrawLayer(layer, sublevel) self.layer, self.sublevel = layer, sublevel end

function CreateFrame(_, _, parent)
    created.frames = created.frames + 1
    return NewRegion("Frame", parent)
end
UIParent = NewRegion("Frame")
UIParent.width, UIParent.height = 1920, 1080

local function Pool(create, resetter)
    local pool = { active = {}, inactive = {} }
    function pool:Acquire()
        local object = table.remove(self.inactive)
        local new = object == nil
        if new then
            object = create()
            if resetter then resetter(self, object, true) end
        end
        self.active[object] = true
        return object, new
    end
    function pool:Release(object)
        if not self.active[object] then
            faults[#faults + 1] = "released inactive object"
            return false
        end
        if resetter then resetter(self, object, false) end
        self.active[object] = nil
        self.inactive[#self.inactive + 1] = object
        return true
    end
    function pool:GetNumActive()
        local count = 0
        for _ in pairs(self.active) do count = count + 1 end
        return count
    end
    pools[#pools + 1] = pool
    return pool
end
pools = {}
function CreateFramePool(kind, parent, _, resetter) return Pool(function() return CreateFrame(kind, nil, parent) end, resetter) end
function CreateTexturePool(parent, layer, sublevel, _, resetter)
    return Pool(function() return parent:CreateTexture(nil, layer, nil, sublevel) end, resetter)
end
C_Texture = { GetAtlasInfo = function(atlas) return atlasInfo[atlas] end }

function Host(width, height)
    local host = CreateFrame("Frame", nil, UIParent)
    host.width, host.height, host.level = width or 40, height or 20, 10
    return host
end
function Plays(frame)
    local total = 0
    for _, texture in ipairs(frame.textures) do total = total + texture.animGroup.plays end
    return total
end
'''


def load(lua=None, preload=""):
    lua = lua or LuaRuntime()
    if preload is not None:
        lua.execute(HARNESS)
        lua.execute(preload)
    for name in ("LibOrbitGlow-1.0.lua", "StatusBarGlows.lua"):
        lua.execute((RUNTIME / name).read_text(encoding="utf-8"))
    lua.execute('lib = LibStub("LibOrbitGlow-1.0")')
    return lua


class GlowTestCase(unittest.TestCase):
    def setUp(self):
        self.lua = load()

    def run_lua(self, code):
        return self.lua.execute(code)

    def eval(self, expression):
        return self.lua.eval(expression)

    def tearDown(self):
        self.assertEqual(self.eval("#faults"), 0, "a pool released an inactive object")

    def assertSame(self, left, right):
        self.assertTrue(self.eval(f"rawequal({left}, {right})"), f"{left} is not {right}")

    def assertNear(self, expression, expected):
        self.assertAlmostEqual(self.eval(expression), expected, places=6)


class Registry(GlowTestCase):
    def test_baseline_glows_register_sorted(self):
        self.assertEqual(list(self.eval("lib:GetGlowList()").values()),
                         ["blizzard", "blizzardants", "blizzardblue", "classic"])
        self.assertEqual(self.eval("lib.minorVersion"), 14)
        self.assertEqual(self.eval("lib:GetGlowInfo('classic').engine"), "Classic")

    def test_invalid_definitions_are_refused_without_registering(self):
        for call in ("lib:RegisterGlow(7, { atlas = 'x' })", "lib:RegisterGlow('bad', 'x')",
                     "lib:RegisterGlow('bad', { engine = 'Pixel' })", "lib:RegisterGlow('bad', { engine = 'Autocast' })",
                     "lib:RegisterGlow('bad', { source = 'Pack' })"):
            self.assertIs(self.eval(call), False, call)
        self.assertFalse(self.eval("lib:IsGlowRegistered('bad')"))
        self.assertEqual(self.eval("#messages"), 1)
        self.assertIn('RegisterGlow("bad") ignored', self.eval("messages[1]"))

    def test_every_engine_type_and_art_source_registers(self):
        for engine in ("Classic", "Thin", "Thick", "Medium"):
            self.assertIs(self.eval(f"lib:RegisterGlow('e{engine}', {{ engine = '{engine}' }})"), True)
        for field in ("path = 'P'", "resolve = function() end", "atlas = 'A'"):
            self.assertIs(self.eval(f"lib:RegisterGlow('art', {{ {field}, source = 'Pack' }})"), True)
        self.assertEqual(self.eval("#messages"), 0)

    def test_registration_fills_defaults_and_loop_only_phases(self):
        self.run_lua("lib:RegisterGlow('plain', { path = 'P' }); lib:RegisterGlow('looper', { path = 'L', loopOnly = true })")
        self.run_lua("lib:RegisterGlow('phased', { path = 'Q', loopOnly = true, phases = { start = true } })")
        self.assertIs(self.eval("lib:GetGlowInfo('plain').shapes.square"), True)
        self.assertEqual(self.eval("lib:GetGlowInfo('plain').source"), "Unknown")
        self.assertIsNone(self.eval("lib:GetGlowInfo('plain').phases"))
        self.assertIs(self.eval("lib:GetGlowInfo('looper').phases.loop"), True)
        self.assertIsNone(self.eval("lib:GetGlowInfo('phased').phases.loop"))
        self.run_lua("lib:RegisterGlow('shaped', { path = 'S', shapes = { round = true } })")
        self.assertIsNone(self.eval("lib:GetGlowInfo('shaped').shapes.square"))

    def test_reregistration_warns_only_on_a_source_change(self):
        self.run_lua("lib:RegisterGlow('g', { path = 'A', source = 'One' }); lib:RegisterGlow('g', { path = 'B', source = 'One' })")
        self.assertEqual(self.eval("#messages"), 0)
        self.run_lua("lib:RegisterGlow('g', { path = 'C', source = 'Two' })")
        self.assertEqual(self.eval("#messages"), 1)
        self.assertIn('re-registered by "Two" (was "One")', self.eval("messages[1]"))
        self.assertEqual(self.eval("lib:GetGlowInfo('g').path"), "C")
        self.run_lua("lib:UnregisterGlow('g')")
        self.assertFalse(self.eval("lib:IsGlowRegistered('g')"))
        self.assertNotIn("g", list(self.eval("lib:GetGlowList()").values()))

    def test_upgrade_drops_retired_engines_and_keeps_packs(self):
        lua = LuaRuntime()
        lua.execute(HARNESS)
        lua.execute('''
            local old = LibStub:NewLibrary("LibOrbitGlow-1.0", 9)
            old.glows = { pixel = { engine = "Pixel" }, auto = { engine = "Autocast" }, pack = { path = "P", source = "Pack" } }
        ''')
        load(lua, preload=None)
        names = list(lua.eval("lib:GetGlowList()").values())
        self.assertNotIn("pixel", names)
        self.assertNotIn("auto", names)
        self.assertIn("pack", names)
        lua.execute("revision = lib.statusBarRevision")
        load(lua, preload=None)
        self.assertEqual(lua.eval("lib.statusBarRevision"), lua.eval("revision"))


class Flipbook(GlowTestCase):
    def test_known_atlas_takes_its_native_grid_and_loops(self):
        self.run_lua("host = Host(); lib.Flipbook:Show(host, { key = 'K', color = { 1, 0.5, 0.25, 0.8 } }); f = host._LibGlowFlipbookK")
        self.assertEqual(self.eval("f.textures[1].atlas"), "UI-HUD-ActionBar-Proc-Loop-Flipbook")
        animation = "f.textures[1].flipbookAnim"
        self.assertEqual((self.eval(f"{animation}.FlipBookRows"), self.eval(f"{animation}.FlipBookColumns"),
                          self.eval(f"{animation}.FlipBookFrames")), (6, 5, 30))
        self.assertEqual(self.eval("f.textures[1].animGroup.looping"), "REPEAT")
        self.assertTrue(self.eval("f.textures[1].animGroup.playing"))
        self.assertIs(self.eval("f.textures[1].desaturated"), True)
        self.assertEqual(self.eval("f.textures[1].blend"), "BLEND")
        self.assertEqual(list(self.eval("f.textures[1].color").values()), [1, 0.5, 0.25, 0.8])
        self.assertEqual(self.eval("f.level"), 18)
        self.assertSame("f.parent", "host")

    def test_colour_accepts_mixins_keyed_and_indexed_tables(self):
        self.run_lua('''
            host = Host()
            lib.Flipbook:Show(host, { key = 'm', color = { GetRGBA = function() return 0.1, 0.2, 0.3, 0.4 end } })
            lib.Flipbook:Show(host, { key = 'k', color = { r = 0.5, g = 0.6, b = 0.7 } })
            lib.Flipbook:Show(host, { key = 'i', color = { 0.9 } })
            lib.Flipbook:Show(host, { key = 'n' })
        ''')
        colors = {key: [round(v, 6) for v in self.eval(f"host._LibGlowFlipbook{key}.textures[1].color").values()]
                  for key in "mkin"}
        self.assertEqual(colors, {"m": [0.1, 0.2, 0.3, 0.4], "k": [0.5, 0.6, 0.7, 1], "i": [0.9, 1, 1, 1],
                                  "n": [1, 1, 1, 1]})

    def test_missing_atlas_falls_back_to_the_bundled_tracer_sheet(self):
        self.run_lua("host = Host(); lib.Flipbook:Show(host, { atlas = 'Missing-Atlas' }); f = host._LibGlowFlipbookDefault")
        self.assertEqual(self.eval("f.textures[1].texture"), TRACER)
        self.assertIsNone(self.eval("f.textures[1].atlas"))
        self.assertEqual(self.eval("f.textures[1].flipbookAnim.FlipBookFrames"), 30)
        self.run_lua("lib.Flipbook:Show(host, { atlas = 'Custom', isTexture = true, rows = 2, cols = 3 })")
        self.assertEqual(self.eval("f.textures[1].texture"), "Custom")
        self.assertEqual(self.eval("f.textures[1].flipbookAnim.FlipBookFrames"), 6)

    def test_unchanged_reshow_only_retints_and_reanchors(self):
        self.run_lua('''
            host = Host(); lib.Flipbook:Show(host, { key = 'K', color = { 1, 0, 0, 1 } }); f = host._LibGlowFlipbookK
            plays = Plays(f)
            host.width = 100
            lib.Flipbook:Show(host, { key = 'K', color = { 0, 1, 0, 0.5 } })
        ''')
        self.assertEqual(self.eval("Plays(f)"), self.eval("plays"))
        self.assertEqual(list(self.eval("f.textures[1].color").values()), [0, 1, 0, 0.5])
        self.assertNear("f.points.TOPLEFT.x", -(100 * 0.4 / 2))
        for change in ("speed = 2", "blendMode = 'ADD'", "N = 2", "scale = 2", "offsetScale = 3", "offsetX = 1",
                       "offsetY = 1", "padding = 4", "desaturated = false", "frameLevel = 3", "force = true",
                       "rows = 3", "cols = 2", "frames = 5", "atlas = 'RotationHelper_Ants_Flipbook_2x'"):
            self.run_lua(f"plays = Plays(f); lib.Flipbook:Show(host, {{ key = 'K', {change} }}); lib.Flipbook:Show(host, {{ key = 'K' }})")
            self.assertGreater(self.eval("Plays(f)"), self.eval("plays"), change)

    def test_padded_anchors_use_scale_padding_offsets_and_supplied_host_size(self):
        self.run_lua('''
            host = Host(40, 20)
            lib.Flipbook:Show(host, { key = 'P', scale = 1.4, offsetScale = 1, padding = 2, offsetX = 3, offsetY = -1 })
            f = host._LibGlowFlipbookP
        ''')
        self.assertNear("f.points.TOPLEFT.x", -8)
        self.assertNear("f.points.TOPLEFT.y", 6)
        self.assertNear("f.points.BOTTOMRIGHT.x", 14)
        self.assertNear("f.points.BOTTOMRIGHT.y", -8)
        self.run_lua('''
            secretHost = Host(); secretHost.GetWidth = function() error("secret width read") end
            secretHost.GetHeight = function() error("secret height read") end
            lib.Flipbook:Show(secretHost, { key = 'S', hostWidth = 30, hostHeight = 10, scale = 2 })
        ''')
        self.assertNear("secretHost._LibGlowFlipbookS.points.TOPLEFT.x", -15)
        self.assertNear("secretHost._LibGlowFlipbookS.points.TOPLEFT.y", 5)

    def test_one_shot_hands_finish_to_the_first_layer_only(self):
        self.run_lua('''
            host = Host(); finished = 0
            lib.Flipbook:Show(host, { key = 'O', N = 2, once = true, onFinished = function() finished = finished + 1 end })
            f = host._LibGlowFlipbookO
        ''')
        self.assertEqual(self.eval("f.textures[1].animGroup.looping"), "NONE")
        self.assertIsNotNone(self.eval("f.textures[1].animGroup.scripts.OnFinished"))
        self.assertIsNone(self.eval("f.textures[2].animGroup.scripts.OnFinished"))
        self.run_lua("f.textures[1].animGroup:Finish(); f.textures[2].animGroup:Finish()")
        self.assertEqual(self.eval("finished"), 1)
        self.run_lua("lib.Flipbook:Show(host, { key = 'O', N = 2 })")
        self.assertEqual(self.eval("f.textures[1].animGroup.looping"), "REPEAT")
        self.assertIsNone(self.eval("f.textures[1].animGroup.scripts.OnFinished"))

    def test_shrinking_layer_count_returns_textures_to_the_pool(self):
        self.run_lua("host = Host(); lib.Flipbook:Show(host, { key = 'N', N = 3 }); f = host._LibGlowFlipbookN; extra = f.textures[3]")
        self.run_lua("lib.Flipbook:Show(host, { key = 'N', N = 1 })")
        self.assertEqual(self.eval("#f.textures"), 1)
        self.assertFalse(self.eval("extra.shown"))
        self.assertEqual(self.eval("pools[1]:GetNumActive()"), 1)

    def test_pooled_hide_releases_and_a_later_show_reuses(self):
        self.run_lua("host = Host(); lib.Flipbook:Show(host, { key = 'R' }); first = host._LibGlowFlipbookR; lib.Flipbook:Hide(host, 'R')")
        self.assertIsNone(self.eval("host._LibGlowFlipbookR"))
        self.assertFalse(self.eval("first.shown"))
        self.assertIsNone(self.eval("first:GetScript('OnUpdate')"))
        self.assertEqual(self.eval("pools[2]:GetNumActive()"), 0)
        self.run_lua("frames = created.frames; other = Host(); lib.Flipbook:Show(other, { key = 'R' })")
        self.assertSame("other._LibGlowFlipbookR", "first")
        self.assertEqual(self.eval("created.frames"), self.eval("frames") + 1)
        self.run_lua("lib.Flipbook:Hide(other, 'R'); lib.Flipbook:Hide(other, 'R'); lib.Flipbook:Hide(other, 'Never')")

    def test_owned_glows_park_without_reading_secret_shown_state(self):
        self.run_lua('''
            host = Host(); lib.Flipbook:Show(host, { key = 'W', owned = true }); f = host._LibGlowFlipbookW
            f.secretShown = true
        ''')
        self.assertTrue(self.eval("f.owned"))
        self.assertEqual(self.eval("pools[2]:GetNumActive()"), 0)
        self.run_lua("plays = Plays(f); lib.Flipbook:Show(host, { key = 'W', owned = true })")
        self.assertEqual(self.eval("Plays(f)"), self.eval("plays"))
        self.run_lua("lib.Flipbook:Hide(host, 'W')")
        self.assertSame("host._LibGlowFlipbookW", "f")
        self.assertTrue(self.eval("f.parked"))
        self.assertFalse(self.eval("f.textures[1].animGroup.playing"))
        self.run_lua("plays = Plays(f); lib.Flipbook:Show(host, { key = 'W', owned = true })")
        self.assertGreater(self.eval("Plays(f)"), self.eval("plays"))
        self.assertIsNone(self.eval("f.parked"))
        self.run_lua("lib.Flipbook:Show(host, { key = 'W', owned = true, N = 3 }); lib.Flipbook:Show(host, { key = 'W', owned = true })")
        self.assertEqual(self.eval("#f.textures"), 1)
        self.assertEqual(self.eval("pools[1]:GetNumActive()"), 0)


class Proc(GlowTestCase):
    def setUp(self):
        super().setUp()
        self.run_lua('''
            lib:RegisterGlow("layered", { path = "Pack/Glow", layered = true, shapes = { square = true, round = true },
                rows = 4, cols = 4, frames = 16, source = "Pack" })
            lib:RegisterGlow("single", { path = "Pack/One", source = "Pack", blendMode = "BLEND", ext = ".blp" })
            lib:RegisterGlow("loop", { path = "Pack/Loop", loopOnly = true, layered = true, core = false, source = "Pack" })
            lib:RegisterGlow("resolver", { resolve = function(phase, shape, suffix)
                calls[#calls + 1] = phase .. "|" .. shape .. "|" .. suffix
                if phase == "loop" then return "R-" .. phase .. suffix end
            end, source = "Pack" })
            calls = {}
            host = Host()
        ''')

    def test_layered_start_hands_off_to_loop_with_tinted_core(self):
        self.run_lua("lib.Proc:Start(host, { glow = 'layered', color = { 0.5, 0, 1, 1 }, frameLevel = 2 }); body = host._LibGlowFlipbookproc; core = host['_LibGlowFlipbookproc\\1core']")
        self.assertEqual(self.eval("body.textures[1].texture"), "Pack/Glow-start-square.tga")
        self.assertEqual(self.eval("core.textures[1].texture"), "Pack/Glow-start-square-core.tga")
        self.assertEqual(self.eval("body.textures[1].animGroup.looping"), "NONE")
        self.assertNear("body.textures[1].flipbookAnim.Duration", 0.28)
        self.assertEqual(self.eval("body.textures[1].flipbookAnim.FlipBookFrames"), 16)
        self.assertEqual((self.eval("body.textures[1].blend"), self.eval("core.textures[1].blend")), ("BLEND", "ADD"))
        self.assertEqual((self.eval("body.level"), self.eval("core.level")), (12, 13))
        self.assertEqual([round(v, 6) for v in self.eval("core.textures[1].color").values()], [0.8, 0.6, 1, 1])
        self.assertIs(self.eval("body.textures[1].desaturated"), False)
        self.assertIsNone(self.eval("core.textures[1].animGroup.scripts.OnFinished"))
        self.run_lua("body.textures[1].animGroup:Finish()")
        self.assertEqual(self.eval("body.textures[1].texture"), "Pack/Glow-loop-square.tga")
        self.assertEqual(self.eval("core.textures[1].texture"), "Pack/Glow-loop-square-core.tga")
        self.assertEqual(self.eval("body.textures[1].animGroup.looping"), "REPEAT")
        self.assertNear("body.textures[1].flipbookAnim.Duration", 1.0)

    def test_stop_plays_the_end_phase_then_clears_both_layers(self):
        self.run_lua("lib.Proc:Loop(host, { glow = 'layered', shape = 'round', key = 'k', endDuration = 0.5 })")
        self.assertEqual(self.eval("host._LibGlowFlipbookk.textures[1].texture"), "Pack/Glow-loop-round.tga")
        self.run_lua("lib.Proc:Stop(host, { glow = 'layered', shape = 'round', key = 'k', endDuration = 0.5 }); body = host._LibGlowFlipbookk")
        self.assertEqual(self.eval("body.textures[1].texture"), "Pack/Glow-end-round.tga")
        self.assertNear("body.textures[1].flipbookAnim.Duration", 0.5)
        self.run_lua("body.textures[1].animGroup:Finish()")
        self.assertIsNone(self.eval("host._LibGlowFlipbookk"))
        self.assertIsNone(self.eval("host['_LibGlowFlipbookk\\1core']"))

    def test_loop_only_glows_skip_start_and_end_and_draw_one_layer(self):
        self.run_lua("lib.Proc:Start(host, { glow = 'loop' })")
        self.assertEqual(self.eval("host._LibGlowFlipbookproc.textures[1].texture"), "Pack/Loop-loop-square.tga")
        self.assertIsNone(self.eval("host['_LibGlowFlipbookproc\\1core']"))
        self.run_lua("lib.Proc:Stop(host, { glow = 'loop' })")
        self.assertIsNone(self.eval("host._LibGlowFlipbookproc"))

    def test_single_layer_uses_its_blend_and_extension(self):
        self.run_lua("lib.Proc:Loop(host, { glow = 'single', color = { 0, 1, 0, 1 } })")
        self.assertEqual(self.eval("host._LibGlowFlipbookproc.textures[1].texture"), "Pack/One-loop-square.blp")
        self.assertEqual(self.eval("host._LibGlowFlipbookproc.textures[1].blend"), "BLEND")
        self.assertEqual(list(self.eval("host._LibGlowFlipbookproc.textures[1].color").values()), [0, 1, 0, 1])

    def test_resolver_decides_which_phases_exist(self):
        self.run_lua("lib.Proc:Start(host, { glow = 'resolver' })")
        self.assertEqual(self.eval("host._LibGlowFlipbookproc.textures[1].texture"), "R-loop")
        self.assertEqual(self.eval("host._LibGlowFlipbookproc.textures[1].animGroup.looping"), "REPEAT")
        self.assertIn("start|square|", list(self.eval("calls").values()))

    def test_unknown_or_atlas_glows_use_the_flipbook_atlas_path(self):
        self.run_lua("lib.Proc:Start(host, { glow = 'nope', key = 'u' })")
        self.assertEqual(self.eval("host._LibGlowFlipbooku.textures[1].atlas"), "UI-HUD-ActionBar-Proc-Loop-Flipbook")
        self.assertEqual(self.eval("host._LibGlowFlipbooku.textures[1].blend"), "ADD")
        self.run_lua("lib.Proc:Stop(host, { glow = 'nope', key = 'u' })")
        self.assertIsNone(self.eval("host._LibGlowFlipbooku"))
        self.run_lua('''
            lib:RegisterGlow("soft", { atlas = "RotationHelper_Ants_Flipbook_2x", blendMode = "BLEND", desaturated = false })
            lib.Proc:Loop(host, { glow = "soft", key = "s" })
        ''')
        self.assertEqual(self.eval("host._LibGlowFlipbooks.textures[1].blend"), "BLEND")
        self.assertIs(self.eval("host._LibGlowFlipbooks.textures[1].desaturated"), False)
        self.run_lua("lib.defaultGlow = 'gone'; lib.Proc:Start(host, { glow = 'nope', key = 'v' })")
        self.assertIsNone(self.eval("host._LibGlowFlipbookv"))

    def test_engine_glows_merge_pack_options_without_overriding_the_caller(self):
        self.run_lua('''
            lib:RegisterGlow("thinpack", { engine = "Thin", options = { scale = 3, atlas = "RotationHelper-ProcLoopBlue-Flipbook-2x" } })
            lib.Proc:Start(host, { glow = "thinpack", key = "e", scale = 2 })
            f = host._LibGlowFlipbooke
        ''')
        self.assertEqual(self.eval("f.textures[1].atlas"), "RotationHelper-ProcLoopBlue-Flipbook-2x")
        self.assertNear("f.points.TOPLEFT.x", -(4 + 40 * 1 / 2))
        self.run_lua("lib.Proc:Clear(host, { glow = 'thinpack', key = 'e' })")
        self.assertIsNone(self.eval("host._LibGlowFlipbooke"))

    def test_resolved_paths_report_every_phase_and_layer(self):
        self.assertEqual(list(self.eval("lib:GetResolvedPaths('layered', 'round')").values()), [
            "Pack/Glow-start-round.tga", "Pack/Glow-start-round-core.tga", "Pack/Glow-loop-round.tga",
            "Pack/Glow-loop-round-core.tga", "Pack/Glow-end-round.tga", "Pack/Glow-end-round-core.tga"])
        self.assertEqual(list(self.eval("lib:GetResolvedPaths('layered', 'hex')").values())[0], "Pack/Glow-start-square.tga")
        self.assertEqual(list(self.eval("lib:GetResolvedPaths('loop')").values()), ["Pack/Loop-loop-square.tga"])
        self.run_lua("lib:RegisterGlow('flat', { path = 'F', shaped = false, shapes = { round = true } })")
        self.assertEqual(list(self.eval("lib:GetResolvedPaths('flat', 'round')").values())[0], "F-start.tga")
        self.run_lua("lib:RegisterGlow('onlyround', { path = 'O', shapes = { round = true } })")
        self.assertEqual(list(self.eval("lib:GetResolvedPaths('onlyround')").values())[0], "O-start-round.tga")
        self.assertEqual(self.eval("lib:GetResolvedPaths('classic').engine"), "Classic")
        self.assertEqual(self.eval("lib:GetResolvedPaths('blizzard').atlas"), "UI-HUD-ActionBar-Proc-Loop-Flipbook")
        self.assertIsNone(self.eval("lib:GetResolvedPaths('missing')"))


class EngineApi(GlowTestCase):
    def test_engine_types_choose_atlas_and_offset(self):
        for kind, atlas, offset in (("Thin", "RotationHelper_Ants_Flipbook_2x", 4),
                                    ("Thick", "RotationHelper-ProcLoopBlue-Flipbook-2x", 1),
                                    ("Medium", "UI-HUD-ActionBar-Proc-Loop-Flipbook", 1)):
            self.run_lua(f"host = Host(40, 20); lib.Show(host, '{kind}', {{ key = 'x' }}); f = host._LibGlowFlipbookx")
            self.assertEqual(self.eval("f.textures[1].atlas"), atlas)
            self.assertNear("f.points.TOPLEFT.x", -(offset + 40 * 0.4 / 2))
            self.run_lua(f"lib.Hide(host, '{kind}', 'x')")
            self.assertIsNone(self.eval("host._LibGlowFlipbookx"))

    def test_apply_and_remove_route_registered_names_through_the_proc_lifecycle(self):
        self.run_lua('''
            lib:RegisterGlow("pack", { path = "P", source = "Pack" })
            host = Host(); lib.Apply(host, "pack", { key = "a" })
        ''')
        self.assertEqual(self.eval("host._LibGlowFlipbooka.textures[1].texture"), "P-start-square.tga")
        self.run_lua("lib.Apply(host, 'pack', { key = 'a', loop = true })")
        self.assertEqual(self.eval("host._LibGlowFlipbooka.textures[1].texture"), "P-loop-square.tga")
        self.run_lua("lib.Remove(host, 'pack', { key = 'a' })")
        self.assertEqual(self.eval("host._LibGlowFlipbooka.textures[1].texture"), "P-end-square.tga")
        self.run_lua("lib.Apply(host, 'Thin', { key = 'b' }); lib.Remove(host, 'Thin', { key = 'b' })")
        self.assertIsNone(self.eval("host._LibGlowFlipbookb"))

    def test_unknown_types_raise_from_every_entry_point(self):
        for call in ("lib.Show(Host(), 'Pixel')", "lib.Hide(Host(), 'Pixel')", "lib.Apply(Host(), 'Pixel')",
                     "lib.Remove(Host(), 'Pixel')", "lib.PreLoad('Pixel', 1)"):
            with self.assertRaisesRegex(Exception, "Unknown glowType 'Pixel'"):
                self.run_lua(call)

    def test_preload_warms_the_pool_and_leaves_nothing_live(self):
        self.run_lua("lib.PreLoad('Thin', 3); frames = created.frames")
        self.assertEqual(self.eval("pools[2]:GetNumActive()"), 0)
        self.assertEqual(len(self.eval("pools[2].inactive")), 3)
        self.run_lua("for i = 1, 3 do lib.Show(Host(), 'Thin', { key = i }) end")
        self.assertEqual(self.eval("created.frames"), self.eval("frames") + 3)


class Button(GlowTestCase):
    def test_classic_glow_builds_tinted_layers_and_animates_in(self):
        self.run_lua("host = Host(40, 40); lib.Show(host, 'Classic', { key = 'c', color = { 1, 0, 0, 0.5 }, frequency = 0.5 }); f = host._LibGlowButtonc")
        for name in ("spark", "innerGlow", "innerGlowOver", "outerGlow", "outerGlowOver", "ants"):
            self.assertEqual(self.eval(f"f.{name}.desaturated"), 1)
            self.assertEqual(list(self.eval(f"f.{name}.color").values()), [1, 0, 0])
        self.assertTrue(self.eval("f.animIn.playing"))
        self.assertNear("f.throttle", 0.25 / 0.5 * 0.01)
        self.assertEqual((self.eval("f.width"), self.eval("f.height")), (56, 56))
        self.assertNear("f.points.TOPLEFT.x", -8)
        self.assertNear("f.ants.width", 40 * 1.4 * 0.85)
        self.assertNear("f.spark.alpha", 0.3 * 0.5)
        for name in ("innerGlow", "innerGlowOver", "outerGlow", "outerGlowOver"):
            self.assertNear(f"f.{name}.alpha", 0.5)
            self.assertEqual(self.eval(f"f.{name}.texture"), "Interface\\SpellActivationOverlay\\IconAlert")
            self.assertEqual(len(self.eval(f"f.{name}.texCoord")), 4)
        self.assertEqual(self.eval("f.ants.alpha"), 0)
        self.assertEqual(self.eval("f.level"), 18)
        self.run_lua("f.animIn:Finish()")
        self.assertNear("f.ants.alpha", 0.5)
        self.assertEqual(self.eval("f.spark.alpha"), 0)
        self.run_lua("host2 = Host(); lib.Show(host2, 'Classic', { key = 'z', frequency = 0 })")
        self.assertNear("host2._LibGlowButtonz.throttle", 0.01)

    def test_reshow_during_fade_out_keeps_the_frame(self):
        self.run_lua('''
            host = Host(); lib.Show(host, 'Classic', { key = 'c' }); f = host._LibGlowButtonc
            f.animIn:Finish(); lib.Hide(host, 'Classic', 'c')
        ''')
        self.assertTrue(self.eval("f.animOut.playing"))
        self.run_lua("lib.Show(host, 'Classic', { key = 'c', color = { 0, 0, 1, 0.25 } })")
        self.assertFalse(self.eval("f.animOut.playing"))
        self.assertTrue(self.eval("f.animIn.playing"))
        self.assertSame("host._LibGlowButtonc", "f")
        self.assertEqual(list(self.eval("f.ants.color").values()), [0, 0, 1])
        for group, appear, fade in (("animIn", 2, 4), ("animOut", 1, 3)):
            self.assertEqual((len(self.eval(f"f.{group}.appear")), len(self.eval(f"f.{group}.fade"))), (appear, fade))
            for i in range(1, appear + 1):
                self.assertNear(f"f.{group}.appear[{i}].ToAlpha", 0.25)
                self.assertEqual(self.eval(f"f.{group}.appear[{i}].FromAlpha"), 0)
            for i in range(1, fade + 1):
                self.assertNear(f"f.{group}.fade[{i}].FromAlpha", 0.25)
                self.assertEqual(self.eval(f"f.{group}.fade[{i}].ToAlpha"), 0)

    def test_steady_reshow_retints_without_replaying_the_intro(self):
        self.run_lua('''
            host = Host(); lib.Show(host, 'Classic', { key = 'c' }); f = host._LibGlowButtonc; f.animIn:Finish()
            plays = f.animIn.plays
            lib.Show(host, 'Classic', { key = 'c', color = { r = 0, g = 1, b = 0, a = 1 } })
        ''')
        self.assertEqual(self.eval("f.animIn.plays"), self.eval("plays"))
        self.assertFalse(self.eval("f.animIn.playing"))
        self.assertEqual(list(self.eval("f.spark.color").values()), [0, 1, 0])

    def test_hide_releases_by_animation_state_and_visibility(self):
        self.run_lua("host = Host(); lib.Show(host, 'Classic', { key = 'a' }); a = host._LibGlowButtona; lib.Hide(host, 'Classic', 'a')")
        self.assertIsNone(self.eval("host._LibGlowButtona"))
        self.run_lua("lib.Show(host, 'Classic', { key = 'b' }); b = host._LibGlowButtonb; b.animIn:Finish(); lib.Hide(host, 'Classic', 'b')")
        self.assertSame("host._LibGlowButtonb", "b")
        self.run_lua("b.animOut:Finish()")
        self.assertIsNone(self.eval("host._LibGlowButtonb"))
        self.run_lua("lib.Show(host, 'Classic', { key = 'h' }); h = host._LibGlowButtonh; h.animIn:Finish(); host.shown = false; lib.Hide(host, 'Classic', 'h')")
        self.assertIsNone(self.eval("host._LibGlowButtonh"))
        self.run_lua("host.shown = true; lib.Show(host, 'Classic', { key = 'o' }); o = host._LibGlowButtono; o.animIn:Finish(); lib.Hide(host, 'Classic', 'o'); o:Hide()")
        self.assertIsNone(self.eval("host._LibGlowButtono"))

    def test_ant_sheet_steps_frames_and_restarts_on_reuse(self):
        self.run_lua('''
            host = Host(); lib.Show(host, 'Classic', { key = 'c', frequency = 0.25 }); f = host._LibGlowButtonc
            f.scripts.OnUpdate(f, 0.004)
            firstFrame, firstCoord = f.ants.frame, f.ants.texCoord
            seen = {}
            for _ = 1, 400 do
                f.scripts.OnUpdate(f, 0.004)
                if f.ants.frame then seen[f.ants.frame] = f.ants.texCoord end
            end
        ''')
        self.assertEqual(self.eval("firstFrame"), 1)
        self.assertIsNone(self.eval("firstCoord"))
        seen = {int(k): list(v.values()) for k, v in self.eval("seen").items() if v is not None}
        self.assertEqual(set(seen), set(range(1, 23)))
        for frame, (left, right, top, bottom) in seen.items():
            self.assertAlmostEqual(left, ((frame - 1) % 5) * 0.1875)
            self.assertAlmostEqual(right - left, 0.1875)
            self.assertAlmostEqual(bottom, -(-frame // 5) * 0.1875)
            self.assertAlmostEqual(bottom - top, 0.1875)
        self.run_lua("lib.Hide(host, 'Classic', 'c'); other = Host(); lib.Show(other, 'Classic', { key = 'c' })")
        self.assertSame("other._LibGlowButtonc", "f")
        self.assertIsNone(self.eval("f.ants.frame"))

    def test_missing_classic_art_or_owned_hosts_use_the_keyed_fallback(self):
        lua = load(preload="missingTextures['Interface\\\\SpellActivationOverlay\\\\IconAlert'] = true")
        lua.execute("host = Host(); lib.Show(host, 'Classic', { key = 'c' })")
        self.assertIsNone(lua.eval("host._LibGlowButtonc"))
        self.assertEqual(lua.eval("host['_LibGlowFlipbookClassic:c'].textures[1].texture"), TRACER)
        lua.execute("lib.Hide(host, 'Classic', 'c')")
        self.assertIsNone(lua.eval("host['_LibGlowFlipbookClassic:c']"))
        self.assertEqual(lua.eval("#faults"), 0)
        self.run_lua("host = Host(); lib.Show(host, 'Classic', { key = 'w', owned = true, hostWidth = 30, hostHeight = 30 })")
        self.assertTrue(self.eval("host['_LibGlowFlipbookClassic:w'].owned"))
        self.assertIsNone(self.eval("host._LibGlowButtonw"))
        self.run_lua("lib.Hide(host, 'Classic', 'w')")
        self.assertTrue(self.eval("host['_LibGlowFlipbookClassic:w'].parked"))


class StatusBar(GlowTestCase):
    VALID = "{ variants = { { ratio = 2, path = 'V' } } }"

    def register(self, extra):
        return self.eval(f"lib:RegisterStatusBarGlow('t', {{ variants = {{ {{ ratio = 2, path = 'V' }} }}, {extra} }})")

    def test_baselines_and_registry(self):
        self.assertEqual(list(self.eval("lib:GetStatusBarGlowList()").values()), ["pinneon", "tracer"])
        self.assertEqual(self.eval("lib:GetStatusBarGlowInfo('tracer').label"), "Tracer")
        self.assertIs(self.eval("lib:UnregisterStatusBarGlow('tracer')"), False)
        self.assertTrue(self.eval("lib:IsStatusBarGlowRegistered('tracer')"))
        self.run_lua("revision = lib.statusBarRevision")
        self.assertIs(self.eval(f"lib:RegisterStatusBarGlow('added', {self.VALID})"), True)
        self.assertEqual(self.eval("lib.statusBarRevision"), self.eval("revision") + 1)
        self.assertIs(self.eval("lib:RegisterStatusBarGlow('refused', {})"), False)
        self.assertEqual(self.eval("lib.statusBarRevision"), self.eval("revision") + 1)
        self.run_lua("revision = lib.statusBarRevision")
        self.assertIs(self.eval("lib:UnregisterStatusBarGlow('pinneon')"), True)
        self.assertFalse(self.eval("lib:IsStatusBarGlowRegistered('pinneon')"))
        self.assertEqual(self.eval("lib.statusBarRevision"), self.eval("revision") + 1)

    def test_definition_validation_boundaries(self):
        accepted = ("frames = 30, rows = 6, cols = 5", "coreAlpha = 1", "coreAlpha = 0", "overhang = 0", "duration = 0.01",
                    "contours = { round = { kind = 'rounded', radiusFraction = 0.5 } }, shapes = { square = '', round = '-r' }",
                    "contours = { square = { kind = 'square' } }", "bodyBlend = 'ALPHAKEY', coreBlend = 'MOD'")
        for extra in accepted:
            self.assertIs(self.register(extra), True, extra)
        refused = ("frames = 31, rows = 6, cols = 5", "rows = 0", "rows = 1.5", "rows = 0/0", "rows = math.huge",
                   "rows = { secret = true }", "rows = 6.5", "frames = 29.5", "cols = 5.5", "duration = math.huge",
                   "overhang = math.huge", "duration = 0", "duration = -1", "overhang = -0.1", "coreAlpha = 1.01",
                   "coreAlpha = -0.1", "bodyBlend = 'GLOW'", "coreBlend = 'GLOW'", "label = 5", "source = 5", "ext = 5",
                   "shapes = { round = '-r' }", "shapes = { square = '', round = 5 }", "shapes = 'x'",
                   "contours = 'x'", "contours = { secret = true }", "contours = { hex = { kind = 'rounded', radiusFraction = 0.1 } }",
                   "contours = { square = { kind = 'rounded', radiusFraction = 0.1 } }",
                   "contours = { round = { kind = 'rounded', radiusFraction = 0.51 } }, shapes = { square = '', round = '-r' }",
                   "contours = { round = { kind = 'rounded', cutFraction = 0.1 } }, shapes = { square = '', round = '-r' }",
                   "contours = { round = { kind = { secret = true } } }, shapes = { square = '', round = '-r' }")
        for extra in refused:
            self.assertIs(self.register(extra), False, extra)
        for definition in ("{ variants = {} }", "{ variants = 'x' }", "{ variants = { { ratio = 0, path = 'V' } } }",
                           "{ variants = { { ratio = 2, path = '' } } }", "{ variants = { 'x' } }", "{}"):
            self.assertIs(self.eval(f"lib:RegisterStatusBarGlow('t', {definition})"), False, definition)
        self.assertIs(self.eval(f"lib:RegisterStatusBarGlow('', {self.VALID})"), False)
        self.assertIs(self.eval(f"lib:RegisterStatusBarGlow(5, {self.VALID})"), False)

    def test_defaults_and_variant_order_are_kept(self):
        self.run_lua("lib:RegisterStatusBarGlow('m', { variants = { { ratio = 4, path = 'A' }, { ratio = 1, path = 'B' }, { ratio = 8, path = 'C' } } })")
        info = "lib:GetStatusBarGlowInfo('m')"
        self.assertEqual([self.eval(f"{info}.variants[{i}].path") for i in (1, 2, 3)], ["A", "B", "C"])
        self.assertIs(self.eval(f"{info}.core"), True)
        self.assertNear(f"{info}.coreAlpha", 0.85)
        self.assertEqual((self.eval(f"{info}.rows"), self.eval(f"{info}.cols"), self.eval(f"{info}.frames")), (6, 5, 30))
        self.assertEqual((self.eval(f"{info}.label"), self.eval(f"{info}.source"), self.eval(f"{info}.ext")), ("m", "Unknown", ".tga"))
        self.assertEqual(self.eval(f"{info}.shapes.square"), "")
        self.run_lua("lib:RegisterStatusBarGlow('n', { core = false, variants = { { ratio = 1, path = 'N' } } })")
        self.assertIs(self.eval("lib:GetStatusBarGlowInfo('n').core"), False)

    def test_resolve_picks_the_nearest_aspect_and_requested_shape(self):
        base = LIB_PATH + "Textures\\dispel-tracer"
        self.assertEqual(self.eval("(lib.StatusBar:Resolve('tracer', 200, 50))"), base + "-40.tga")
        self.assertEqual(self.eval("(lib.StatusBar:Resolve('tracer', 100, 40))"), base + "-25.tga")
        self.assertEqual(self.eval("(lib.StatusBar:Resolve('tracer', 160, 50))"), base + "-40.tga")
        self.assertEqual(self.eval("(lib.StatusBar:Resolve('tracer', 150, 50))"), base + "-25.tga")
        self.assertEqual(self.eval("(lib.StatusBar:Resolve('missing', 100, 40, 'round'))"), base + "-25-round.tga")
        self.assertEqual(self.eval("(lib.StatusBar:Resolve('tracer', 100, 40, 'hex'))"), base + "-25.tga")
        for args in ("0, 40", "100, 0", "-1, 40", "0/0, 40", "{ secret = true }, 40", "100, 40, 5", "100, 40, { secret = true }"):
            self.assertIsNone(self.eval(f"lib.StatusBar:Resolve('tracer', {args})"), args)

    def test_equally_near_variants_keep_declaration_order(self):
        self.run_lua("lib:RegisterStatusBarGlow('pair', { variants = { { ratio = 1, path = 'Square' }, { ratio = 4, path = 'Wide' } } })")
        self.assertEqual(self.eval("(lib.StatusBar:Resolve('pair', 2, 1))"), "Square.tga")
        self.run_lua("lib:RegisterStatusBarGlow('pair', { variants = { { ratio = 4, path = 'Wide' }, { ratio = 1, path = 'Square' } } })")
        self.assertEqual(self.eval("(lib.StatusBar:Resolve('pair', 2, 1))"), "Wide.tga")

    def test_status_bar_module_loads_only_beside_its_matching_core(self):
        lua = LuaRuntime()
        lua.execute(HARNESS)
        lua.execute('lib = LibStub:NewLibrary("LibOrbitGlow-1.0", 15); lib.minorVersion = 15')
        lua.execute((RUNTIME / "StatusBarGlows.lua").read_text(encoding="utf-8"))
        self.assertIsNone(lua.eval("lib.statusBarGlows"))
        self.assertIsNone(lua.eval("lib.StatusBar"))
        lua.execute("lib.minorVersion = 14")
        lua.execute((RUNTIME / "StatusBarGlows.lua").read_text(encoding="utf-8"))
        self.assertEqual(lua.eval("lib.statusBarMinor"), 14)
        self.assertTrue(lua.eval("lib:IsStatusBarGlowRegistered('tracer')"))

    def test_contours_choose_the_closest_baked_corner(self):
        def shape(contour, width=100, height=40):
            return self.lua.execute(f"local _, _, s = lib.StatusBar:Resolve('tracer', {width}, {height}, nil, {contour}); return s")
        self.assertEqual(shape("{ kind = 'rounded', radius = 5 }"), "soft")
        self.assertEqual(shape("{ kind = 'rounded', radius = 0 }"), "square")
        self.assertEqual(shape("{ kind = 'rounded', radius = 100 }"), "round-large")
        self.assertEqual(shape("{ kind = 'chamfer', cut = 10 }"), "chamfer-large")
        self.assertEqual(shape("{ kind = 'notch', radius = 2.5 }"), "notch-small")
        self.assertEqual(shape("{ kind = 'blade', cut = 7 }"), "blade")
        self.assertEqual(shape("{ kind = 'square' }"), "square")
        self.assertEqual(shape("nil"), "square")
        for contour in ("{ kind = 'hex', radius = 4 }", "{ kind = 'rounded' }", "{ kind = 'rounded', radius = -1 }",
                        "'rounded'", "{ secret = true }", "{ kind = { secret = true } }"):
            self.assertIsNone(shape(contour), contour)

    def test_contour_ties_prefer_the_larger_corner_then_the_lower_name(self):
        self.run_lua('''
            lib:RegisterStatusBarGlow("tie", { variants = { { ratio = 1, path = "T" } },
                shapes = { square = "", a = "-a", b = "-b", small = "-s", large = "-l" },
                contours = { b = { kind = "rounded", radiusFraction = 0.25 }, a = { kind = "rounded", radiusFraction = 0.25 },
                    small = { kind = "chamfer", cutFraction = 0.125 }, large = { kind = "chamfer", cutFraction = 0.375 } } })
        ''')
        resolve = "select(3, lib.StatusBar:Resolve('tie', 64, 64, nil, {}))"
        self.assertEqual(self.eval(resolve.replace("{}", "{ kind = 'rounded', radius = 16 }")), "a")
        self.assertEqual(self.eval(resolve.replace("{}", "{ kind = 'chamfer', cut = 16 }")), "large")
        self.assertEqual(self.eval(resolve.replace("{}", "{ kind = 'chamfer', cut = 15 }")), "small")

    def test_show_builds_body_and_core_layers_and_restarts_only_on_change(self):
        self.run_lua("host = Host(100, 40); state = lib.StatusBar:Show(host, { key = 'k', color = { r = 1, g = 0.5, b = 0 } })")
        self.assertEqual((self.eval("state.body.sublevel"), self.eval("state.core.sublevel")), (5, 6))
        self.assertEqual((self.eval("state.body.blend"), self.eval("state.core.blend")), ("BLEND", "ADD"))
        self.assertEqual((self.eval("state.body.alpha"), self.eval("state.core.alpha")), (1, 0.85))
        self.assertEqual(list(self.eval("state.body.color").values()), [1, 0.5, 0, 1])
        self.assertNear("state.body.points.TOPLEFT.x", -12.5)
        self.assertNear("state.body.points.TOPLEFT.y", 5)
        self.assertNear("state.body.points.BOTTOMRIGHT.x", 12.5)
        self.assertEqual(self.eval("state.bodyLayer.animation.FlipBookFrames"), 30)
        self.assertEqual(self.eval("state.bodyLayer.group.looping"), "REPEAT")
        self.assertEqual(self.eval("state.bodyLayer.group.plays"), 1)
        self.run_lua("lib.StatusBar:Show(host, { key = 'k', color = { 0, 1, 0 } })")
        self.assertEqual(self.eval("state.bodyLayer.group.plays"), 1)
        self.assertEqual(list(self.eval("state.body.color").values()), [0, 1, 0, 1])
        self.run_lua("lib.StatusBar:Show(host, { key = 'k', duration = 2 })")
        self.assertEqual(self.eval("state.bodyLayer.group.plays"), 2)
        self.assertEqual(self.eval("state.bodyLayer.animation.Duration"), 2)
        self.run_lua("lib.StatusBar:Hide(host, 'k')")
        self.assertFalse(self.eval("state.body.shown or state.core.shown"))
        self.run_lua("lib.StatusBar:Show(host, { key = 'k', duration = 2 })")
        self.assertIs(self.eval("state.body.shown and state.core.shown"), True)
        self.assertEqual(self.eval("state.bodyLayer.group.plays"), 3)
        self.assertEqual(self.eval("state.coreLayer.group.plays"), 3)

    def test_core_less_glows_hide_an_existing_core_and_bad_input_draws_nothing(self):
        self.run_lua('''
            lib:RegisterStatusBarGlow("flat", { core = false, variants = { { ratio = 2, path = "F" } } })
            host = Host(100, 50); state = lib.StatusBar:Show(host)
            lib.StatusBar:Show(host, { glow = "flat" })
        ''')
        self.assertFalse(self.eval("state.core.shown"))
        self.assertEqual(self.eval("state.body.texture"), "F.tga")
        self.run_lua("flatHost = Host(100, 50); flat = lib.StatusBar:Show(flatHost, { glow = 'flat' })")
        self.assertIsNone(self.eval("flat.coreLayer"))
        for options in ("{ duration = 0 }", "{ width = 0 }", "{ height = 0/0 }", "{ shape = 5 }"):
            self.assertIsNone(self.eval(f"lib.StatusBar:Show(Host(), {options})"), options)
        self.run_lua("lib.StatusBar:Hide(Host(), 'never'); lib.StatusBar:Hide(host, 'never')")

    def test_secret_colour_channels_pass_through_untouched(self):
        self.run_lua("secret = { secret = true }; state = lib.StatusBar:Show(Host(100, 40), { color = { r = secret } })")
        color = self.eval("state.body.color")
        self.assertSame("state.body.color[1]", "secret")
        self.assertEqual((color[2], color[3], color[4]), (1, 1, 1))
        self.run_lua("state = lib.StatusBar:Show(Host(100, 40), { color = { GetRGBA = function() return 0.1, 0.2, 0.3, 0.4 end } })")
        self.assertEqual([round(v, 6) for v in self.eval("state.body.color").values()], [0.1, 0.2, 0.3, 0.4])


if __name__ == "__main__":
    unittest.main()
