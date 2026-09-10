"""Lua 5.1 contract tests; these do not simulate WoW's renderer or restrictions."""
from pathlib import Path
import unittest
import struct

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "LibOrbitGlow-1.0"

MOCK = r'''
local Object = {}
Object.__index = Object
function NewObject(parent)
    return setmetatable({parent = parent, scripts = {}, points = {}, textures = {}, width = 160, height = 40,
        playCount = 0, stopCount = 0, shown = true, level = 1}, Object)
end
function Object:CreateTexture() local t = NewObject(self); self.textures[#self.textures+1] = t; return t end
function Object:CreateAnimationGroup() self.group = NewObject(self); return self.group end
function Object:CreateAnimation() self.animation = NewObject(self); return self.animation end
function Object:SetScript(key, value) self.scripts[key] = value end
function Object:GetScript(key) return self.scripts[key] end
function Object:Play() self.playing = true; self.playCount = self.playCount + 1 end
function Object:Stop() self.playing = false; self.stopCount = self.stopCount + 1 end
function Object:IsPlaying() return self.playing end
function Object:Show() self.shown = true end
function Object:Hide() self.shown = false end
function Object:IsShown() return self.shown end
function Object:ClearAllPoints() self.points = {} end
function Object:SetPoint(...) self.points[#self.points+1] = {...} end
function Object:SetAllPoints(target) self.allPoints = target end
function Object:SetParent(parent) self.parent = parent end
function Object:GetParent() return self.parent end
function Object:GetWidth() assert(not self.denyGeometry); return self.width end
function Object:GetHeight() assert(not self.denyGeometry); return self.height end
function Object:GetSize() return self:GetWidth(), self:GetHeight() end
function Object:SetSize(w,h) self.width,self.height = w,h end
function Object:SetFrameLevel(level) self.level = level end
function Object:GetFrameLevel() return self.level end
function Object:SetVertexColor(...) self.color = {...} end
function Object:SetTexCoord(...) self.coords = {...} end
for _, entry in ipairs({
    {'SetTexture','path'}, {'SetAtlas','atlas'}, {'SetAlpha','alpha'}, {'SetBlendMode','blend'},
    {'SetLooping','looping'}, {'SetDuration','duration'}, {'SetFlipBookRows','rows'},
    {'SetFlipBookColumns','cols'}, {'SetFlipBookFrames','frames'},
    {'SetFlipBookFrameWidth','frameWidth'}, {'SetFlipBookFrameHeight','frameHeight'},
    {'SetDrawLayer','drawLayer'}, {'SetDesaturated','desaturated'}, {'SetOrder','order'},
    {'SetTarget','target'}, {'SetChildKey','childKey'}, {'SetStartDelay','delay'}, {'SetFromAlpha','from'}, {'SetToAlpha','to'},
    {'SetScale','scale'}, {'SetToScale','toScale'}, {'SetFromScale','fromScale'},
}) do
    local field = entry[2]
    Object[entry[1]] = function(self, value) self[field] = value end
end
function CreateFrame(_, _, parent) return NewObject(parent) end
local function Pool(parent, reset)
    local pool = {free = {}}
    function pool:Acquire()
        local object = table.remove(self.free)
        local fresh = not object
        object = object or NewObject(parent)
        return object, fresh
    end
    function pool:Release(object)
        if reset then reset(self, object) end
        self.free[#self.free+1] = object
    end
    return pool
end
function CreateTexturePool(parent, _, _, _, reset) return Pool(parent, reset) end
function CreateFramePool(_, parent, _, reset) return Pool(parent, reset) end
UIParent = NewObject()
tinsert, tremove = table.insert, table.remove
table.wipe = function(t) for k in pairs(t) do t[k] = nil end end
issecretvalue = function(value) return SECRET_NUMBER ~= nil and value == SECRET_NUMBER end
function debugstack() return 'Interface\\AddOns\\TestHost\\Libs\\LibOrbitGlow-1.0\\StatusBarGlows.lua:1' end
lib = {glows = {pixel = {engine = 'Pixel'}, autocast = {engine = 'Autocast'},
    custom = {path = 'custom', source = 'Test'}}, Pixel = {}, Autocast = {}}
LibStub = setmetatable({minor = 10}, {__call = function() return lib end})
function LibStub:NewLibrary(_, minor)
    if minor <= self.minor then return nil end
    self.minor = minor
    return lib
end
'''


class GlowTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCK)
        for file in ("LibOrbitGlow-1.0.lua", "StatusBarGlows.lua"):
            self.lua.execute((LIB / file).read_text(encoding="utf-8"))

    def test_upgrade_removes_retired_engines_preserves_packs(self):
        self.lua.execute('''
            assert(lib.Pixel == nil and lib.Autocast == nil)
            assert(not lib:IsGlowRegistered('pixel') and not lib:IsGlowRegistered('autocast'))
            assert(lib:IsGlowRegistered('custom'))
            for _, name in ipairs({'Pixel', 'Autocast'}) do
                assert(not pcall(lib.Show, NewObject(), name))
                assert(not lib:RegisterGlow('retired', {engine = name}))
            end
            assert(#lib:GetStatusBarGlowList() == 2)
            assert(not lib:IsGlowRegistered('tracer'))
        ''')

    def test_remaining_icon_engines_show_and_hide(self):
        self.lua.execute('''
            local host = NewObject()
            for _, name in ipairs({'Thin', 'Medium', 'Thick', 'Classic'}) do
                lib.Show(host, name, {key = 'test'})
                lib.Hide(host, name, 'test')
            end
        ''')

    def test_geometry_and_all_baseline_assets(self):
        for name in ("tracer", "pinneon"):
            for width, ratio in ((100, "25"), (160, "40")):
                for shape in ("square", "soft-small", "soft", "soft-large", "softer", "round", "round-large",
                              "chamfer-small", "chamfer", "chamfer-large"):
                    path, definition, resolved_shape = self.lua.eval("function(n,w,s) return lib.StatusBar:Resolve(n,w,40,s) end")(
                        name, width, shape
                    )
                    self.assertEqual(resolved_shape, shape)
                    suffix = "" if shape == "square" else f"-{shape}"
                    filename = f"dispel-{name}-{ratio}{suffix}.tga"
                    self.assertTrue(path.endswith(filename))
                    asset = LIB / "Textures" / filename
                    self.assertTrue(asset.is_file())
                    with asset.open("rb") as stream:
                        header = stream.read(18)
                    sheet_width, sheet_height = struct.unpack_from("<HH", header, 12)
                    self.assertEqual(sheet_width % 5, 0)
                    self.assertEqual(sheet_height % 6, 0)
                    self.assertEqual(definition["frames"], 30)
        self.lua.execute('''
            assert(lib.StatusBar:Resolve('tracer', 0, 40) == nil)
            assert(lib.StatusBar:Resolve('tracer', 160, -1) == nil)
            assert(lib.StatusBar:Resolve('tracer', 0/0, 40) == nil)
            assert(lib.StatusBar:Resolve('tracer', math.huge, 40) == nil)
            SECRET_NUMBER = 123
            assert(lib.StatusBar:Resolve('tracer', SECRET_NUMBER, 40) == nil)
            assert(lib.StatusBar:Resolve('missing', 160, 40, 'missing'):match('tracer%-40.tga$'))
        ''')

    def test_registration_validation_and_copy(self):
        self.lua.execute('''
            local def = {variants = {{ratio = 4, path = 'test'}}, shapes = {square = '', soft = '-soft'},
                rows = 2, cols = 2, frames = 4, duration = 2, core = false, source = 'Test'}
            assert(lib:RegisterStatusBarGlow('custom', def))
            def.variants[1].path = 'changed'
            assert(lib.StatusBar:Resolve('custom', 160, 40, 'soft') == 'test-soft.tga')
            for _, invalid in ipairs({{}, {variants = {}}, {variants = {{ratio = 0, path = 'x'}}},
                {variants = {{ratio = 1, path = 'x'}}, duration = 0},
                {variants = {{ratio = 1, path = 'x'}}, rows = 1, cols = 1, frames = 2},
                {variants = {{ratio = 1, path = 'x'}}, shapes = {soft = '-soft'}}}) do
                assert(not lib:RegisterStatusBarGlow('custom', invalid))
            end
            assert(lib:GetStatusBarGlowInfo('custom').source == 'Test')
            assert(not lib:UnregisterStatusBarGlow('tracer'))
            assert(lib:UnregisterStatusBarGlow('custom'))
            assert(not lib:IsStatusBarGlowRegistered('custom'))
        ''')

    def test_contour_defaults_and_explicit_shape_precedence(self):
        self.lua.execute('''
            local function Shape(shape, contour)
                return select(3, lib.StatusBar:Resolve('tracer', 160, 40, shape, contour))
            end
            assert(Shape() == 'square')
            assert(Shape(nil, {kind = 'square'}) == 'square')
            assert(Shape(nil, {kind = 'rounded', radius = 0}) == 'square')
            assert(Shape(nil, {kind = 'chamfer', cut = 0}) == 'square')
            assert(Shape(nil, {kind = 'rounded', radius = 10}) == 'softer')
            assert(Shape(nil, {kind = 'chamfer', cut = 5}) == 'chamfer')
            assert(Shape('soft', {kind = 'chamfer', cut = 5}) == 'soft')
            assert(Shape('square', {kind = 'rounded', radius = 10}) == 'square')
            assert(Shape('missing', {kind = 'rounded', radius = 10}) == 'square')
            assert(Shape('round', {kind = 'unsupported'}) == 'round')
            assert(lib:RegisterStatusBarGlow('legacy', {variants = {{ratio = 4, path = 'legacy'}},
                shapes = {square = '', hexagon = '-hexagon'}}))
            assert(select(3, lib.StatusBar:Resolve('legacy', 160, 40, 'hexagon', {kind = 'rounded', radius = 8})) == 'hexagon')
            assert(select(3, lib.StatusBar:Resolve('legacy', 160, 40, nil, {kind = 'rounded', radius = 8})) == 'square')
        ''')

    def test_baseline_contours_at_supported_aspects_and_heights(self):
        self.lua.execute('''
            local cases = {
                {20, {kind = 'rounded', radius = 5}, 'softer'},
                {30, {kind = 'rounded', radius = 5}, 'soft-large'},
                {40, {kind = 'rounded', radius = 5}, 'soft'},
                {80, {kind = 'rounded', radius = 5}, 'soft-small'},
                {20, {kind = 'rounded', radius = 10}, 'round-large'},
                {40, {kind = 'rounded', radius = 10}, 'softer'},
                {80, {kind = 'rounded', radius = 10}, 'soft'},
                {30, {kind = 'rounded', radius = 14}, 'round-large'},
                {40, {kind = 'rounded', radius = 14}, 'round'},
                {80, {kind = 'rounded', radius = 14}, 'soft-large'},
                {20, {kind = 'chamfer', cut = 5}, 'chamfer-large'},
                {40, {kind = 'chamfer', cut = 5}, 'chamfer'},
                {80, {kind = 'chamfer', cut = 5}, 'chamfer-small'},
            }
            for _, name in ipairs({'tracer', 'pinneon'}) do
                for _, aspect in ipairs({2.5, 4}) do
                    for _, case in ipairs(cases) do
                        local path, definition, shape = lib.StatusBar:Resolve(name, case[1]*aspect, case[1], nil, case[2])
                        assert(shape == case[3], name .. ':' .. case[1] .. ':' .. shape)
                        assert(definition.shapes[shape] and path:find(definition.shapes[shape], 1, true))
                    end
                end
            end
        ''')

    def test_custom_contours_use_pack_metadata_and_rendered_axes(self):
        self.lua.execute('''
            local def = {variants = {{ratio = 4, path = 'custom'}},
                shapes = {square = '', tight = '-tight', sweep = '-sweep', bevel = '-bevel'},
                contours = {tight = {kind = 'rounded', radiusFraction = 0.125},
                    sweep = {kind = 'rounded', radiusFraction = 0.25}, bevel = {kind = 'chamfer', cutFraction = 0.2}}}
            assert(lib:RegisterStatusBarGlow('custom', def))
            def.contours.tight.radiusFraction = 0.49
            assert(lib:GetStatusBarGlowInfo('custom').contours.tight.radiusFraction == 0.125)
            local function Shape(w, h, contour)
                return select(3, lib.StatusBar:Resolve('custom', w, h, nil, contour))
            end
            assert(Shape(160, 40, {kind = 'rounded', radius = 10}) == 'sweep')
            -- Stretching to twice the sheet aspect doubles only the horizontal radius; tight is closer on both axes.
            assert(Shape(320, 40, {kind = 'rounded', radius = 10}) == 'tight')
            assert(Shape(160, 40, {kind = 'chamfer', cut = 8}) == 'bevel')
            assert(Shape(160, 40, {kind = 'rounded', radius = 0.1}) == 'square')
            assert(Shape(160, 40, {kind = 'rounded', radius = 1000}) == 'sweep')
            def.variants[1].ratio = 0.25
            assert(lib:RegisterStatusBarGlow('portrait', def))
            assert(select(3, lib.StatusBar:Resolve('portrait', 40, 160, nil, {kind = 'rounded', radius = 10})) == 'sweep')
            assert(lib:RegisterStatusBarGlow('cut-only', {variants = {{ratio = 4, path = 'cut'}},
                shapes = {square = '', bevel = '-bevel'}, contours = {bevel = {kind = 'chamfer', cutFraction = 0.2}}}))
            assert(select(3, lib.StatusBar:Resolve('cut-only', 160, 40, nil, {kind = 'rounded', radius = 8})) == 'square')
        ''')

    def test_invalid_contours_do_not_replace_registration_or_change_live_glow(self):
        self.lua.execute('''
            local host = NewObject()
            local state = lib.StatusBar:Show(host, {contour = {kind = 'rounded', radius = 5}})
            local original, revision = lib:GetStatusBarGlowInfo('tracer'), lib.statusBarRevision
            local plays, shape = state.body.group.playCount, state.shape
            for _, invalid in ipairs({{}, false, 'round', {kind = 'unknown'}, {kind = 'rounded'},
                {kind = 'rounded', radius = -1}, {kind = 'rounded', radius = 0/0},
                {kind = 'chamfer', cut = math.huge}}) do
                assert(lib.StatusBar:Show(host, {contour = invalid}) == nil)
                assert(#host.textures == 2 and state.body.group.playCount == plays and state.shape == shape)
            end
            for _, invalid in ipairs({false, {missing = {kind = 'rounded', radiusFraction = 0.2}},
                {square = {kind = 'rounded', radiusFraction = 0.2}}, {soft = {}}, {soft = {kind = 'rounded'}},
                {soft = {kind = 'rounded', radiusFraction = -1}}, {soft = {kind = 'rounded', radiusFraction = 0.6}},
                {soft = {kind = 'chamfer', cutFraction = math.huge}}}) do
                assert(not lib:RegisterStatusBarGlow('tracer', {variants = {{ratio = 4, path = 'invalid'}},
                    shapes = {square = '', soft = '-soft'}, contours = invalid}))
                assert(lib:GetStatusBarGlowInfo('tracer') == original and lib.statusBarRevision == revision)
            end
            SECRET_NUMBER = 123
            assert(lib.StatusBar:Show(host, {contour = {kind = 'rounded', radius = SECRET_NUMBER}}) == nil)
            local contour = {kind = 'chamfer', cut = 5}
            SECRET_NUMBER = contour
            assert(lib.StatusBar:Show(host, {contour = contour}) == nil)
            assert(lib.StatusBar:Show(host, {shape = 'round', contour = contour}) == state)
            SECRET_NUMBER = nil
        ''')

    def test_consumers_keep_masks_and_resize_without_new_objects(self):
        self.lua.execute('''
            assert(Orbit == nil)
            local host, foreignMask = NewObject(), {}
            host.mask = foreignMask
            function host:CreateMaskTexture() error('consumer owns masks') end
            local options = {key = 'external', contour = {kind = 'rounded', radius = 5}, width = 160, height = 40}
            local state = lib.StatusBar:Show(host, options)
            state.body.mask = foreignMask
            function state.body:AddMaskTexture() error('consumer owns masks') end
            function state.body:RemoveMaskTexture() error('consumer owns masks') end
            local plays = state.body.group.playCount
            assert(state.shape == 'soft')
            assert(lib.StatusBar:Show(host, options) == state and state.body.group.playCount == plays)
            options.width, options.height = 320, 80
            assert(lib.StatusBar:Show(host, options) == state and state.shape == 'soft-small')
            assert(#host.textures == 2 and state.body.group.playCount == plays + 1)
            options.contour = nil
            assert(lib.StatusBar:Show(host, options) == state and state.shape == 'square')
            lib.StatusBar:Hide(host, 'external')
            assert(host.mask == foreignMask and state.body.mask == foreignMask)
            assert(not state.body.shown and not state.core.shown)
        ''')

    def test_duplicate_and_older_embeds_preserve_registry_and_namespace(self):
        self.lua.execute('''
            local def = {variants = {{ratio = 4, path = 'custom'}}, shapes = {square = '', own = '-own'},
                contours = {own = {kind = 'rounded', radiusFraction = 0.2}}}
            assert(lib:RegisterStatusBarGlow('consumer', def))
            savedStatusBar = lib.StatusBar
            savedDefinition = lib:GetStatusBarGlowInfo('consumer')
            savedRevision = lib.statusBarRevision
        ''')
        for file in ("LibOrbitGlow-1.0.lua", "StatusBarGlows.lua"):
            self.lua.execute((LIB / file).read_text(encoding="utf-8"))
        self.lua.execute('''
            assert(lib.StatusBar == savedStatusBar and lib:GetStatusBarGlowInfo('consumer') == savedDefinition)
            assert(lib.statusBarRevision == savedRevision)
            LibStub.minor, lib.minorVersion, lib.statusBarMinor = 11, 11, 11
        ''')
        for file in ("LibOrbitGlow-1.0.lua", "StatusBarGlows.lua"):
            self.lua.execute((LIB / file).read_text(encoding="utf-8"))
        self.lua.execute('''
            assert(lib.minorVersion == 12 and lib.statusBarMinor == 12)
            assert(lib.StatusBar == savedStatusBar and lib:GetStatusBarGlowInfo('consumer') == savedDefinition)
            assert(select(3, savedStatusBar:Resolve('consumer', 160, 40, nil, {kind = 'rounded', radius = 8})) == 'own')
            savedRevision = lib.statusBarRevision
        ''')
        older = (LIB / "StatusBarGlows.lua").read_text(encoding="utf-8").replace("local VERSION = 12", "local VERSION = 11", 1)
        self.lua.execute(older)
        self.lua.execute('assert(lib.statusBarMinor == 12 and lib.statusBarRevision == savedRevision)')

    def test_equal_geometry_has_deterministic_shape_selection(self):
        self.lua.execute('''
            local definition = {variants = {{ratio = 4, path = 'ties'}},
                shapes = {square = '', beta = '-beta', alpha = '-alpha', small = '-small'},
                contours = {beta = {kind = 'rounded', radiusFraction = 0.375},
                    alpha = {kind = 'rounded', radiusFraction = 0.375}, small = {kind = 'rounded', radiusFraction = 0.125}}}
            assert(lib:RegisterStatusBarGlow('ties', definition))
            -- A 10-unit request ties between 5 and 15 units; equal larger candidates sort by shape name.
            assert(select(3, lib.StatusBar:Resolve('ties', 160, 40, nil, {kind = 'rounded', radius = 10})) == 'alpha')
        ''')

    def test_mount_reuse_resize_switch_and_cleanup(self):
        self.lua.execute('''
            local host = NewObject()
            host.denyGeometry = true
            local options = {glow = 'tracer', key = 'dispel', width = 160, height = 40, color = {0.2,0.4,0.8,1}}
            local state = lib.StatusBar:Show(host, options)
            assert(state.body:GetParent() == host and state.core:GetParent() == host)
            assert(next(host.scripts) == nil and next(state.body.group.scripts) == nil)
            assert(state.body.points[1][4] == -20 and state.body.points[1][5] == 5)
            local plays = state.body.group.playCount
            assert(lib.StatusBar:Show(host, options) == state)
            assert(state.body.group.playCount == plays and #host.textures == 2)
            options.color = {1,0,0,0.5}
            lib.StatusBar:Show(host, options)
            assert(state.body.color[1] == 1 and state.body.group.playCount == plays)
            options.width = 100
            lib.StatusBar:Show(host, options)
            assert(state.body.path:match('tracer%-25.tga$'))
            assert(state.body.points[1][4] == -12.5)
            options.glow, options.shape = 'pinneon', 'round'
            lib.StatusBar:Show(host, options)
            assert(state.body.path:match('pinneon%-25%-round.tga$'))
            options.shape = 'chamfer'
            lib.StatusBar:Show(host, options)
            assert(state.body.path:match('pinneon%-25%-chamfer.tga$'))
            assert(#host.textures == 2 and state.body.group.playing)
            lib:RegisterStatusBarGlow('single', {variants = {{ratio = 4,path = 'single'}},core = false})
            options.glow = 'single'
            lib.StatusBar:Show(host, options)
            assert(not state.core.shown and not state.core.group.playing)
            lib:UnregisterStatusBarGlow('single')
            lib.StatusBar:Hide(host, 'dispel')
            assert(not state.body.shown and not state.body.group.playing)
            options.glow = 'tracer'
            assert(lib.StatusBar:Show(host, options) == state and #host.textures == 2)
            options.key = 'second'
            local second = lib.StatusBar:Show(host, options)
            lib.StatusBar:Hide(host, 'dispel')
            assert(second.body.shown and second.body.group.playing)
        ''')


if __name__ == "__main__":
    unittest.main()
