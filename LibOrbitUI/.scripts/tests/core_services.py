"""Exercise shipped Core services (callbacks, events, throttle, runtime, store, controller, client) under Lua 5.1."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
SOURCES = ("Core/Bootstrap.lua", "Core/Callbacks.lua", "Core/Events.lua", "Core/Throttle.lua", "Core/Runtime.lua",
           "Core/SettingsStore.lua", "Core/Controller.lua")
HARNESS = r'''
mock = { errors = {}, timers = {}, frames = {}, combat = false }
table.freeze = function(value) return value end
function issecretvalue() return false end
function Mixin(target, mixin)
    for key, value in pairs(mixin) do target[key] = value end
    return target
end
function InCombatLockdown() return mock.combat end
function geterrorhandler() return function(err) table.insert(mock.errors, err) end end
function CreateFrame()
    local frame = { events = {}, scripts = {}, shown = true }
    table.insert(mock.frames, frame)
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:UnregisterEvent(event) self.events[event] = nil end
    function frame:UnregisterAllEvents() self.events = {} end
    function frame:SetScript(event, callback) self.scripts[event] = callback end
    function frame:GetScript(event) return self.scripts[event] end
    function frame:Show() self.shown = true end
    function frame:Hide() self.shown = false end
    return frame
end
local function NewTimer(seconds, callback)
    local timer = { seconds = seconds, callback = callback }
    function timer:Cancel() self.cancelled = true end
    table.insert(mock.timers, timer)
    return timer
end
C_Timer = { NewTimer = NewTimer, NewTicker = NewTimer }
function Rejects(pattern, callback, ...)
    local ok, err = pcall(callback, ...)
    return not ok and tostring(err):find(pattern, 1, true) ~= nil
end
'''


class CoreServices(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(HARNESS)
        self.lua.execute("addon = {}")
        for relative in SOURCES:
            self.lua.execute("return assert(loadstring(...))", (RUNTIME / relative).read_text(encoding="utf-8"))(
                "Consumer", self.lua.globals().addon
            )
        self.lua.execute("UI = addon.LibOrbitUI")

    def test_callbacks_return_results_and_name_the_failing_context(self):
        self.lua.execute('''
            local ok, value = UI.Callbacks:Run(function(a, b) return a + b end, "Sum", 2, 3)
            assert(ok == true and value == 5)
            assert(UI.Callbacks:Wrap(function(a) return a * 2 end, "Double")(4) == 8)
            local failed, err = UI.Callbacks:Run(function() error("boom", 0) end, "Owner")
            assert(failed == false and err == "boom")
            assert(mock.errors[1] == "LibOrbitUI [Owner:wrapped_call] boom", mock.errors[1])
            UI.Callbacks:Run(function() error("again", 0) end)
            assert(mock.errors[2] == "LibOrbitUI [Unknown:wrapped_call] again", mock.errors[2])
            assert(UI.Callbacks:Wrap(function() error("x", 0) end, "Wrapped")() == nil and #mock.errors == 3)
        ''')

    def test_events_reject_empty_names_and_report_removal(self):
        self.lua.execute('''
            local events = UI.Events:Create()
            assert(Rejects("event name is required", events.On, events, "", function() end))
            assert(not next(events.listeners))
            local calls = 0
            local function Count() calls = calls + 1 end
            events:On("ORBIT_TEST", Count)
            assert(events:Off("ORBIT_TEST", function() end) == false)
            assert(events:Off("ORBIT_TEST", Count) == true)
            assert(events:Off("ORBIT_TEST", Count) == false)
            events:Fire("ORBIT_TEST")
            assert(calls == 0)
            events:On("PLAYER_LOGIN", Count)
            assert(events.frame.events.PLAYER_LOGIN)
            assert(events:Off("PLAYER_LOGIN", Count) == true and not events.frame.events.PLAYER_LOGIN)
        ''')

    def test_repeated_and_nested_dispatch_retains_no_per_dispatch_storage(self):
        self.lua.execute('''
            local events = UI.Events:Create()
            local order = {}
            events:On("ORBIT_INNER", function() order[#order + 1] = "inner" end)
            events:On("ORBIT_OUTER", function()
                order[#order + 1] = "outer"
                events:Fire("ORBIT_INNER")
                error("listener failure", 0)
            end)
            events:On("ORBIT_OUTER", function() order[#order + 1] = "after" end)
            events:Fire("ORBIT_OUTER")
            assert(table.concat(order, ",") == "outer,inner,after", table.concat(order, ","))
            assert(#mock.errors == 1 and mock.errors[1]:find("listener failure", 1, true))
            order = setmetatable({}, { __newindex = function() end })
            mock.errors = {}
            collectgarbage("collect")
            local before = collectgarbage("count")
            for _ = 1, 10000 do events:Fire("ORBIT_OUTER") end
            mock.errors = {}
            collectgarbage("collect")
            local grown = collectgarbage("count") - before
            assert(grown < 64, "dispatch retained " .. grown .. " KiB")
        ''')

    def test_throttle_rejects_non_positive_or_unbounded_intervals(self):
        self.lua.execute('''
            local throttle = UI.Throttle:Create()
            for _, interval in ipairs({ 0, -1, math.huge, -math.huge, "1" }) do
                assert(Rejects("finite and positive", throttle.Gate, throttle, {}, "t", interval, 1),
                    tostring(interval))
                assert(Rejects("finite and positive", throttle.OnUpdate, throttle, interval, {}, function() end),
                    tostring(interval))
            end
            local state, fired = {}, {}
            for i = 1, 4 do fired[i] = throttle:Gate(state, "t", 0.5, 0.25) end
            assert(not fired[1] and fired[2] and not fired[3] and fired[4])
            local calls = 0
            local update = throttle:OnUpdate(0.5, {}, function() calls = calls + 1 end, "Test")
            for _ = 1, 4 do update({}, 0.25) end
            assert(calls == 2)
        ''')

    def test_runtime_rejects_non_positive_delays_without_scheduling(self):
        self.lua.execute('''
            local runtime = UI.Runtime:Create({})
            for _, delay in ipairs({ 0, -1, "1" }) do
                assert(Rejects("timer interval must be positive", runtime.After, runtime, "k", delay, function() end),
                    tostring(delay))
                assert(Rejects("timer interval must be positive", runtime.Ticker, runtime, "k", delay, function() end),
                    tostring(delay))
            end
            assert(#mock.timers == 0 and not next(runtime.work))
            local calls = 0
            runtime:After("k", 0.01, function() calls = calls + 1 end)
            assert(#mock.timers == 1 and mock.timers[1].seconds == 0.01)
            mock.timers[1].callback()
            mock.timers[1].callback()
            assert(calls == 1)
        ''')

    def test_store_rejects_infinite_numbers_and_unbounded_values(self):
        self.lua.execute('''
            local store = UI.SettingsStore:Create({ Scale = 100, Data = {} })
            assert(store:Initialize())
            for _, value in ipairs({ math.huge, -math.huge, 0 / 0 }) do
                local ok, err = store:Set(1, "Scale", value)
                assert(ok == nil and err == "Invalid or undeclared LibOrbitUI setting", tostring(value))
            end
            assert(store:Set(1, "Scale", -12.5) and store:Get(1, "Scale") == -12.5)
            local function Chain(tables)
                local root = {}
                local node = root
                for _ = 2, tables do
                    node.next = {}
                    node = node.next
                end
                return root
            end
            assert(store:Set(1, "Data", Chain(32)))
            assert(store:Set(1, "Data", Chain(33)) == nil)
            local wide = {}
            for i = 1, 100000 do wide[i] = true end
            assert(store:Set(1, "Data", wide))
            wide[100001] = true
            assert(store:Set(1, "Data", wide) == nil)
            local ok, err = store:Initialize({ version = 1, settings = { [1] = { Data = wide } }, collections = {} })
            assert(ok == nil and err == "Malformed LibOrbitUI settings root")
        ''')

    def test_controller_reports_indexed_setting_changes_and_unique_generations(self):
        self.lua.execute('''
            local controller = UI.Controller:Create({ name = "Indexed", defaults = { Scale = 100 } })
            assert(controller.store:Initialize())
            local seen = {}
            controller.onSettingChanged = function(owner, index, key, value)
                assert(owner == controller)
                seen[#seen + 1] = index .. ":" .. key .. "=" .. tostring(value)
            end
            assert(controller:SetSetting(2, "Scale", 50))
            assert(controller:SetSetting(nil, "Scale", 75))
            assert(controller:SetSetting(3, "Scale", "bad") == nil)
            assert(table.concat(seen, ",") == "2:Scale=50,1:Scale=75", table.concat(seen, ","))
            assert(controller:GetSetting(2, "Scale") == 50 and controller:GetSetting(1, "Scale") == 75)

            local applies = 0
            function controller:ApplySettings() applies = applies + 1 end
            local generations = { controller:GetLifecycleGeneration() }
            local function Record() generations[#generations + 1] = controller:GetLifecycleGeneration() end
            assert(controller:Enable() == true); Record()
            assert(controller:Disable() == true); Record()
            assert(controller:Enable() == true); Record()
            assert(controller:Disable() == true); Record()
            for i = 2, #generations do
                assert(generations[i] > generations[i - 1], table.concat(generations, ","))
            end
            assert(applies == 2)
        ''')


class ClientIdentity(unittest.TestCase):
    def resolve(self, version, interface, legacy):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute("table.freeze = function(value) return value end; addon = {}")
        g = lua.globals()
        g.fixture_version, g.fixture_interface, g.fixture_legacy = version, interface, legacy
        lua.execute('''
            function GetBuildInfo() return fixture_version, "70000", "Nov 1 2026", fixture_interface end
            if fixture_legacy ~= "absent" then
                C_AddOns = { DoesAddOnExist = function(name)
                    assert(name == "Blizzard_LegacySystem")
                    return fixture_legacy
                end }
            end
        ''')
        for relative in ("Core/Bootstrap.lua", "Core/Client.lua"):
            lua.execute("return assert(loadstring(...))", (RUNTIME / relative).read_text(encoding="utf-8"))(
                "Consumer", g.addon
            )
        client = g.addon.LibOrbitUI.Client
        return client.family, client.reason, client.legacyAddonExists, client.interface

    def test_version_and_legacy_addon_signals_classify_each_client(self):
        cases = (
            (("12.1.5", 120105, False), ("retail", "version-signature", False, 120105)),
            (("12.1.5", 120105, True), ("unknown", "conflicting-client-signals", True, 120105)),
            (("1.60.1", 16001, False), ("forever", "version-signature", False, 16001)),
            (("1.60.1", 16001, True), ("forever", "version-and-addon", True, 16001)),
            (("1.60.1", 16001, "absent"), ("forever", "version-signature", None, 16001)),
            (("11.2.7", 110207, False), ("unknown", "unrecognized-version", False, 110207)),
        )
        for fixture, expected in cases:
            with self.subTest(fixture=fixture):
                self.assertEqual(self.resolve(*fixture), expected)


if __name__ == "__main__":
    unittest.main()
