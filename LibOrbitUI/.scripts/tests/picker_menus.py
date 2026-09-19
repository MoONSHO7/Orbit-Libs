"""Orbit-owned picker menus and real shared scrollbar under Lua 5.1; pixels still need WoW."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"
BOOT = r'''
state={allocations=0,writes=0,tooltips=0}
function noop() end
table.freeze=function(t) return t end
state.frames={}
function InCombatLockdown() return false end
function GetCursorPosition() return 0,state.cursorY or 0 end
function Mixin(target,source) for k,v in pairs(source) do target[k]=v end;return target end
function Tick(n)
    for i=1,n do
        local frames={unpack(state.frames)}
        for _,frame in ipairs(frames) do
            if frame:IsVisible() and frame:GetScript("OnUpdate") then frame:Fire("OnUpdate",1/60) end
        end
    end
end
ChatFontNormal="chat"
function SearchBoxTemplate_OnTextChanged() end
function CreateObjectPool(create,reset)
    local pool={free={}}
    function pool:Acquire() return table.remove(self.free) or create(self) end
    function pool:Release(row) reset(self,row);table.insert(self.free,row) end
    return pool
end
function Frame(parent,kind,template)
    local f={parent=parent,kind=kind,template=template,shown=true,scripts={},hooks={},events={},width=240,height=24}
    table.insert(state.frames,f)
    function f:SetScript(event,fn) self.scripts[event]=fn end
    function f:GetScript(event) return self.scripts[event] end
    function f:HookScript(event,fn)
        self.hooks[event]=self.hooks[event] or {};table.insert(self.hooks[event],fn)
    end
    function f:Fire(event,...)
        if self.scripts[event] then self.scripts[event](self,...) end
        for _,fn in ipairs(self.hooks[event] or {}) do fn(self,...) end
    end
    function f:Show()
        if not self.shown then self.shown=true;self:Fire("OnShow") end
    end
    function f:Hide()
        if self.shown then self.shown=false;self:Fire("OnHide") end
    end
    function f:IsShown() return self.shown end
    function f:IsVisible() return self.shown and (not self.parent or self.parent:IsVisible()) end
    function f:SetShown(value) if value then self:Show() else self:Hide() end end
    function f:SetParent(value) self.parent=value end
    function f:GetParent() return self.parent end
    function f:SetSize(w,h) self.width=w;self.height=h;self:Fire("OnSizeChanged",w,h) end
    function f:SetWidth(w) self.width=w end
    function f:SetHeight(h) self.height=h end
    function f:GetWidth() return self.width end
    function f:GetHeight()
        if self.points and self.points.TOPRIGHT and self.points.BOTTOMRIGHT then
            local target=self.points.TOPRIGHT[2]
            if type(target)=="table" and target.kind=="ScrollFrame" then return target:GetHeight() end
        end
        return self.height
    end
    function f:SetScale(value) self.scale=value end
    function f:SetIgnoreParentScale(value) self.ignoreParentScale=value end
    function f:GetEffectiveScale()
        return (self.scale or 1)*(not self.ignoreParentScale and self.parent and self.parent:GetEffectiveScale() or 1)
    end
    function f:SetPoint(...)
        self.lastPoint={...};self.points=self.points or {};self.points[select(1,...)]=self.lastPoint
    end
    function f:ClearAllPoints() self.lastPoint=nil;self.points={} end
    function f:SetAllPoints(target) self.allPoints=target end
    function f:SetText(value) self.text=value;self:Fire("OnTextChanged",false) end
    function f:GetText() return self.text end
    function f:GetUnboundedStringWidth() return #(self.text or "")*7 end
    function f:SetFont(path,size,flags) self.font={path,size,flags} end
    function f:SetFontObject(value) self.fontObject=value end
    function f:SetTexture(value) self.texture=value end
    function f:SetFocus() self.focus=true end
    function f:ClearFocus() self.focus=false end
    function f:HasFocus() return self.focus==true end
    function f:GetCursorPosition() return self.cursor or 0 end
    function f:SetCursorPosition(value) self.cursor=value end
    function f:EnableMouse(value) self.mouse=value end
    function f:SetAtlas(value) self.atlas=value end
    function f:SetBackdrop(value) self.backdrop=value end
    function f:SetBackdropColor(...) self.backdropColor={...} end
    function f:SetBackdropBorderColor(...) self.borderColor={...} end
    function f:SetRotation(value) self.rotation=value end
    function f:SetChecked(value) self.checked=value end
    function f:IsEnabled() return self.enabled~=false end
    function f:GetBottom() return self.bottom or 600 end
    function f:IsMouseOver() return self.mouseOver==true end
    function f:RegisterEvent(event) self.events[event]=true end
    function f:UnregisterEvent(event) self.events[event]=nil end
    function f:SetScrollChild(child) self.child=child end
    function f:GetVerticalScrollRange() return math.max(0,(self.child and self.child:GetHeight() or 0)-self:GetHeight()) end
    function f:GetVerticalScroll() return self.scroll or 0 end
    function f:SetVerticalScroll(value)
        value=math.max(0,math.min(value,self:GetVerticalScrollRange()))
        if value~=self:GetVerticalScroll() then self.scroll=value;self:Fire("OnVerticalScroll",value) end
    end
    function f:UpdateScrollChildRect() self:Fire("OnScrollRangeChanged") end
    function f:CreateFontString(_,_,font)
        local value=Frame(self,"FontString");value.fontObject=font;return value
    end
    function f:CreateTexture() return Frame(self,"Texture") end
    function f:RegisterCallback(event,fn) self.events[event]=fn end
    for _,key in ipairs({"SetAutoFocus","SetJustifyH","SetWordWrap","SetTextColor","SetVertexColor",
        "SetColorTexture","SetTexCoord","SetDrawLayer","SetAlpha","SetDesaturated",
        "SetShadowOffset","SetShadowColor","SetFrameStrata","SetFrameLevel","SetClampedToScreen",
        "SetClipsChildren","SetPropagateKeyboardInput","EnableMouseWheel","RegisterForDrag"}) do f[key]=noop end
    assert(kind~="DropdownButton", "Native dropdown ownership is forbidden")
    f:SetScript("OnShow",noop)
    return f
end
function CreateFrame(kind,_,parent,template) return Frame(parent,kind,template) end
UIParent=Frame()
addon={LibOrbitUI={Config={}}}
Pixel={Enforce=noop,Multiple=function(_,v) return v end,Snap=function(_,v) return v end,
    Point=function(_,frame,...) frame:SetPoint(...) end}
Constants={Texture={White="white"},Strata={FullscreenDialog="FULLSCREEN_DIALOG"},UI={LabelFont="label"},Widget={LabelWidth=110,LabelGap=10,ValueWidth=40,Width=500,Height=32}}
Tooltip={SetOwner=noop,SetText=noop,AddLine=noop,Show=function() state.tooltips=state.tooltips+1 end}
'''


class PickerMenuTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BOOT)
        for file in ("Widgets/ScrollBar.lua", "Pickers/ConfigPickerControl.lua", "Pickers/MediaMenu.lua",
                     "Widgets/ConfigDropdown.lua", "Pickers/ConfigFontPicker.lua", "Pickers/ConfigTexturePicker.lua"):
            self.lua.execute((ROOT / "Config" / file).read_text(encoding="utf-8"), "Addon", self.lua.globals().addon)
        self.lua.execute(r'''
            layout=addon.LibOrbitUI.Config
            layout.configOptions={constants=Constants,pixel=Pixel,tooltip=Tooltip,tooltipHide=noop}
            layout.scrollBar=addon.LibOrbitUI.ScrollBar:Create(Pixel)
            layout.mediaMenu=addon.LibOrbitUI.MediaMenu:CreateProvider({pixel=Pixel},layout,Constants,
                function(name) return name:find("Orbit",1,true)==1 end)
            layout.pickerOptions={media={defaultFont="OrbitFont",fallbackFont="fallback",defaultTexture="Smooth",
                noneLabel="None",fetch=function(kind,name) return kind.."/"..name end,
                isValid=function() return true end,list=function() return {"Other","OrbitFont"} end}}
            function Write(value) state.value=value;state.writes=state.writes+1 end
            function Open(control) control.Control:Fire("OnClick");return control.Dropdown end
            function Choose(menu,index) menu.rows[index]:Fire("OnClick") end
            function PreviewMenu(count)
                local frame=Frame();frame.Label=Frame(frame,"FontString")
                local control=layout:CreatePickerControl(frame)
                control.Text:SetText("Glow");control.Swatch=Frame(control);control.Swatch.animating=true
                local items={}
                for i=1,count do items[i]=string.format("Item%03d",i) end
                function frame:ShowDropdown()
                    if not self.Dropdown then
                        self.Dropdown=layout.mediaMenu:Create(control,{rowHeight=36,maxHeight=420,sorted=false,
                            createRow=function(parent)
                                state.allocations=state.allocations+1
                                local row=Frame(parent);row.Text=Frame(row,"FontString");return row
                            end,renderRow=function(row,item)
                                state.renders=(state.renders or 0)+1;row.Text:SetText(item);row.animating=true
                            end,onSelect=Write})
                        layout:BindPickerDropdown(control,self.Dropdown)
                    end
                    self.Dropdown:Populate(items,"Item001")
                end
                layout:LayoutPickerLabelAndControl(frame,"Glow")
                return frame
            end
        ''')

    def test_owned_chrome_selection_actions_and_private_tooltips(self):
        self.lua.execute(r'''
            local control=layout:CreateDropdown(Frame(),"Orientation",{
                {text="Vertical",value=0,tooltip="Tip"},{text="Horizontal",value=1},
                {divider=true},{text="Enter Spell Id",action=function() state.action=true end}},0,Write)
            assert(control.Control.kind=="Button" and control.Control.template=="BackdropTemplate")
            assert(control.Control.Arrow.atlas=="common-dropdown-icon-next")
            assert(control.Control.backdropColor[1]==0.08 and control.Control:GetHeight()==24)
            assert(control.Control.Text:GetText()=="Vertical" and control.Dropdown==nil)
            local menu=Open(control)
            assert(menu.rows[1].Selected:IsShown() and not menu.rows[1].Check:IsShown() and menu.rows[3].Divider:IsShown())
            assert(menu.backdropColor[1]==0.06 and control.Control.Arrow.rotation==math.pi/2)
            assert(menu.ScrollBar==menu.ScrollFrame.OrbitScrollBar)
            assert(not menu.ScrollBar:IsShown() and menu:GetScript("OnUpdate")==nil)
            menu.rows[1]:Fire("OnEnter");assert(state.tooltips==1)
            Choose(menu,2)
            assert(state.value==1 and control.Control.Text:GetText()=="Horizontal")
            assert(not control.Control.isOpen and next(menu.rows)==nil)
            Open(control);Choose(menu,4);assert(state.action and state.writes==1)
        ''')

    def test_multiselect_preserves_copied_choices_without_rebuilding_rows(self):
        self.lua.execute(r'''
            local cfg={emptyText="None",summary=function(n) return n.." selected" end}
            local control=layout:CreateDropdown(Frame(),"Options",{{text="A",value="a"},{text="B",value="b"}},
                {},Write,nil,nil,cfg)
            local menu=Open(control);local first=menu.rows[1]
            assert(first.Check.template=="UIRadialButtonTemplate" and first.Check:IsShown() and not first.Check.checked)
            Choose(menu,1);assert(menu:IsShown() and state.value[1]=="a")
            assert(menu.rows[1]==first and first.Check.checked and control.Control.Text:GetText()=="A")
            Choose(menu,2);local previous=state.value;assert(#previous==2)
            Choose(menu,1);assert(#state.value==1 and state.value[1]=="b" and #previous==2)
            menu:Hide();assert(control.Control.Text:GetText()=="B")
        ''')

    def test_popup_escapes_panel_clipping_but_keeps_scale_anchor_and_owner_lifetime(self):
        self.lua.execute(r'''
            UIParent:SetScale(0.75)
            local panel=Frame(UIParent);panel:SetScale(0.8);panel:SetClipsChildren(true)
            local control=layout:CreateDropdown(panel,"Orientation",{
                {text="Vertical",value=0},{text="Horizontal",value=1}},0,Write)
            local menu=Open(control)
            assert(menu:GetParent()==UIParent and menu:GetParent()~=control.Control)
            assert(menu:GetEffectiveScale()==control.Control:GetEffectiveScale())
            assert(menu.lastPoint[2]==control.Control and menu:IsShown())
            control.Control:Fire("OnHide")
            assert(not menu:IsShown() and not control.Control.isOpen and next(menu.rows)==nil)
            panel:SetScale(1.2);Open(control)
            assert(menu:GetEffectiveScale()==control.Control:GetEffectiveScale())
            Choose(menu,2);assert(state.value==1 and not menu:IsShown())
        ''')

    def test_closed_font_texture_and_animation_previews_survive_dismissal(self):
        self.lua.execute(r'''
            local font=layout:CreateFontPicker(Frame(),"Font","OrbitFont",Write)
            assert(font.Control.Text.font[1]=="font/OrbitFont")
            local menu=Open(font)
            assert(menu.rows[1].Content.Text.font[1]=="font/OrbitFont")
            Choose(menu,3);assert(font.Control.Text.font[1]=="font/Other" and not font.Control.isOpen)
            local texture=layout:CreateTexturePicker(Frame(),"Texture","Smooth",Write)
            assert(texture.Control.Texture.texture=="statusbar/Smooth")
            menu=Open(texture);assert(menu.rows[4].Content.Texture.texture=="statusbar/Other")
            Choose(menu,4);assert(texture.Control.Texture.texture=="statusbar/Other")
            local frame=PreviewMenu(20);menu=Open(frame);menu:Hide()
            assert(frame.Control.Swatch.animating and frame.Control.Text:GetText()=="Glow")
        ''')

    def test_scroll_uses_bounded_stable_rows_and_does_not_refresh_when_idle(self):
        self.lua.execute(r'''
            local frame=PreviewMenu(1000);local menu=Open(frame)
            assert(state.allocations<=12 and menu.ScrollBar:IsShown())
            local row=menu.rows[3];local renders=state.renders
            menu.ScrollFrame:SetVerticalScroll(1)
            assert(menu.rows[3]==row and state.renders<=renders+1)
            renders=state.renders;Tick(180)
            assert(state.renders==renders and menu.ScrollFrame:GetVerticalScroll()==1)
            menu.ScrollFrame:Fire("OnMouseWheel",-1);Tick(180)
            local position=menu.ScrollFrame:GetVerticalScroll()
            assert(position>1 and menu.ScrollBar.scrollTarget==nil and state.allocations<=13)
            for index,slot in pairs(menu.rows) do assert(slot.Content.Text:GetText()==menu.filtered[index]) end
            renders=state.renders;Tick(180)
            assert(state.renders==renders and menu.ScrollFrame:GetVerticalScroll()==position)
        ''')

    def test_pinned_search_clear_and_refresh_keep_header_and_focus(self):
        self.lua.execute(r'''
            local frame=PreviewMenu(80);local menu=Open(frame)
            local search=menu.Search;search:SetCursorPosition(3)
            menu.ScrollFrame:Fire("OnMouseWheel",-1);Tick(3)
            search:SetText("Item079")
            assert(search:GetParent():GetParent()==menu and search:HasFocus() and search:GetCursorPosition()==3)
            assert(#menu.filtered==1 and menu.rows[1].Content.Text:GetText()=="Item079")
            assert(menu.ScrollFrame:GetVerticalScroll()==0 and not menu.ScrollBar:IsShown())
            Tick(100);assert(menu.ScrollFrame:GetVerticalScroll()==0)
            menu:RefreshItems({"Item079","Item079extra"})
            assert(#menu.filtered==2 and search:GetText()=="Item079" and search:HasFocus())
            search:SetText("");assert(#menu.filtered==2)
        ''')

    def test_dismissal_stops_scroll_and_rejects_recycled_callbacks(self):
        self.lua.execute(r'''
            local frame=PreviewMenu(80);local menu=Open(frame)
            local old=menu.rows[2]:GetScript("OnClick")
            menu.ScrollFrame:Fire("OnMouseWheel",-1);Tick(2)
            frame.Control:Hide();old();assert(state.writes==0 and not menu:IsShown())
            assert(menu.ScrollBar.scrollTarget==nil and next(menu.rows)==nil)
            frame.Control:Show();Open(frame);old();assert(state.writes==0)
            Tick(100);assert(menu.ScrollFrame:GetVerticalScroll()==0)
            menu:Fire("OnEvent","GLOBAL_MOUSE_DOWN");assert(not menu:IsShown())
            Open(frame);menu:Fire("OnKeyDown","ESCAPE");assert(not menu:IsShown())
        ''')

    def test_scrollbar_drag_and_hidden_scroll_cancellation(self):
        self.lua.execute(r'''
            local frame=PreviewMenu(80);local menu=Open(frame)
            local bar=menu.ScrollBar
            state.cursorY=500;bar:Fire("OnDragStart")
            state.cursorY=450;bar:Fire("OnUpdate",1/60)
            assert(menu.ScrollFrame:GetVerticalScroll()>0)
            bar:Fire("OnDragStop");assert(bar:GetScript("OnUpdate")==nil)
            menu.ScrollFrame:Fire("OnMouseWheel",-1)
            menu.ScrollFrame:Hide();assert(bar.scrollTarget==nil)
        ''')


if __name__ == "__main__":
    unittest.main()
