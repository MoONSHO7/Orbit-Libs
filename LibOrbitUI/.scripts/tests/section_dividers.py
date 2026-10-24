"""Execute the shipped divider owners with the real pixel service; native rasterization still needs WoW."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime
from picker_menus import BOOT

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
SOURCES = (
    "Rendering/Pixel.lua", "Config/Config.lua", "Config/Layout.lua", "Config/LayoutControls.lua",
    "Config/LayoutTabs.lua", "Config/Dialogs/ConfigPanel.lua",
)
SCREEN_HEIGHTS = (1080, 1440, 2160)
FRAME_SCALES = (0.5, 0.64, 1.0, 1.25)

HARNESS = r'''
issecretvalue = function() return false end
function GetPhysicalScreenSize() return 2560, physical_height end
function CreateColor(r, g, b, a) return {r = r, g = g, b = b, a = a} end
NORMAL_FONT_COLOR = {GetRGB = function() return 1, 0.82, 0 end}
local BaseFrame = Frame
function Frame(parent, kind, template)
    local frame = BaseFrame(parent, kind, template)
    function frame:SetGradient(orientation, from, to) self.gradient = {orientation, from, to} end
    function frame:GetFont() return "font", 12, "" end
    function frame:GetStringWidth() return #(self.text or "") * 7 end
    function frame:Enable() self.enabled = true end
    function frame:Disable() self.enabled = false end
    function frame:SetHorizontalScroll(value) self.horizontal = value end
    function frame:GetHorizontalScroll() return self.horizontal or 0 end
    function frame:GetHorizontalScrollRange() return 0 end
    return frame
end
'''

SETUP = r'''
local UI = addon.LibOrbitUI
pixel = UI.Pixel:Create()
layout = UI.Layout:Create({pixel = pixel, tooltip = Tooltip, tooltipHide = noop, scrollBar = {}}, UI.Config.Defaults)
layout:RegisterTabsWidgetType()
function Close(actual, expected, label)
    assert(math.abs(actual - expected) < 1e-9, string.format("%s: expected %.12g, got %.12g", label, expected, actual))
end
function OnePixel(frame) return (768 / physical_height) / frame:GetEffectiveScale() end
function Textures(frame)
    local textures = {}
    for _, child in ipairs(state.frames) do
        if child.parent == frame and child.kind == "Texture" then textures[#textures + 1] = child end
    end
    return textures
end
function AssertDivider(divider, r, g, b, label)
    local textures = Textures(divider)
    assert(#textures == 2, label .. ": divider needs two tapered halves")
    for _, texture in ipairs(textures) do
        local _, from, to = unpack(texture.gradient)
        for _, color in ipairs({from, to}) do
            assert(color.r == r and color.g == g and color.b == b, label .. ": divider colour drifted")
        end
        assert(from.a + to.a == 1, label .. ": divider halves must taper from or to transparency")
    end
end
function AssertDefault(divider, label)
    Close(divider:GetHeight(), OnePixel(divider), label .. " height")
    AssertDivider(divider, 0.3, 0.3, 0.3, label)
end
function Parent(scale)
    local frame = Frame(UIParent)
    frame:SetScale(scale)
    return frame
end
function AssertTabReserve(bar, divider, label)
    local reserved = 24 + math.max(1, divider:GetHeight())
    Close(bar._tabScroll:GetHeight(), reserved, label .. " tab scroll")
    Close(bar._tabScroll.Content:GetHeight(), reserved, label .. " tab content")
end
function DisplayEvent(event)
    local listeners = {}
    for _, frame in ipairs(state.frames) do
        if frame.events[event] then table.insert(listeners, 1, frame) end
    end
    for _, frame in ipairs(listeners) do frame:Fire("OnEvent", event) end
end
function FlushTimers()
    local timers = state.timers
    state.timers = {}
    for _, callback in ipairs(timers) do callback() end
end
'''


class SectionDividers(unittest.TestCase):
    def each(self, code):
        for family in ("retail", "forever"):
            for height in SCREEN_HEIGHTS:
                lua = LuaRuntime(unpack_returned_tuples=True)
                lua.execute(BOOT + HARNESS)
                lua.globals().physical_height = height
                lua.execute("addon.LibOrbitUI.Client={family=...}", family)
                for source in SOURCES:
                    lua.execute((RUNTIME / source).read_text(encoding="utf-8"), "Divider", lua.globals().addon)
                lua.execute(SETUP)
                for scale in FRAME_SCALES:
                    with self.subTest(family=family, screen_height=height, frame_scale=scale):
                        lua.globals().scale = scale
                        lua.execute(code)
                        lua.execute("assert(#state.errors == 0)")

    def test_default_divider_is_one_physical_pixel_in_the_shared_colour(self):
        self.each('''
            AssertDefault(layout:CreateTaperedDivider(Parent(scale)), "default")
        ''')

    def test_default_height_resnaps_when_shown_under_another_scale(self):
        self.each('''
            local divider = layout:CreateTaperedDivider(Parent(1))
            divider:Hide(); divider:SetParent(Parent(scale)); divider:Show()
            AssertDefault(divider, "reparented")
        ''')

    def test_explicit_colour_and_logical_height_are_retained(self):
        self.each('''
            local divider = layout:CreateTaperedDivider(Parent(scale), {r = 1, g = 0.5, b = 0}, 3)
            divider:Hide(); divider:SetParent(Parent(scale * 2)); divider:Show()
            assert(divider:GetHeight() == 3, "an explicit logical height was re-snapped")
            AssertDivider(divider, 1, 0.5, 0, "explicit")
        ''')

    def test_section_divider_spans_its_parent_below_the_header_row(self):
        self.each('''
            local parent = Parent(scale)
            for _, case in ipairs({{-40, -58}, {nil, -18}}) do
                local divider = layout:CreateSectionDivider(parent, case[1])
                AssertDefault(divider, "section")
                local left, right = divider.points.TOPLEFT, divider.points.TOPRIGHT
                assert(left[2] == parent and left[3] == "TOPLEFT" and left[4] == 0 and left[5] == case[2])
                assert(right[2] == parent and right[3] == "TOPRIGHT" and right[4] == 0 and right[5] == case[2])
            end
        ''')

    def test_panel_and_tab_dividers_share_the_defaults_and_keep_the_tab_divider_unclipped(self):
        self.each('''
            local dialog = Parent(scale)
            dialog.Title = Frame(dialog)
            local renderer = addon.LibOrbitUI.ConfigPanel:Create(layout.context, layout, addon.LibOrbitUI.Config.Defaults,
                {Attach = noop})
            local panel = renderer:CreateFrame(dialog)
            AssertDefault(panel.HeaderDivider, "panel header")
            local footer = {}
            for _, child in ipairs(state.frames) do
                if child.parent == panel.Footer and #Textures(child) == 2 then footer[#footer + 1] = child end
            end
            assert(#footer == 1, "panel footer needs one divider")
            AssertDefault(footer[1], "panel footer")

            local bar = Parent(scale)
            local _, divider = layout:CreateTabBar(bar, {"General", "Advanced"}, "General", noop)
            AssertDefault(divider, "tab")
            local scroll = bar._tabScroll
            AssertTabReserve(bar, divider, "created")
            assert(divider.points.TOPLEFT[5] == -24, "the tab divider moved below the tab row")
            layout:CreateTabBar(bar, {"General"}, "General", noop, true)
            assert(not divider:IsShown() and scroll:GetHeight() == 25, "an omitted divider kept its reserve")
        ''')

    def test_refresh_resnaps_shown_dividers_and_their_tab_reserve_after_a_scale_change(self):
        self.each('''
            local parent, bar = Parent(1), Parent(1)
            local section = layout:CreateSectionDivider(parent)
            local _, tab = layout:CreateTabBar(bar, {"General", "Advanced"}, "General", noop)
            for _, factor in ipairs({0.5, 3}) do
                parent:SetScale(scale * factor); bar:SetScale(scale * factor)
                assert(math.abs(section:GetHeight() - OnePixel(section)) > 1e-9, "the rescale did not change one pixel")
                layout:RefreshDividerPixels()
                AssertDefault(section, "refreshed section")
                AssertDefault(tab, "refreshed tab")
                AssertTabReserve(bar, tab, "refreshed")
                parent:SetScale(1); bar:SetScale(1)
                layout:RefreshDividerPixels()
            end
        ''')

    def test_display_events_refresh_after_the_pixel_service_updates(self):
        self.each('''
            local parent = Parent(1)
            local section = layout:CreateSectionDivider(parent)
            parent:SetScale(scale * 0.5)
            DisplayEvent("UI_SCALE_CHANGED"); FlushTimers()
            AssertDefault(section, "ui scale event")
            local original = physical_height
            physical_height = original == 1440 and 2160 or 1440
            DisplayEvent("DISPLAY_SIZE_CHANGED"); FlushTimers()
            AssertDefault(section, "display size event")
            physical_height = original
            DisplayEvent("DISPLAY_SIZE_CHANGED"); FlushTimers()
            AssertDefault(section, "restored display")
        ''')

    def test_hidden_dividers_resnap_on_show_and_omitted_tab_dividers_reserve_nothing(self):
        self.each('''
            local parent, bar = Parent(1), Parent(1)
            local section = layout:CreateSectionDivider(parent)
            local _, tab = layout:CreateTabBar(bar, {"General"}, "General", noop)
            section:Hide()
            layout:CreateTabBar(bar, {"General"}, "General", noop, true)
            parent:SetScale(scale * 0.5); bar:SetScale(scale * 0.5)
            layout:RefreshDividerPixels()
            assert(bar._tabScroll:GetHeight() == 25, "a refresh restored an omitted divider's reserve")
            section:Show()
            AssertDefault(section, "shown after refresh")
            layout:CreateTabBar(bar, {"General"}, "General", noop)
            AssertDefault(tab, "restored tab")
            AssertTabReserve(bar, tab, "restored")
        ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
