"""Execute the shipped dropdown value-warning badge through schema, panel and pool owners; native input needs WoW."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime
from picker_menus import BOOT

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
SOURCES = (
    "Core/Callbacks.lua", "Core/EscapeClose.lua", "Rendering/Pixel.lua", "Config/Config.lua",
    "Config/ConfigSchema.lua", "Config/Layout.lua", "Config/LayoutControls.lua", "Config/Widgets/ScrollBar.lua",
    "Config/ConfigPickerWidgets.lua", "Config/Widgets/ConfigValueSwatch.lua", "Config/Pickers/MediaMenu.lua",
    "Config/Pickers/ConfigPickerControl.lua", "Config/Widgets/ConfigDropdown.lua", "Config/Dialogs/ConfigPanel.lua",
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
    function frame:RegisterForClicks(...) self.clickButtons = {...} end
    function frame:GetChecked() return self.checked end
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
function Tooltip:GetOwner() return self.owner end
function Tooltip:SetText(text, r, g, b) self.title, self.titleColor = text, {r, g, b} end
function Tooltip:AddLine(text, r, g, b, wrap) self.lines[#self.lines + 1] = {text = text, color = r, wrap = wrap} end
function Tooltip:Show() self.shown = true end
function Tooltip:Hide() self.shown = false end
function Tooltip:IsOwned(owner) return self.owner == owner end
function TooltipHide() Tooltip:Hide() end
-- Native dispatch: clicks reach the nearest region with click input enabled, never a motion-only badge.
function Click(region)
    while region and not region.mouseClicks do region = region:GetParent() end
    if region then region:Fire("OnClick", "LeftButton") end
    return region
end
'''

SETUP = r'''
local UI = addon.LibOrbitUI
Constants = UI.Config.Defaults
pixel = UI.Pixel:Create()
context = {pixel = pixel, tooltip = Tooltip, tooltipHide = TooltipHide, scrollBar = {}}
layout = UI.Layout:Create(context, Constants)
Mixin(layout, UI.Config)
layout.configOptions = {constants = Constants, pixel = pixel, tooltip = Tooltip, tooltipHide = TooltipHide}
layout.pickerOptions = {color = {open = noop, resolveValue = function(v) return v.r, v.g, v.b, v.a end}}
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
CHECKBOX = {tooltip = "Shadow", initialValue = true, callback = noop}
SWATCH = {tooltip = "Colour", initialValue = {r = 1, g = 0, b = 0, a = 1}, callback = noop}
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
function Badge(control) return control.ValueWarning end
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
function Step(frame) return pixel:GetScale() / frame:GetEffectiveScale() end
function OnGrid(value, frame, label)
    local count = value / Step(frame)
    assert(math.abs(count - math.floor(count + 0.5)) < 1e-6, label .. " is off the pixel grid")
end
-- Returns a value-column accessory's left and right edges relative to its row's right edge.
function Edges(control, accessory)
    local point = accessory.points.CENTER
    assert(point[2] == control and point[3] == "RIGHT" and point[5] == 0, "accessory left the row's value column")
    return point[4] - accessory:GetWidth() / 2, point[4] + accessory:GetWidth() / 2
end
function AssertBox(control)
    local box, scale = control.Control, control:GetEffectiveScale()
    local right, left = box.points.RIGHT, box.points.LEFT
    assert(right[2] == control and right[3] == "RIGHT" and right[4] == -Constants.Widget.ValueWidth and right[5] == 0,
        "the dropdown box no longer ends at the value column")
    assert(left[2] == control.Label and left[3] == "RIGHT" and left[4] == Constants.Widget.LabelGap)
    local text = box.Text.points.RIGHT
    assert(text[2] == box.Arrow and text[3] == "LEFT", "the value text left its arrow")
    Close(text[4], -pixel:Multiple(3, scale), "text gap")
    Close(box.Text.points.LEFT[2], pixel:Multiple(8, scale), "text inset")
    assert(Badge(control) == nil or Badge(control):GetParent() == control, "the badge must belong to the row")
end
function AssertBadge(control)
    AssertBox(control)
    if not Shown(control) then
        return
    end
    local badge, scale = Badge(control), control:GetEffectiveScale()
    local size = pixel:EvenSnap(Constants.Widget.ValueSwatchSize, scale)
    Close(badge:GetWidth(), size, "badge width"); Close(badge:GetHeight(), size, "badge height")
    local left, right = Edges(control, badge)
    assert(left > -Constants.Widget.ValueWidth and right <= 0, "the badge must sit right of the box")
    OnGrid(left, control, "badge left edge"); OnGrid(right, control, "badge right edge")
    return left, right
end
function AssertAlone(control)
    assert(Shown(control), "the badge is hidden")
    local left, right = AssertBadge(control)
    local width, scale = Badge(control):GetWidth(), control:GetEffectiveScale()
    local edge = pixel:Snap(-pixel:Multiple(Constants.Widget.ValueInset, scale) - width / 2, scale)
    Close((left + right) / 2, edge, "a lone badge must take the column's right edge")
end
function AssertBeside(control, accessory)
    assert(Shown(control), "the badge is hidden")
    local _, badgeRight = AssertBadge(control)
    local left = Edges(control, accessory)
    local gap = left - badgeRight
    assert(gap > 0 and math.abs(gap - pixel:Multiple(Constants.Widget.LabelGap, control:GetEffectiveScale()))
        <= Step(control) + 1e-9, "the badge must group left of the accessory with the value-column gap")
end
function Point(frame) return unpack(frame.points.CENTER, 1, 5) end
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

    def test_badge_sits_in_the_value_column_and_follows_selection(self):
        self.each(r'''
            local control = Render(Definition())
            local badge = Badge(control)
            assert(Shown(control) and badge.Icon.atlas == "transmog-icon-warning-small")
            assert(badge:GetParent() == control and badge:GetScript("OnUpdate") == nil)
            AssertAlone(control)
            Choose(control, 1)
            assert(state.value == "OFF" and not Shown(control) and control.Control.Text:GetText() == "Off")
            AssertBox(control)
            Choose(control, 3)
            assert(state.value == "CTRL" and Shown(control) and control.Control.Text:GetText() == "CTRL key")
            AssertAlone(control)
            layout:Reset(container)
            local plain = Render({type = "dropdown", key = "Other", label = "Other", options = OPTIONS})
            assert(plain == control and not Shown(plain))
            AssertBox(plain)
        ''')

    def test_badge_groups_left_of_a_value_checkbox_or_swatch_without_moving_them(self):
        self.each(r'''
            for _, extra in ipairs({{valueCheckbox = CHECKBOX}, {valueColor = SWATCH}}) do
                local control = Render(Definition(extra))
                local accessory = extra.valueCheckbox and control.ValueCheckbox or control.ValueColorSwatch
                assert(Shown(control) and accessory:IsShown())
                AssertBeside(control, accessory)
                local before = {Point(accessory)}
                Choose(control, 1)
                assert(not Shown(control) and accessory:IsShown())
                AssertBox(control)
                Choose(control, 4)
                assert(Shown(control))
                AssertBeside(control, accessory)
                local after = {Point(accessory)}
                for index = 1, 5 do assert(before[index] == after[index], "toggling the warning moved its neighbour") end
                layout:Reset(container)
            end
        ''')

    def test_rows_without_a_warning_keep_their_accessory_anchors(self):
        self.each(r'''
            local warned = Render(Definition({valueCheckbox = CHECKBOX}))
            assert(Shown(warned))
            layout:Reset(container)
            local plain = Render({type = "dropdown", key = "Outline", label = "Outline", options = OPTIONS,
                valueCheckbox = CHECKBOX})
            assert(plain == warned and not Shown(plain))
            AssertBox(plain)
            local checkbox, scale = plain.ValueCheckbox, plain:GetEffectiveScale()
            local size = pixel:Snap(Constants.Widget.ValueCheckboxSize, scale)
            local expected = -pixel:Snap(size / 2 + pixel:Multiple(Constants.Widget.ValueInset, scale), scale)
            Close(checkbox.points.CENTER[4], expected, "plain dropdown checkbox anchor")
        ''')

    def test_hover_shows_title_then_wrapped_body_without_touching_the_box(self):
        self.each(r'''
            local control = Render(Definition())
            local badge = Badge(control)
            assert(badge.mouseMotion == true and badge.mouseClicks == false)
            badge:Fire("OnEnter")
            assert(Tooltip.shown and Tooltip.owner == badge and Tooltip.anchor == "ANCHOR_RIGHT")
            assert(Tooltip.title == "Warning" and Tooltip.titleColor[1] == 1 and #Tooltip.lines == 1)
            assert(Tooltip.lines[1].text == "Turn off to reduce CPU/Memory usage" and Tooltip.lines[1].wrap == true)
            assert(not control.Control.hovered and control.Control.borderColor[1] == 0, "the badge drove box hover")
            badge:Fire("OnLeave")
            assert(not Tooltip.shown and control.Control.borderColor[1] == 0)
            Tooltip:SetOwner(container, "ANCHOR_RIGHT"); Tooltip:Show()
            badge:Fire("OnLeave"); control:RefreshOptions(OPTIONS, "OFF", Write)
            assert(not Shown(control) and Tooltip.shown and Tooltip.owner == container,
                "the badge closed a tooltip it did not own")
        ''')

    def test_badge_is_not_a_click_target_and_the_box_still_opens_its_menu(self):
        self.each(r'''
            local control = Render(Definition())
            assert(Click(Badge(control)) == nil and control.Control.Popup == nil, "a badge click opened the menu")
            assert(Click(control.Control) == control.Control)
            local menu = control.Control.Popup
            assert(menu:IsShown() and control.Control.isOpen and Shown(control))
            Click(Badge(control))
            assert(menu:IsShown(), "a badge click closed the menu")
            Click(control.Control)
            assert(not menu:IsShown() and not control.Control.isOpen)
            Click(control.Control); menu.rows[2]:Fire("OnClick")
            assert(state.value == "ALT" and Shown(control))
            AssertAlone(control)
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
            AssertAlone(control)
            badge:Fire("OnEnter"); container:Hide()
            assert(not Tooltip.shown, "an ancestor hide left the badge tooltip open")
        ''')

    def test_mixed_and_multiselect_values_never_show_the_badge(self):
        self.each(r'''
            local control = Render(Definition({mixed = true, mixedText = "Mixed"}))
            assert(control.Control.Text:GetText() == "Mixed" and not Shown(control))
            AssertBox(control)
            Choose(control, 2)
            assert(state.value == "ALT" and control.configMixed == nil and Shown(control))
            AssertAlone(control)
            local multi = {emptyText = "None", summary = function(count) return count .. " keys" end}
            local direct = layout:CreateDropdown(container, "Keys", OPTIONS, {"ALT"}, Write, nil, nil, multi, WARNING)
            assert(not Shown(direct))
            direct:RefreshOptions(OPTIONS, "CTRL", Write)
            assert(Shown(direct) and direct.Control.Text:GetText() == "CTRL key")
            AssertAlone(direct)
            direct:RefreshOptions(OPTIONS, {"CTRL", "ALT"}, Write, multi)
            assert(not Shown(direct) and direct.Control.Text:GetText() == "2 keys")
        ''')

    def test_disabled_state_hides_the_badge_through_the_control_state_contract(self):
        self.each(r'''
            state.disabled = true
            local definition = Definition({disabled = function() return state.disabled end,
                valueCheckbox = CHECKBOX})
            local control = Render(definition)
            assert(not Shown(control) and not control.Control:IsEnabled())
            AssertBox(control)
            local checks = state.checks
            state.disabled = false; renderer:ApplyControlState(control, definition)
            assert(Shown(control) and state.checks == checks, "enabling re-ran the value predicate")
            AssertBeside(control, control.ValueCheckbox)
            state.disabled = true; renderer:ApplyControlState(control, definition)
            assert(not Shown(control))
            layout:Reset(container)
            state.value = "OFF"
            local late = Render(Definition({disabled = function() return state.disabled end}))
            assert(late == control and not Shown(late))
            late:RefreshOptions(OPTIONS, "ALT", Write)
            assert(not Shown(late), "a disabled refresh showed the badge")
            state.disabled = false; renderer:ApplyControlState(late, definition)
            assert(Shown(late), "enabling did not restore a warning chosen while disabled")
            AssertAlone(late)
        ''')

    def test_pooled_reuse_never_shows_a_stale_badge_or_runs_old_callbacks(self):
        self.each(r'''
            local control = Render(Definition())
            local badge = Badge(control)
            badge:Fire("OnEnter"); assert(Tooltip.shown)
            layout:Reset(container)
            assert(not badge:IsShown() and not Tooltip.shown and control.valueWarning == nil)
            assert(control.dropValueWarning == nil and control.valueWarningWanted == false)
            local checks = state.checks
            local plain = Render({type = "dropdown", key = "Other", label = "Other", options = OPTIONS})
            assert(plain == control and Badge(plain) == badge and not Shown(plain))
            AssertBox(plain)
            Choose(plain, 3)
            assert(state.checks == checks and not Shown(plain), "a reused dropdown ran the previous predicate")
            layout:Reset(container)
            local quiet = Render(Definition({valueWarning = {title = "Warning", visible = false}}))
            assert(quiet == control and not Shown(quiet))
            local frames = #state.frames
            layout:Reset(container)
            local again = Render(Definition())
            assert(again == control and Shown(again) and #state.frames == frames, "reuse allocated new frames")
            AssertAlone(again)
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
