"""Exercise shipped Movement/EditSession input release at combat boundaries under Lua 5.1."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime
from picker_menus import BOOT

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
HARNESS = r'''
EventRegistry={events={}}
function EventRegistry:RegisterCallback(event,callback,owner)
    self.events[event]=self.events[event] or {}
    self.events[event][owner]=callback
end
function EventRegistry:UnregisterCallback(event,owner) self.events[event][owner]=nil end
C_InstanceEncounter={IsEncounterInProgress=function() return false end}
EditModeManagerFrame={
    IsEditModeActive=function() return true end,
    IsShown=function() return true end,
    IsEditModeLocked=function() return false end,
}
function GetCurrentKeyBoardFocus() return nil end
function IsShiftKeyDown() return false end
function GetMouseFoci() return {} end
local base=Frame
function Frame(parent,kind,template)
    local frame=base(parent,kind,template)
    function frame:SetToplevel() end
    function frame:SetMovable() end
    function frame:GetRect() return self:GetLeft(),self:GetBottom(),self:GetWidth(),self:GetHeight() end
    function frame:GetLeft() return 100 end
    function frame:ShowSelected() self:Show() end
    function frame:ShowHighlighted() self:Show() end
    function frame:StopMovingOrSizing() end
    function frame:UnregisterAllEvents() self.events={} end
    return frame
end
function MakeMovement()
    return addon.LibOrbitUI.Movement:Create({owner={},pixel=Pixel},Frame(UIParent),{
        label="Move",onSelect=noop,
        applyPosition=function() state.writes=state.writes+1 end,
    })
end
function Press(movement,key)
    local overlay=movement.overlay
    if not overlay:IsVisible() or not overlay.keyboard then return true end
    overlay:Fire("OnKeyDown",key)
    return not overlay:IsVisible() or overlay.propagate
end
UIParent:SetSize(1920,1080)
'''


class MovementInput(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute(BOOT + HARNESS)
        for source in ("Movement/Geometry.lua", "Movement/EditSession.lua", "Movement/Movement.lua"):
            self.lua.execute((RUNTIME / source).read_text(encoding="utf-8"), "Test", self.lua.globals().addon)

    def test_consumed_nudge_is_released_by_combat_event_before_or_after_lockdown(self):
        for event_first in (False, True):
            with self.subTest(event_first=event_first):
                self.setUp()
                self.lua.globals().eventFirst = event_first
                self.lua.execute('''
                    local movement=MakeMovement()
                    movement:SetSelected(true)
                    assert(not Press(movement,"UP") and state.writes==1)
                    if not eventFirst then state.combat=true end
                    movement.session.poll:Fire("OnEvent","PLAYER_REGEN_DISABLED")
                    assert(not movement:IsEditing() and not movement.overlay:IsVisible())
                    state.combat=true
                    assert(Press(movement,"W") and Press(movement,"1"))
                    Combat(false)
                    assert(movement:IsEditing() and not movement.selected)
                    movement:SetSelected(true)
                    assert(Press(movement,"W") and not Press(movement,"DOWN") and state.writes==2)
                    assert(#state.errors==0)
                ''')

    def test_key_during_lockdown_releases_input_before_the_poll(self):
        self.lua.execute('''
            local movement=MakeMovement()
            movement:SetSelected(true)
            assert(not Press(movement,"UP"))
            state.combat=true
            assert(Press(movement,"W") and not movement.overlay:IsVisible())
            assert(not movement:IsEditing() and state.writes==1 and #state.errors==0)
        ''')

    def test_construct_disable_and_destroy_in_combat_leave_no_live_capture(self):
        self.lua.execute('''
            state.combat=true
            local movement=MakeMovement()
            assert(not movement:IsEditing() and Press(movement,"W"))
            Combat(false)
            movement:SetSelected(true)
            assert(not Press(movement,"UP"))
            state.combat=true
            movement:SetEnabled(false)
            assert(Press(movement,"W"))
            movement:Destroy()
            Combat(false)
            assert(not movement.overlay:IsVisible() and not next(movement.session.poll.events))
            assert(not movement.updates:GetScript("OnUpdate") and #state.errors==0)
        ''')


if __name__ == "__main__":
    unittest.main()
