"""Pixel rounding and repeated nudges in shipped Lua 5.1; native rendering still needs WoW."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


PIXEL = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0/Rendering/Pixel.lua"
SCREEN_HEIGHTS = (768, 900, 1080, 1440, 1600, 2160)
FRAME_SCALES = (0.53, 0.64, 0.73, 0.85, 1.0, 1.25, 1.5)


def runtime(height):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().physical_height = height
    lua.execute(r'''
addon={LibOrbitUI={}}
secret=setmetatable({}, {__add=function() error('Arithmetic on secret') end,
 __sub=function() error('Arithmetic on secret') end, __div=function() error('Arithmetic on secret') end,
 __mul=function() error('Arithmetic on secret') end})
function issecretvalue(value) return rawequal(value,secret) end
function GetPhysicalScreenSize() return 2560,physical_height end
function geterrorhandler() return error end
function CreateFrame()
 local frame={events={},scripts={}}
 function frame:RegisterEvent(event) self.events[event]=true end
 function frame:UnregisterAllEvents() self.events={} end
 function frame:SetScript(event,handler) self.scripts[event]=handler end
 return frame
end
function Close(actual,expected,label)
 assert(math.abs(actual-expected)<1e-8,
  string.format('%s: expected %.12g, got %.12g',label,expected,actual))
end
''')
    lua.execute(PIXEL.read_text(encoding="utf-8"), "PixelFixture", lua.globals().addon)
    lua.execute("P=addon.LibOrbitUI.Pixel:Create()")
    return lua


class PixelRoundingTests(unittest.TestCase):
    def each_scale(self, code):
        for height in SCREEN_HEIGHTS:
            lua = runtime(height)
            for scale in FRAME_SCALES:
                with self.subTest(screen_height=height, frame_scale=scale):
                    lua.globals().scale = scale
                    lua.execute(code)

    def test_one_pixel_nudges_and_reversals_keep_the_same_rendered_step(self):
        self.each_scale(r'''
local step=P:Multiple(1,scale)
for _,point in ipairs({'CENTER','TOP','BOTTOM','LEFT','RIGHT','TOPLEFT','TOPRIGHT','BOTTOMLEFT','BOTTOMRIGHT'}) do
 for _,size in ipairs({{37,37},{37,38},{38,37},{38,38}}) do
  local width,height=P:Multiple(size[1],scale),P:Multiple(size[2],scale)
  for _,origin in ipairs({-1440,-38,-1,0,1,38,1440}) do
   for _,direction in ipairs({-1,1}) do
    for _,axis in ipairs({'X','Y'}) do
     local x,y=origin*step,-origin*step
     local startX,startY=P:SnapPosition(x,y,point,width,height,scale)
     local prevX,prevY=startX,startY
     local label=point..' '..size[1]..'x'..size[2]..' '..origin..' '..direction..axis
     for i=1,12 do
      x=x+(axis=='X' and direction*step or 0)
      y=y+(axis=='Y' and direction*step or 0)
      local nextX,nextY=P:SnapPosition(x,y,point,width,height,scale)
      Close((nextX-prevX)/step,axis=='X' and direction or 0,label..' forward X')
      Close((nextY-prevY)/step,axis=='Y' and direction or 0,label..' forward Y')
      prevX,prevY=nextX,nextY
     end
     for i=1,12 do
      x=x-(axis=='X' and direction*step or 0)
      y=y-(axis=='Y' and direction*step or 0)
      local nextX,nextY=P:SnapPosition(x,y,point,width,height,scale)
      Close((nextX-prevX)/step,axis=='X' and -direction or 0,label..' reverse X')
      Close((nextY-prevY)/step,axis=='Y' and -direction or 0,label..' reverse Y')
      prevX,prevY=nextX,nextY
     end
     Close((prevX-startX)/step,0,label..' restored X')
     Close((prevY-startY)/step,0,label..' restored Y')
    end
   end
  end
 end
end
''')

    def test_snap_ties_round_toward_positive_and_off_ties_remain_distinct(self):
        self.each_scale(r'''
local step=P:Multiple(1,scale)
for _,base in ipairs({-1440,-38,-2,-1,0,1,37,1440}) do
 for _,factor in ipairs({1,2}) do
  local snap=factor==1 and P.Snap or P.EvenSnap
  local tie=(base+0.5)*factor*step
  Close(snap(P,tie,scale)/(factor*step),base+1,'positive tie')
  Close(snap(P,tie-factor*step*1e-6,scale)/(factor*step),base,'below tie')
  Close(snap(P,tie+factor*step*1e-6,scale)/(factor*step),base+1,'above tie')
 end
end
''')

    def test_count_and_multiple_ties_remain_signed_away_from_zero(self):
        self.each_scale(r'''
local step=P:Multiple(1,scale)
for _,sign in ipairs({-1,1}) do
 for _,base in ipairs({0,1,2,37,1439}) do
  local half=base+0.5
  Close(P:ToCount(sign*half*step,scale),sign*(base+1),'count half')
  Close(P:ToCount(sign*(half-1e-6)*step,scale),sign*base,'count below half')
  Close(P:ToCount(sign*(half+1e-6)*step,scale),sign*(base+1),'count above half')
  Close(P:Multiple(sign*half,scale)/step,sign*(base+1),'multiple half')
  Close(P:Multiple(sign*(half-1e-6),scale)/step,sign*math.max(base,1),'multiple below half')
  Close(P:Multiple(sign*(half+1e-6),scale)/step,sign*(base+1),'multiple above half')
 end
end
assert(P:Multiple(0,scale)==0 and P:ToCount(0,scale)==0)
''')

    def test_secret_passthrough_and_unavailable_values_keep_existing_contract(self):
        lua = runtime(1080)
        lua.execute(r'''
assert(rawequal(P:Snap(secret,0.73),secret))
assert(rawequal(P:EvenSnap(secret,0.73),secret))
assert(rawequal(P:Multiple(secret,0.73),secret))
assert(P:Multiple(-3,secret)==-3)
assert(P:ToCount(secret,0.73)==0)
assert(P:Snap(nil)==0 and P:EvenSnap(nil)==0 and P:ToCount(nil)==0 and P:Multiple(nil)==0)
local step=P:Multiple(1,0.73)
local x,y=P:SnapPosition(2.2*step,-2.2*step,'CENTER',secret,secret,0.73)
Close(x/step,2,'secret width bypass');Close(y/step,-2,'secret height bypass')
''')


if __name__ == "__main__":
    unittest.main()
