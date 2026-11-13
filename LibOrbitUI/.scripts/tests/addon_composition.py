"""Run shipped Addon boot, reconciliation and movement composition with a real Runtime under Lua 5.1."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
SOURCES = ("Core/Bootstrap.lua", "Core/Callbacks.lua", "Core/Runtime.lua", "Addon/Addon.lua", "Addon/AddonMovement.lua")
HARNESS = r'''
mock = { combat = false, errors = {}, timers = {}, categories = 0, movements = {} }
table.freeze = function(value) return value end
SlashCmdList = {}
function Mixin(target, mixin)
    for key, value in pairs(mixin) do target[key] = value end
    return target
end
function InCombatLockdown() return mock.combat end
function geterrorhandler() return function(err) table.insert(mock.errors, err) end end
function NewFrame()
    local frame = { events = {}, scripts = {}, shown = true, points = {} }
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:UnregisterEvent(event) self.events[event] = nil end
    function frame:UnregisterAllEvents() self.events = {} end
    function frame:SetScript(event, callback) self.scripts[event] = callback end
    function frame:Show() self.shown = true end
    function frame:Hide() self.shown = false end
    function frame:IsShown() return self.shown end
    function frame:SetSize() end
    function frame:SetText(value) self.text = value end
    function frame:ClearAllPoints() self.points = {} end
    function frame:SetPoint(point, relative, relativePoint, x, y)
        self.points[point] = { relative, relativePoint, x, y }
    end
    function frame:GetNumPoints()
        local count = 0
        for _ in pairs(self.points) do count = count + 1 end
        return count
    end
    return frame
end
function CreateFrame() return NewFrame() end
UIParent = NewFrame()
C_Timer = { NewTimer = function(_, callback)
    local timer = { callback = callback }
    function timer:Cancel() self.cancelled = true end
    table.insert(mock.timers, timer)
    return timer
end }
C_Timer.NewTicker = C_Timer.NewTimer
function RunTimers()
    local timers = mock.timers
    mock.timers = {}
    for _, timer in ipairs(timers) do
        if not timer.cancelled then timer.callback() end
    end
end
Settings = {
    RegisterCanvasLayoutCategory = function(_, title) return { title = title } end,
    RegisterAddOnCategory = function() mock.categories = mock.categories + 1 end,
}
function Controller(enabled, canActivate)
    local controller = { active = false, enables = 0, disables = 0, applies = 0, positions = {} }
    function controller:GetSetting(index, key)
        if key == "Enabled" then return enabled end
        return self.positions[index]
    end
    function controller:SetSetting(index, key, value) self.positions[index] = value; return true end
    function controller:IsActive() return self.active end
    function controller:Enable()
        self.enables = self.enables + 1
        self.active = canActivate
        if self.active and self.onLoaded then self.onLoaded(self) end
        return self.active or nil
    end
    function controller:Disable() self.disables = self.disables + 1; self.active = false; return true end
    function controller:ApplySettings() self.applies = self.applies + 1 end
    return controller
end
function App(controller, extra)
    local options = {
        addonName = "Product", name = "Product", title = "Product", controller = controller,
        context = { pixel = { Point = function() end } },
        store = { Initialize = function(_, data) return data end },
        readStore = function() return {} end,
        writeStore = function() end,
        labels = { settings = "Settings" },
        slashKey = "PRODUCT", slash = { "/product" },
        frames = function() return {} end,
    }
    for key, value in pairs(extra or {}) do options[key] = value end
    return addon.LibOrbitUI.Addon:Create(options)
end
function Boot(app)
    app.events.scripts.OnEvent(app.events, "ADDON_LOADED", "Product")
    app.events.scripts.OnEvent(app.events, "PLAYER_LOGIN")
end
'''


class AddonComposition(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(HARNESS)
        self.lua.execute("addon = {}")
        for relative in SOURCES:
            self.lua.execute("return assert(loadstring(...))", (RUNTIME / relative).read_text(encoding="utf-8"))(
                "Product", self.lua.globals().addon
            )
        self.lua.execute('''
            addon.LibOrbitUI.Movement = { Create = function(_, _, frame, options)
                local movement = { frame = frame, options = options, enabled = {}, resets = {} }
                function movement:SetEnabled(value) self.enabled[#self.enabled + 1] = value end
                function movement:Refresh() end
                function movement:Reset(position) self.resets[#self.resets + 1] = position end
                table.insert(mock.movements, movement)
                return movement
            end }
        ''')

    def tearDown(self):
        self.lua.execute("assert(#mock.errors == 0, mock.errors[1])")

    def test_nothing_applies_before_login_readiness(self):
        self.lua.execute('''
            local controller = Controller(true, true)
            local app = App(controller)
            app:Apply(); app:Reconcile(); app:ResetPosition()
            assert(#mock.timers == 0 and controller.enables == 0 and controller.disables == 0)
            app.events.scripts.OnEvent(app.events, "ADDON_LOADED", "Product")
            app:Apply(); app:Reconcile()
            assert(#mock.timers == 0 and controller.enables == 0 and mock.categories == 1)
            app.events.scripts.OnEvent(app.events, "PLAYER_LOGIN")
            assert(app.ready and controller.enables == 1 and controller:IsActive())
            app:Apply(); RunTimers()
            assert(controller.applies == 1)
        ''')

    def test_rejected_store_never_becomes_ready(self):
        self.lua.execute('''
            local controller = Controller(true, true)
            local app = App(controller, { store = { Initialize = function() return nil, "Malformed" end } })
            Boot(app)
            assert(not app.ready and app.storeError == "Malformed" and controller.enables == 0)
        ''')

    def test_hosted_product_is_ready_without_a_local_store(self):
        self.lua.execute('''
            local readies, applies = 0, 0
            local bridge = { Ready = function() readies = readies + 1 end, Apply = function() applies = applies + 1 end,
                IsEnabled = function() return true end }
            local controller = Controller(true, true)
            local app = App(controller, { bridge = bridge,
                store = { Initialize = function() error("hosted products never initialize a local store") end } })
            Boot(app)
            assert(app.ready and readies == 1 and mock.categories == 0)
            app:Reconcile()
            assert(applies == 1 and controller.enables == 0)
        ''')

    def test_movement_follows_the_controller_active_state(self):
        self.lua.execute('''
            local frame = NewFrame()
            local controller = Controller(true, false)
            local records = { { frame = frame, index = 1, label = "Main" } }
            local app = App(controller, { frames = function() return records end })
            Boot(app)
            app:AttachMovement()
            app:Reconcile()
            local movement = mock.movements[1]
            assert(controller.enables == 2 and not controller:IsActive())
            assert(movement.enabled[#movement.enabled] == false)
            controller.active = true
            app:Reconcile()
            assert(movement.enabled[#movement.enabled] == true and controller.applies == 1)
        ''')

    def test_restore_prefers_saved_then_frame_then_record_defaults(self):
        self.lua.execute('''
            local controller = Controller(true, true)
            local app = App(controller)
            local frame = NewFrame()
            frame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 5, -5)
            frame.defaultPosition = { point = "CENTER", x = 10, y = 20 }
            app.frameRecords[1] = { defaultPosition = { point = "BOTTOM", x = 1, y = 2 } }
            app:RestorePosition(frame, 1)
            assert(frame:GetNumPoints() == 1 and frame.points.CENTER[2] == "CENTER" and frame.points.CENTER[3] == 10)
            frame.defaultPosition = nil
            app:RestorePosition(frame, 1)
            assert(frame:GetNumPoints() == 1 and frame.points.BOTTOM[3] == 1)
            controller.positions[1] = { point = "LEFT", relativePoint = "RIGHT", x = 3, y = 4 }
            app:RestorePosition(frame, 1)
            assert(frame:GetNumPoints() == 1 and frame.points.LEFT[2] == "RIGHT" and frame.points.LEFT[4] == 4)
            controller.positions[1] = { point = "TOP", x = 0, y = 0 }
            frame.orbitIsDragging = true
            app:RestorePosition(frame, 1)
            frame.orbitIsDragging = nil
            mock.combat = true
            app:RestorePosition(frame, 1)
            mock.combat = false
            assert(frame.points.LEFT and not frame.points.TOP)
            local unplaced = NewFrame()
            app:RestorePosition(unplaced, 2)
            assert(unplaced:GetNumPoints() == 0)
        ''')

    def test_movement_records_need_a_frame_and_numeric_index(self):
        self.lua.execute('''
            local app = App(Controller(true, true), { frames = function()
                return { { frame = NewFrame(), index = "1", label = "Main" } }
            end })
            assert(not pcall(app.AttachMovement, app) and #mock.movements == 0)
            app = App(Controller(true, true), { frames = function() return { { index = 1, label = "Main" } } end })
            assert(not pcall(app.AttachMovement, app) and #mock.movements == 0)
        ''')


if __name__ == "__main__":
    unittest.main()
