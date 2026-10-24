"""Execute the shipped slider's drag, commit, cancellation and pooled lifecycles; native input still needs WoW."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime
from picker_menus import BOOT

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"

HARNESS = r'''
state.clock, state.pending, state.native, state.inits = 0, {}, {down = 0, up = 0}, {}
function C_Timer.NewTimer(delay, callback)
    local timer = {due = state.clock + delay, callback = callback}
    function timer:Cancel() self.cancelled = true end
    state.pending[#state.pending + 1] = timer
    return timer
end
function Advance(seconds)
    state.clock = state.clock + seconds
    local due = state.pending
    state.pending = {}
    for _, timer in ipairs(due) do
        if timer.cancelled then
        elseif timer.due <= state.clock then timer.callback() else state.pending[#state.pending + 1] = timer end
    end
end
local function Children(parent)
    local children = {}
    for _, frame in ipairs(state.frames) do
        if frame.parent == parent and frame.shown then children[#children + 1] = frame end
    end
    return children
end
local function Cascade(frame, event)
    frame:Fire(event)
    for _, child in ipairs(Children(frame)) do Cascade(child, event) end
end
local BaseFrame = Frame
function Frame(parent, kind, template)
    local frame = BaseFrame(parent, kind, template)
    function frame:Hide()
        if self.shown then
            local visible = self:IsVisible()
            self.shown = false
            if visible then Cascade(self, "OnHide") end
        end
    end
    function frame:Show()
        if not self.shown then
            self.shown = true
            if self:IsVisible() then Cascade(self, "OnShow") end
        end
    end
    function frame:SetEnabled(value) self.enabled = value end
    function frame:GetRegions() return end
    function frame:GetObjectType() return self.kind end
    if template == "EditModeSettingSliderTemplate" then
        frame.Label = Frame(frame, "FontString")
        local stepper = Frame(frame)
        frame.Slider = stepper
        local inner = Frame(stepper, "Slider")
        stepper.Slider, stepper.Back, stepper.Forward = inner, Frame(stepper, "Button"), Frame(stepper, "Button")
        stepper.callbacks = {}
        function stepper:RegisterCallback(event, callback, owner)
            self.callbacks[owner] = {event = event, callback = callback}
        end
        function stepper:UnregisterCallback(event, owner)
            if self.callbacks[owner] and self.callbacks[owner].event == event then self.callbacks[owner] = nil end
        end
        function stepper:TriggerEvent(event, ...)
            for owner, entry in pairs(self.callbacks) do
                if entry.event == event then entry.callback(owner, ...) end
            end
        end
        function stepper:SetEnabled(enabled) inner:SetEnabled(enabled) end
        function stepper:Init(value, minValue, maxValue, steps)
            state.inits[#state.inits + 1] = {value, minValue, maxValue, steps}
            inner.min, inner.max, inner.step = minValue, maxValue, (maxValue - minValue) / steps
            inner:SetScript("OnValueChanged", function(_, changed) stepper:TriggerEvent("OnValueChanged", changed) end)
            inner:SetValue(value)
        end
        function inner:SetValue(value)
            value = math.max(self.min, math.min(self.max, value))
            if value ~= self.value then
                self.value = value
                self:Fire("OnValueChanged", value)
            end
        end
        function inner:GetValue() return self.value end
        inner:SetScript("OnMouseDown", function(slider)
            if slider:IsEnabled() then state.native.down = state.native.down + 1 end
        end)
        inner:SetScript("OnMouseUp", function(slider)
            if slider:IsEnabled() then state.native.up = state.native.up + 1 end
        end)
        stepper.Back:SetScript("OnClick", function() inner:SetValue(inner.value - inner.step) end)
        stepper.Forward:SetScript("OnClick", function() inner:SetValue(inner.value + inner.step) end)
    end
    return frame
end
'''

SETUP = r'''
Constants.UI.ValueFont = "value"
local UI = addon.LibOrbitUI
UI.Config.ReleaseValueControls = noop
layout = UI.Layout:Create({pixel = Pixel, tooltip = Tooltip, tooltipHide = noop, scrollBar = {}}, Constants)
Mixin(layout, UI.Config)
layout.configOptions = {constants = Constants, pixel = Pixel, tooltip = Tooltip, tooltipHide = noop}
container = Frame(UIParent)
events = {}
function Record(name)
    return function(...) events[#events + 1] = {name, ...} end
end
function Build(options, name)
    name = name or "a"
    options = options or {}
    options.onDragStart = options.onDragStart or Record(name .. ":start")
    options.onDragStop = options.onDragStop or Record(name .. ":stop")
    local slider = layout:CreateSlider(container, "Delay", 0, 2, 0.5, function(value) return value .. "s" end,
        0.5, Record(name .. ":commit"), options)
    layout:AddControl(container, slider)
    return slider
end
function Press(slider, button) slider.Slider.Slider:Fire("OnMouseDown", button or "LeftButton") end
function Release(slider, button) slider.Slider.Slider:Fire("OnMouseUp", button or "LeftButton") end
function Move(slider, value) slider.Slider.Slider:SetValue(value) end
function Step(slider) slider.Slider.Forward:Fire("OnClick", "LeftButton") end
function Expect(...)
    local expected = {...}
    local actual = {}
    for index, event in ipairs(events) do
        local text = event[1]
        for item = 2, select("#", unpack(event)) do text = text .. "=" .. tostring(event[item]) end
        actual[index] = text
    end
    assert(table.concat(actual, ",") == table.concat(expected, ","),
        "expected " .. table.concat(expected, ",") .. ", got " .. table.concat(actual, ","))
end
'''


class SliderLifecycle(unittest.TestCase):
    def check(self, source):
        for family in ("retail", "forever"):
            with self.subTest(family=family):
                lua = LuaRuntime(unpack_returned_tuples=True)
                lua.execute(BOOT)
                lua.execute("addon.LibOrbitUI.Client={family=...}", family)
                lua.execute(HARNESS)
                for source_file in ("Config/Layout.lua", "Config/Widgets/ConfigSlider.lua"):
                    lua.execute((RUNTIME / source_file).read_text(encoding="utf-8"), "Slider", lua.globals().addon)
                lua.execute(SETUP)
                lua.execute(source)
                lua.execute("assert(#state.errors == 0)")

    def test_release_stops_drag_then_commits_once_and_keeps_native_handlers(self):
        self.check('''
            local slider = Build({updateOnRelease = true})
            Press(slider); Move(slider, 1.5)
            Expect("a:start")
            assert(slider.Value:GetText() == "1.5s", "drag did not preview its value")
            Release(slider)
            Expect("a:start", "a:stop=false", "a:commit=1.5")
            assert(state.native.down == 1 and state.native.up == 1, "library replaced the native mouse handlers")
        ''')

    def test_live_slider_reports_drags_without_release_commit(self):
        self.check('''
            local slider = Build()
            Press(slider); Move(slider, 1); Release(slider)
            Expect("a:start", "a:commit=1", "a:stop=false")
        ''')

    def test_disabled_slider_still_receives_mouse_scripts_but_starts_and_commits_nothing(self):
        self.check('''
            local slider = Build({updateOnRelease = true})
            slider.Slider:SetEnabled(false)
            Press(slider); Release(slider)
            slider.Slider.Slider:Fire("OnMouseDown"); slider.Slider.Slider:Fire("OnMouseUp")
            assert(#events == 0, "a disabled press or release reached the drag or commit callbacks")
            assert(state.native.down == 0 and state.native.up == 0, "native handlers ignore disabled input")
            slider.Slider:SetEnabled(true); Press(slider); Expect("a:start")
        ''')

    def test_only_the_button_that_opened_the_press_ends_it(self):
        self.check('''
            local released = Build({updateOnRelease = true})
            Press(released); Move(released, 1)
            Press(released, "RightButton"); Release(released, "RightButton")
            Expect("a:start")
            Move(released, 2); Release(released)
            Expect("a:start", "a:stop=false", "a:commit=2")
            Release(released)
            Expect("a:start", "a:stop=false", "a:commit=2")
            events = {}
            local live = Build({}, "b")
            Press(live); Move(live, 1); Press(live, "RightButton"); Release(live, "RightButton"); Move(live, 2)
            Release(live)
            Expect("b:start", "b:commit=1", "b:commit=2", "b:stop=false")
        ''')

    def test_rebuilding_from_a_drag_callback_never_commits_to_the_next_binding(self):
        self.check('''
            local slider
            slider = Build({updateOnRelease = true, onDragStop = function(cancelled)
                Record("a:stop")(cancelled)
                if not cancelled then layout:ReleaseControl(slider); Build({updateOnRelease = true}, "b") end
            end})
            Press(slider); Move(slider, 1.5); Release(slider)
            Expect("a:start", "a:stop=false")
            layout:ReleaseControl(slider)
            events = {}
            local starting
            starting = Build({updateOnRelease = true, onDragStart = function()
                Record("c:start")()
                layout:ReleaseControl(starting); Build({updateOnRelease = true}, "d")
            end}, "c")
            Press(starting); Move(starting, 2); Release(starting)
            Expect("c:start", "c:stop=true")
            layout:ReleaseControl(starting)
            events = {}
            local held = Build({updateOnRelease = true}, "e")
            Press(held); Move(held, 1)
            layout:ReleaseControl(held)
            local next = Build({updateOnRelease = true}, "f")
            assert(next == held, "pooled slider was not reused")
            Release(next)
            Expect("e:start", "e:stop=true")
        ''')

    def test_hiding_an_ancestor_cancels_drag_and_stepper_without_commit(self):
        self.check('''
            local slider = Build({updateOnRelease = true})
            Press(slider); Move(slider, 2)
            container:Hide()
            Expect("a:start", "a:stop=true")
            container:Show(); Release(slider)
            Expect("a:start", "a:stop=true")
            Step(slider); container:Hide(); Advance(1)
            Expect("a:start", "a:stop=true")
            container:Show(); Press(slider); Release(slider)
            Expect("a:start", "a:stop=true", "a:start", "a:stop=false", "a:commit=2")
        ''')

    def test_public_cancel_drops_pending_stepper_and_release_commits(self):
        self.check('''
            local slider = Build({updateOnRelease = true})
            Step(slider); Step(slider); Advance(0.05)
            slider:CancelPendingCommit(); Advance(1)
            assert(#events == 0, "a cancelled stepper commit fired")
            Step(slider); Advance(1); Expect("a:commit=2")
            events = {}
            Press(slider); slider:CancelPendingCommit(); slider:CancelPendingCommit(); Release(slider)
            Expect("a:start", "a:stop=true")
        ''')

    def test_reinitialize_is_silent_keeps_bounds_and_supersedes_stepper(self):
        self.check('''
            local live = Build()
            live:Reinitialize(4, 0, 10, 2)
            assert(#events == 0 and live.Value:GetText() == "4s")
            local init = state.inits[#state.inits]
            assert(init[1] == 4 and init[2] == 0 and init[3] == 10 and init[4] == 5)
            live:Reinitialize(6)
            init = state.inits[#state.inits]
            assert(#events == 0 and init[2] == 0 and init[3] == 10 and init[4] == 5, "value-only reset lost bounds")
            Move(live, 8); Expect("a:commit=8")
            events = {}
            local released = Build({updateOnRelease = true}, "b")
            Step(released); released:Reinitialize(0.5); Advance(1)
            assert(#events == 0, "a reinitialized slider committed its superseded stepper value")
        ''')

    def test_stop_handler_can_cancel_or_resync_before_the_release_commit(self):
        self.check('''
            local cancelling
            cancelling = Build({updateOnRelease = true, onDragStop = function(cancelled)
                Record("a:stop")(cancelled)
                if not cancelled then cancelling:CancelPendingCommit() end
            end})
            Press(cancelling); Move(cancelling, 1); Release(cancelling)
            Expect("a:start", "a:stop=false")
            events = {}
            local resync
            resync = Build({updateOnRelease = true, onDragStop = function() resync:Reinitialize(0.5) end}, "b")
            Press(resync); Move(resync, 2); Release(resync)
            Expect("b:start", "b:commit=2")
        ''')

    def test_set_callbacks_ends_the_previous_binding_before_rebinding(self):
        self.check('''
            local slider = Build({updateOnRelease = true})
            Press(slider); Move(slider, 1)
            Step(slider)
            slider:SetCallbacks(Record("b:commit"), Record("b:start"), Record("b:stop"))
            Advance(1); Release(slider)
            Expect("a:start", "a:stop=true")
            Press(slider); Move(slider, 2); Release(slider)
            Expect("a:start", "a:stop=true", "b:start", "b:stop=false", "b:commit=2")
        ''')

    def test_pool_release_expires_callbacks_and_reuse_adds_no_hooks(self):
        self.check('''
            local slider = Build({updateOnRelease = true})
            local inner = slider.Slider.Slider
            Press(slider); Step(slider)
            layout:ReleaseControl(slider)
            Expect("a:start", "a:stop=true")
            Advance(1); Release(slider); Press(slider); Move(slider, 2); Release(slider)
            Expect("a:start", "a:stop=true")
            for cycle = 1, 3 do
                local reused = Build(cycle == 2 and {} or {updateOnRelease = true}, "c" .. cycle)
                assert(reused == slider, "pooled slider was not reused")
                layout:ReleaseControl(reused)
            end
            assert(#inner.hooks.OnMouseDown == 1 and #inner.hooks.OnMouseUp == 1, "pooled reuse stacked mouse hooks")
            assert(#slider.Slider.Forward.hooks.OnClick == 1 and #slider.hooks.OnHide == 1, "reuse stacked hooks")
            events = {}
            local live = Build({onDragStart = noop, onDragStop = noop}, "d")
            Press(live); Move(live, 1.5); Release(live); Step(live); Advance(1)
            Expect("d:commit=1.5", "d:commit=2")
            events = {}
            local released = Build({updateOnRelease = true}, "e")
            Step(released); Step(released); Advance(1)
            Expect("e:commit=1.5")
        ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
