"""Execute the shipped dropdown value-warning badge through schema, panel and pool owners; native input needs WoW."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime
from picker_menus import BOOT

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
SOURCES = (
    "Core/Callbacks.lua", "Core/EscapeClose.lua", "Rendering/Pixel.lua", "Config/ConfigSchema.lua",
    "Config/Layout.lua", "Config/LayoutControls.lua", "Config/Widgets/ScrollBar.lua",
    "Config/Widgets/ConfigValueSwatch.lua", "Config/Pickers/MediaMenu.lua", "Config/Pickers/ConfigPickerControl.lua",
    "Config/Widgets/ConfigDropdown.lua", "Config/Dialogs/ConfigPanel.lua",
)
FRAME_SCALES = (0.64, 1.0, 1.25)

HARNESS = r'''
issecretvalue = function() return false end
function GetPhysicalScreenSize() return 2560, 1440 end
function CreateColor(r, g, b, a) return {r = r, g = g, b = b, a = a} end
local BaseFrame = Frame
function Frame(parent, kind, template)
    local frame = BaseFrame(parent, kind, template)
    frame.enabled = true
    frame.mouseClicks = kind == "Button" or kind == "CheckButton"
    function frame:SetEnabled(value)
        value = value and true or false
        if self.enabled ~= value then
            self.enabled = value
            self:Fire(value and "OnEnable" or "OnDisable")
        end
    end
    function frame:Enable() self:SetEnabled(true) end
    function frame:Disable() self:SetEnabled(false) end
    function frame:IsEnabled() return self.enabled end
    function frame:EnableMouse(value) self.mouseClicks, self.mouseMotion = value, value end
    function frame:EnableMouseMotion(value) self.mouseMotion = value end
    function frame:SetMouseClickEnabled(value) self.mouseClicks = value end
    function frame:GetSize() return self.width, self.height end
    function frame:SetAlpha(value) self.alpha = value end
    function frame:SetIgnoreParentAlpha() end
    function frame:SetFrameLevel(value) self.level = value end
    function frame:SetMaxLines() end
    function frame:CanWordWrap() return false end
    function frame:GetObjectType() return self.kind end
    local hide = frame.Hide
    -- Native hides run OnHide for every visible descendant, not only the hidden frame.
    function frame:Hide()
        local descendants = {}
        if self:IsVisible() then
            for _, other in ipairs(state.frames) do
                local parent = other ~= self and other:IsVisible() and other:GetParent()
                while parent and parent ~= self do parent = parent:GetParent() end
                if parent then descendants[#descendants + 1] = other end
            end
        end
        hide(self)
        for _, other in ipairs(descendants) do other:Fire("OnHide") end
    end
    return frame
end
Tooltip = {lines = {}}
function Tooltip:SetOwner(owner, anchor) self.owner, self.anchor, self.title, self.lines = owner, anchor, nil, {} end
function Tooltip:SetText(text, r, g, b) self.title, self.titleColor = text, {r, g, b} end
function Tooltip:AddLine(text, r, g, b, wrap) self.lines[#self.lines + 1] = {text = text, color = r, wrap = wrap} end
function Tooltip:Show() self.shown = true end
function Tooltip:Hide() self.shown = false end
function Tooltip:IsOwned(owner) return self.owner == owner end
function TooltipHide() Tooltip:Hide() end
-- Native dispatch: clicks reach the nearest region with click input enabled, never a motion-only badge.
function Click(region)
    while region and not region.mouseClicks do region = region:GetParent() end
    region:Fire("OnClick", "LeftButton")
    return region
end
'''

SETUP = r'''
local UI = addon.LibOrbitUI
pixel = UI.Pixel:Create()
context = {pixel = pixel, tooltip = Tooltip, tooltipHide = TooltipHide, scrollBar = {}}
layout = UI.Layout:Create(context, Constants)
Mixin(layout, UI.Config)
layout.configOptions = {constants = Constants, pixel = pixel, tooltip = Tooltip, tooltipHide = TooltipHide}
layout.RegisterTabsWidgetType = noop
layout:InitializeBaseWidgetTypes()
layout.scrollBar = UI.ScrollBar:Create(pixel)
layout.mediaMenu = UI.MediaMenu:CreateProvider({pixel = pixel}, layout, Constants, function() return false end)
renderer = UI.ConfigPanel:Create(context, layout, Constants, {})
container = Frame(UIParent)
container:SetScale(scale)
state.value, state.checks = "ALT", 0
OPTIONS = {
    {value = "OFF", label = "Off"}, {value = "ALT", label = "ALT key"},
    {value = "CTRL", label = "CTRL key"}, {value = "SHIFT", label = "SHIFT key"},
}
WARNING = {
    title = "Warning",
    text = function() return "Turn off to reduce CPU/Memory usage" end,
    visible = function(value) state.checks = state.checks + 1; return value ~= "OFF" end,
}
function Definition(extra)
    local definition = {type = "dropdown", key = "MapInteractKey", label = "Map Interactivity",
        options = OPTIONS, valueWarning = WARNING}
    for key, value in pairs(extra or {}) do definition[key] = value end
    return definition
end
function Write(value) state.writes = state.writes + 1; state.value = value end
function Render(definition)
    return renderer:RenderControl(container, definition, function() return state.value end, Write)
end
function Badge(control) return control.Control.ValueWarning end
function Shown(control)
    local badge = Badge(control)
    return badge ~= nil and badge:IsShown()
end
function Choose(control, index)
    local menu = Click(control.Control).Popup
    assert(menu:IsShown(), "the picker menu did not open")
    menu.rows[index]:Fire("OnClick")
end
function Close(actual, expected, label)
    assert(math.abs(actual - expected) < 1e-9, string.format("%s: expected %.12g, got %.12g", label, expected, actual))
end
function AssertInset(control)
    local text, badge = control.Control.Text.points.RIGHT, Badge(control)
    local gap = pixel:Multiple(3, control.Control.Text:GetEffectiveScale())
    if Shown(control) then
        assert(text[2] == badge and text[3] == "LEFT", "value text must stop before the badge")
        local point = badge.points.RIGHT
        assert(point[2] == control.Control.Arrow and point[3] == "LEFT", "badge must sit left of the arrow")
        Close(point[4], -pixel:Multiple(4, badge:GetEffectiveScale()), "badge gap")
        local size = pixel:EvenSnap(14, badge:GetEffectiveScale())
        Close(badge:GetWidth(), size, "badge width"); Close(badge:GetHeight(), size, "badge height")
    else
        assert(text[2] == control.Control.Arrow and text[3] == "LEFT", "hidden badge kept the value inset")
    end
    Close(text[4], -gap, "text gap")
end
'''


class ValueWarning(unittest.TestCase):
    def each(self, code):
        for family in ("retail", "forever"):
            for scale in FRAME_SCALES:
                with self.subTest(family=family, scale=scale):
                    lua = LuaRuntime(unpack_returned_tuples=True)
                    lua.execute(BOOT + HARNESS)
                    lua.execute("addon.LibOrbitUI.Client={family=...}", family)
                    for source in SOURCES:
                        lua.execute((RUNTIME / source).read_text(encoding="utf-8"), "Warning", lua.globals().addon)
                    lua.globals().scale = scale
                    lua.execute(SETUP)
                    lua.execute(code)
                    lua.execute("assert(#state.errors == 0)")

    def test_badge_follows_selection_and_insets_the_value_text(self):
        self.each(r'''
            local control = Render(Definition())
            local badge = Badge(control)
            assert(Shown(control) and badge.Icon.atlas == "transmog-icon-warning-small")
            assert(badge:GetParent() == control.Control and badge:GetScript("OnUpdate") == nil)
            AssertInset(control)
            Choose(control, 1)
            assert(state.value == "OFF" and not Shown(control) and control.Control.Text:GetText() == "Off")
            AssertInset(control)
            Choose(control, 3)
            assert(state.value == "CTRL" and Shown(control) and control.Control.Text:GetText() == "CTRL key")
            AssertInset(control)
        ''')

    def test_hover_shows_title_then_wrapped_body_and_keeps_picker_hover(self):
        self.each(r'''
            local control = Render(Definition())
            local badge = Badge(control)
            assert(badge.mouseMotion == true and badge.mouseClicks == false)
            badge:Fire("OnEnter")
            assert(Tooltip.shown and Tooltip.owner == badge and Tooltip.anchor == "ANCHOR_RIGHT")
            assert(Tooltip.title == "Warning" and Tooltip.titleColor[1] == 1 and #Tooltip.lines == 1)
            assert(Tooltip.lines[1].text == "Turn off to reduce CPU/Memory usage" and Tooltip.lines[1].wrap == true)
            assert(control.Control.hovered and control.Control.borderColor[1] == 0.3)
            badge:Fire("OnLeave")
            assert(not Tooltip.shown and not control.Control.hovered and control.Control.borderColor[1] == 0)
            Tooltip:SetOwner(container, "ANCHOR_RIGHT"); Tooltip:Show()
            badge:Fire("OnLeave"); control:RefreshOptions(OPTIONS, "OFF", Write)
            assert(not Shown(control) and Tooltip.shown and Tooltip.owner == container,
                "the badge closed a tooltip it did not own")
        ''')

    def test_badge_clicks_reach_the_picker_and_open_its_menu(self):
        self.each(r'''
            local control = Render(Definition())
            assert(Click(Badge(control)) == control.Control)
            local menu = control.Control.Popup
            assert(menu:IsShown() and control.Control.isOpen)
            Click(Badge(control))
            assert(not menu:IsShown() and not control.Control.isOpen)
            Click(Badge(control)); menu.rows[2]:Fire("OnClick")
            assert(state.value == "ALT" and Shown(control))
        ''')

    def test_hiding_while_hovered_releases_the_owned_tooltip(self):
        self.each(r'''
            local control = Render(Definition())
            local badge = Badge(control)
            badge:Fire("OnEnter"); assert(Tooltip.shown)
            control:RefreshOptions(OPTIONS, "OFF", Write)
            assert(not Shown(control) and not Tooltip.shown)
            control:RefreshOptions(OPTIONS, "SHIFT", Write)
            assert(Shown(control) and control.Control.Text:GetText() == "SHIFT key")
            AssertInset(control)
            badge:Fire("OnEnter"); container:Hide()
            assert(not Tooltip.shown, "an ancestor hide left the badge tooltip open")
        ''')

    def test_mixed_and_multiselect_values_never_show_the_badge(self):
        self.each(r'''
            local control = Render(Definition({mixed = true, mixedText = "Mixed"}))
            assert(control.Control.Text:GetText() == "Mixed" and not Shown(control))
            AssertInset(control)
            Choose(control, 2)
            assert(state.value == "ALT" and control.configMixed == nil and Shown(control))
            local multi = {emptyText = "None", summary = function(count) return count .. " keys" end}
            local direct = layout:CreateDropdown(container, "Keys", OPTIONS, {"ALT"}, Write, nil, nil, multi, WARNING)
            assert(not Shown(direct))
            direct:RefreshOptions(OPTIONS, "CTRL", Write)
            assert(Shown(direct) and direct.Control.Text:GetText() == "CTRL key")
            direct:RefreshOptions(OPTIONS, {"CTRL", "ALT"}, Write, multi)
            assert(not Shown(direct) and direct.Control.Text:GetText() == "2 keys")
        ''')

    def test_disabled_state_hides_the_badge_through_the_control_state_contract(self):
        self.each(r'''
            state.disabled = true
            local definition = Definition({disabled = function() return state.disabled end})
            local control = Render(definition)
            assert(not Shown(control) and not control.Control:IsEnabled())
            AssertInset(control)
            local checks = state.checks
            state.disabled = false; renderer:ApplyControlState(control, definition)
            assert(Shown(control) and state.checks == checks, "enabling re-ran the value predicate")
            AssertInset(control)
            state.disabled = true; renderer:ApplyControlState(control, definition)
            assert(not Shown(control))
        ''')

    def test_pooled_reuse_never_shows_a_stale_badge_or_runs_old_callbacks(self):
        self.each(r'''
            local control = Render(Definition())
            local badge = Badge(control)
            badge:Fire("OnEnter"); assert(Tooltip.shown)
            layout:Reset(container)
            assert(not badge:IsShown() and not Tooltip.shown and control.Control.valueWarning == nil)
            assert(control.dropValueWarning == nil and control.Control.Text.points.RIGHT[2] == control.Control.Arrow)
            local checks = state.checks
            local plain = Render({type = "dropdown", key = "Other", label = "Other", options = OPTIONS})
            assert(plain == control and Badge(plain) == badge and not Shown(plain))
            AssertInset(plain)
            Choose(plain, 3)
            assert(state.checks == checks and not Shown(plain), "a reused dropdown ran the previous predicate")
            layout:Reset(container)
            local quiet = Render(Definition({valueWarning = {title = "Warning", visible = false}}))
            assert(quiet == control and not Shown(quiet))
            local frames = #state.frames
            layout:Reset(container)
            local again = Render(Definition())
            assert(again == control and Shown(again) and #state.frames == frames, "reuse allocated new frames")
            Badge(again):Fire("OnEnter")
            assert(Tooltip.title == "Warning" and Tooltip.lines[1].text == "Turn off to reduce CPU/Memory usage")
        ''')

    def test_repeated_refreshes_allocate_nothing_and_first_creation_in_combat_is_allowed(self):
        self.each(r'''
            Combat(true)
            local control = Render(Definition())
            assert(Shown(control))
            local frames, checks = #state.frames, state.checks
            for index = 1, 20 do
                control:RefreshOptions(OPTIONS, index % 2 == 0 and "ALT" or "OFF", Write)
            end
            assert(#state.frames == frames and state.checks == checks + 20 and Shown(control))
            Tick(30)
            assert(state.checks == checks + 20, "idle frames evaluated the warning")
            Combat(false)
        ''')


if __name__ == "__main__":
    unittest.main()
