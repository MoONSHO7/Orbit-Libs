"""Execute the shipped range slider's drag and callback owners; native input still needs WoW."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime
from picker_menus import BOOT


SOURCE = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0/Config/Widgets/ConfigRangeSlider.lua"

HARNESS = r'''
local BaseFrame=Frame
function Frame(parent,kind,template)
    local frame=BaseFrame(parent,kind,template)
    frame.SetBlendMode=noop
    function frame:GetLeft() return self.left or 100 end
    return frame
end
C_Texture={GetAtlasInfo=function() return {width=14,height=14} end}
function GetCursorPosition() return state.cursorX or 0,0 end
function IsMouseButtonDown(button)
    assert(button=="LeftButton")
    return state.down or false
end
local Config=addon.LibOrbitUI.Config
Config.configOptions={tooltip=Tooltip,tooltipHide=noop}
events={}
function Record(kind,low,high) events[#events+1]={kind,low,high} end
function Configure(gap,dual)
    rs:Configure({minGap=gap or 0,dual=dual,onDragStart=function() Record('start') end,
        onDragStop=function() Record('stop') end,
        onPreview=function(low,high) Record('preview',low,high) end,
        onCommit=function(low,high) Record('commit',low,high) end})
end
function Build(scale)
    rs=Config:CreateRangeSlider(UIParent,226)
    rs:SetScale(scale)
    local thumbs={}
    for _,frame in ipairs(state.frames) do
        if frame:GetParent()==rs then
            if frame.kind=='Button' then thumbs[#thumbs+1]=frame
            elseif frame.kind=='Frame' then track=frame end
        end
    end
    assert(#thumbs==2 and track)
    lowThumb,highThumb=thumbs[1],thumbs[2]
    Configure()
end
function Cursor(value)
    state.cursorX=(track:GetLeft()+track:GetWidth()*value/100)*rs:GetEffectiveScale()
end
function Press(thumb,value)
    Cursor(value);state.down=true;thumb:Fire('OnMouseDown','LeftButton')
end
function Drag(value) Cursor(value);Tick(1) end
function Release(thumb)
    state.down=false
    if thumb then thumb:Fire('OnMouseUp','LeftButton') else Tick(1) end
end
function Range(low,high)
    assert(rs.low==low and rs.high==high,
        string.format('expected %s/%s, got %s/%s',low,high,rs.low,rs.high))
end
function Event(index,kind,low,high)
    local event=events[index]
    assert(event and event[1]==kind,'unexpected event '..index)
    if low~=nil then assert(event[2]==low and event[3]==high,'incorrect event range') end
end
function Stopped(count)
    assert(not rs:GetScript('OnUpdate'),'released slider retained drag polling')
    assert((lowThumb.tex.scale or 1)==1 and (highThumb.tex.scale or 1)==1,'thumb highlight survived release')
    Tick(10)
    assert(#events==count,'released slider emitted another callback')
end
'''


class RangeSlider(unittest.TestCase):
    def check(self, source):
        for family in ("retail", "forever"):
            for scale in (.65, 1, 1.25):
                with self.subTest(family=family, scale=scale):
                    lua = LuaRuntime(unpack_returned_tuples=True)
                    lua.execute(BOOT)
                    lua.execute("addon.LibOrbitUI.Client={family=...}", family)
                    lua.execute(SOURCE.read_text(encoding="utf-8"), "RangeSliderFixture", lua.globals().addon)
                    lua.execute(HARNESS)
                    lua.execute("Build(...)", scale)
                    lua.execute(source)
                    lua.execute("assert(#state.errors==0)")

    def test_high_thumb_can_open_equal_range_to_the_left(self):
        for initial in (25, 100):
            with self.subTest(initial=initial):
                self.check(f'''
                    rs:SetRange({initial},{initial})
                    Press(highThumb,{initial});Drag({initial-10});Range({initial-10},{initial})
                    assert(lowThumb.tex.scale==1.2 and highThumb.tex.scale==1)
                    Event(1,'start');Event(2,'preview',{initial-10},{initial})
                    Release(highThumb);Event(3,'stop');Event(4,'commit',{initial-10},{initial})
                    Stopped(4)
                ''')

    def test_low_thumb_can_open_equal_range_to_the_right(self):
        for initial in (0, 25):
            with self.subTest(initial=initial):
                self.check(f'''
                    rs:SetRange({initial},{initial})
                    Press(lowThumb,{initial});Drag({initial+10});Range({initial},{initial+10})
                    assert(lowThumb.tex.scale==1 and highThumb.tex.scale==1.2)
                    Release();Event(1,'start');Event(2,'preview',{initial},{initial+10})
                    Event(3,'stop');Event(4,'commit',{initial},{initial+10});Stopped(4)
                ''')

    def test_stationary_exact_and_substep_pointer_emit_no_preview(self):
        self.check('''
            rs:SetRange(25,25);Press(highThumb,25)
            Tick(10);Drag(25.2);Range(25,25)
            assert(#events==1,'stationary equal range emitted a value callback')
            Event(1,'start')
            Release();Event(2,'stop');Event(3,'commit',25,25);Stopped(3)
        ''')

    def test_selected_endpoint_remains_owned_when_drag_returns_to_overlap(self):
        self.check('''
            rs:SetRange(25,25);Press(highThumb,25)
            Drag(15);Range(15,25);Drag(25);Range(25,25)
            Drag(35);Range(25,25)
            assert(#events==3,'a selected low endpoint crossed into the high endpoint')
            Drag(5);Range(5,25)
            Release();Stopped(6)
        ''')

    def test_hide_releases_switched_thumb_once_and_reuse_has_no_old_direction(self):
        self.check('''
            rs:SetRange(25,25);Press(highThumb,25);Drag(15)
            rs:Hide();Event(3,'stop');Event(4,'commit',15,25);Stopped(4)
            events={};rs:Show();rs:SetRange(0,0)
            Press(lowThumb,0);Drag(20);Range(0,20)
            Release(lowThumb);Event(3,'stop');Event(4,'commit',0,20);Stopped(4)
        ''')

    def test_configured_gap_remains_enforced_after_ordinary_drags(self):
        self.check('''
            Configure(10,true);rs:SetRange(25,35)
            Press(lowThumb,25);Drag(30);Range(25,35)
            assert(#events==1,'minimum-gap clamp emitted a preview')
            Drag(20);Range(20,35);Release()
            events={};Press(highThumb,35);Drag(10);Range(20,30)
            Drag(20);Range(20,30)
            assert(#events==2,'clamped high endpoint emitted repeated previews')
            Release();Event(4,'commit',20,30);Stopped(4)
        ''')

    def test_single_thumb_ignores_equal_range_disambiguation(self):
        self.check('''
            Configure(0,false);rs:SetRange(25,25)
            assert(not highThumb:IsShown())
            Press(lowThumb,25);Drag(40);Range(40,25)
            Release();Event(4,'commit',40,25);Stopped(4)
        ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
