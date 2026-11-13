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

    def test_nearest_edge_and_orientation_fallbacks(self):
        self.lua.execute('''
            local Geometry=addon.LibOrbitUI.Geometry
            assert(Geometry:NearestEdge(10,500,20,20,1920,1080)=="LEFT")
            assert(Geometry:NearestEdge(1890,500,20,20,1920,1080)=="RIGHT")
            assert(Geometry:NearestEdge(900,1050,20,20,1920,1080)=="TOP")
            assert(Geometry:NearestEdge(900,10,20,20,1920,1080)=="BOTTOM")
            assert(Geometry:DetectOrientation(nil,"TOP")=="TOP" and Geometry:DetectOrientation(nil)=="LEFT")
            assert(Geometry:DetectOrientation({},"BOTTOM")=="BOTTOM")
            function GetScreenWidth() return 1920 end
            function GetScreenHeight() return 1080 end
            local frame=Frame(UIParent)
            frame.width,frame.height,frame.bottom=20,20,1050
            frame.GetLeft=function() return 900 end
            assert(Geometry:DetectOrientation(frame,"LEFT")=="TOP")
            frame.GetLeft=function() return nil end
            assert(Geometry:DetectOrientation(frame,"RIGHT")=="RIGHT")
        ''')

    def test_session_generations_encounters_and_poll_cadence(self):
        self.lua.execute('''
            local nativeActive,encounter=true,false
            EditModeManagerFrame.IsEditModeActive=function() return nativeActive end
            C_InstanceEncounter.IsEncounterInProgress=function() return encounter end
            local log,generations={},{}
            local function Session(options)
                options.onEnter=function(_,reason,generation) log[#log+1]="enter:"..reason;generations[#generations+1]=generation end
                options.onExit=function(_,reason,generation) log[#log+1]="exit:"..reason;generations[#generations+1]=generation end
                return addon.LibOrbitUI.EditSession:Create({},options)
            end
            local session=Session({})
            session:SetEnabled(false);session:SetEnabled(true);session:SetEnabled(false);session:SetEnabled(true)
            for i=2,#generations do assert(generations[i]>generations[i-1],table.concat(generations,",")) end
            encounter=true
            session:Refresh("poll")
            assert(not session:IsActive() and log[#log]=="exit:encounter")
            local exempt=Session({blockEncounter=false})
            assert(exempt:IsActive() and log[#log]=="enter:create")
            encounter=false
            session:Refresh("poll")
            assert(session:IsActive())
            nativeActive=false
            session.poll:Fire("OnUpdate",0.1)
            assert(not session:IsActive() and log[#log]=="exit:exit",log[#log])
        ''')

    def test_session_transitions_never_nest(self):
        self.lua.execute('''
            local depth,nested,session=0,0
            local function Callback(change)
                return function()
                    if depth>0 then nested=nested+1 end
                    depth=depth+1;change();depth=depth-1
                end
            end
            session=addon.LibOrbitUI.EditSession:Create({},{
                enabled=false,
                onEnter=Callback(function() session:SetEnabled(false) end),
                onExit=Callback(function() session:SetEnabled(true) end),
            })
            session:SetEnabled(true)
            assert(nested==0 and session:IsActive())
            session.poll:Fire("OnUpdate",0.1)
            assert(nested==0 and not session:IsActive())
        ''')

    def test_reset_respects_encounters_and_zero_size_frames_hide_the_overlay(self):
        self.lua.execute('''
            local encounter=false
            C_InstanceEncounter.IsEncounterInProgress=function() return encounter end
            local function Make(options,frame)
                options.label,options.onSelect="Move",noop
                options.applyPosition=function() state.writes=state.writes+1 end
                return addon.LibOrbitUI.Movement:Create({owner={},pixel=Pixel},frame or Frame(UIParent),options)
            end
            local blocked,exempt=Make({}),Make({blockEncounter=false})
            assert(blocked:IsEditing() and blocked.overlay:IsShown())
            encounter=true
            assert(blocked:Reset({point="CENTER",x=0,y=0})==false and state.writes==0)
            assert(exempt:Reset({point="CENTER",x=0,y=0})==true and state.writes==1)
            encounter=false
            local empty=Frame(UIParent);empty.width=0
            local hidden=Make({},empty)
            assert(hidden:IsEditing() and not hidden.overlay:IsShown())
            empty.width=40;hidden:Refresh()
            assert(hidden.overlay:IsShown())
        ''')

    def test_selection_moves_between_overlays_in_one_context(self):
        self.lua.execute('''
            local context={owner={},pixel=Pixel}
            local function Make()
                return addon.LibOrbitUI.Movement:Create(context,Frame(UIParent),{label="Move",onSelect=noop,applyPosition=noop})
            end
            local first,second=Make(),Make()
            first:SetSelected(true)
            assert(first.overlay.keyboard and context.movementSelection==first)
            first:SetSelected(true)
            assert(first.overlay.keyboard and context.movementSelection==first)
            second:SetSelected(true)
            assert(second.overlay.keyboard and not first.overlay.keyboard and context.movementSelection==second)
            second:SetSelected(false)
            assert(not second.overlay.keyboard and context.movementSelection==nil)
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
