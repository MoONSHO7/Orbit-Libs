"""Execute availability, mixed values and pooled input owners; native pixels need WoW."""

from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime
from picker_menus import BOOT

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"

HARNESS = r'''
local BaseFrame = Frame
function Frame(parent, kind, template)
    local frame = BaseFrame(parent, kind, template)
    frame.level = 1
    function frame:SetAlpha(value) self.alpha = value end
    function frame:SetIgnoreParentAlpha(value) self.ignoreParentAlpha = value end
    function frame:SetPropagateMouseClicks(value) self.propagateMouseClicks = value end
    function frame:SetTextInsets(...) self.textInsets={...} end
    function frame:SetWordWrap(value) self.wordWrap=value end
    function frame:CanWordWrap() return self.wordWrap~=false end
    function frame:SetMaxLines(value) self.maxLines=value end
    function frame:SetHorizTile() end
    function frame:SetVertTile() end
    function frame:SetEnabled(value) self.enabled = value end
    function frame:Enable() self:SetEnabled(true) end
    function frame:Disable() self:SetEnabled(false) end
    function frame:GetChecked() return self.checked end
    function frame:SetCheckedTexture(value) self.checkedTexture = self.checkedTexture or Frame(self); self.checkedTexture.texture = value end
    function frame:GetCheckedTexture() return self.checkedTexture end
    function frame:GetFrameLevel() return self.level end
    function frame:SetFrameLevel(value) self.level = value end
    function frame:GetRegions() return end
    function frame:GetObjectType() return self.kind end
    function frame:GetFontString() return self end
    function frame:GetStringWidth() return #(self.text or "") * 7 end
    function frame:GetStringHeight() return math.ceil(self:GetStringWidth() / math.max(1, self:GetWidth())) * 12 end
    function frame:UnregisterCallback(event) self.events[event] = nil end
    if template == "EditModeSettingCheckboxTemplate" then
        frame.Label, frame.Button = Frame(frame, "FontString"), Frame(frame, "CheckButton")
    elseif template == "EditModeSettingSliderTemplate" then
        frame.Label, frame.Slider = Frame(frame, "FontString"), Frame(frame)
        local slider = frame.Slider
        slider.Slider, slider.Back, slider.Forward = Frame(slider), Frame(slider), Frame(slider)
        function slider:Init(value)
            self.Slider.value = value
            self.events.OnValueChanged(self, value)
        end
        function slider.Slider:GetValue() return self.value end
    end
    return frame
end
function wipe(t) for k in pairs(t) do t[k] = nil end end
Constants.UI.ValueFont = "value"
Constants.Widget.ValueInset = 4
Constants.Texture.CheckboxCheck, Constants.Texture.ReadyCheckNotReady = "check", "cross"
Tooltip.lines = {}
function Tooltip:SetText(text) self.title = text; self.lines = {} end
function Tooltip:AddLine(text) self.lines[#self.lines + 1] = text end
function Tooltip:AddDoubleLine(left,right) self.lines[#self.lines+1]=left.."  "..right end
function Tooltip:SetOwner(owner) self.owner=owner;self.lines={} end
function Tooltip:IsShown() return false end
function Tooltip:IsOwned(owner) return self.owner==owner end
'''


class ControlStates(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BOOT + HARNESS)
        for source in (
            "Config/ConfigSchema.lua", "Config/Layout.lua", "Config/LayoutControls.lua", "Config/Widgets/ConfigButton.lua",
            "Config/Widgets/ConfigReadout.lua",
            "Config/Widgets/ConfigEditBox.lua",
            "Config/Widgets/ConfigSlider.lua", "Config/Widgets/ConfigCheckbox.lua",
            "Config/Widgets/ScrollBar.lua", "Config/Pickers/MediaMenu.lua",
            "Config/Pickers/ConfigPickerControl.lua", "Config/Widgets/ConfigDropdown.lua",
            "Config/Dialogs/ConfigPanel.lua",
        ):
            self.lua.execute((RUNTIME / source).read_text(encoding="utf-8"), "Test", self.lua.globals().addon)
        self.lua.execute(r'''
            local UI = addon.LibOrbitUI
            UI.Config.ReleaseValueControls = noop
            context = {pixel = Pixel, tooltip = Tooltip, tooltipHide = noop, scrollBar = {}}
            layout = UI.Layout:Create(context, Constants)
            Mixin(layout, UI.Config)
            layout.configOptions = {constants = Constants, pixel = Pixel, tooltip = Tooltip, tooltipHide = noop}
            layout.RegisterTabsWidgetType = noop
            layout:InitializeBaseWidgetTypes()
            layout.scrollBar = UI.ScrollBar:Create(Pixel)
            layout.mediaMenu = UI.MediaMenu:CreateProvider({pixel = Pixel}, layout, Constants, function() return false end)
            layout:RegisterWidgetType("checkbox", function(parent, definition, get, change)
                return layout:CreateCheckbox(parent, definition.label, definition.tooltip, get(), change)
            end)
            layout:RegisterWidgetType("slider", function(parent, definition, get, change)
                return layout:CreateSlider(parent, definition.label, definition.min, definition.max, definition.step,
                    definition.formatter, get(), change, definition)
            end)
            layout:RegisterWidgetType("dropdown", function(parent, definition, get, change)
                return layout:CreateDropdown(parent, definition.label, definition.options, get(), change)
            end)
            layout:RegisterWidgetType("description", function(parent, definition)
                local frame = Frame(parent); frame.text = definition.text; return frame
            end)
            layout:RegisterWidgetType("test", function(parent, definition, get, change)
                local frame = Frame(parent)
                frame.definition, frame.change = definition, change
                frame.configUnavailable = state.unavailable
                return frame
            end)
            renderer = UI.ConfigPanel:Create(context, layout, Constants, {})
            container = Frame()
            function Write(value) state.writes = state.writes + 1; state.value = value end
            function Render(definition)
                return renderer:RenderControl(container, definition, function() return definition.default end, Write, Write)
            end
        ''')

    def test_dynamic_availability_blocks_all_writers_and_preserves_reason_help(self):
        self.lua.execute(r'''
            local definition = {type = "test", label = "Glow", tooltip = "Choose the effect",
                disabled = function() return state.disabled end,
                disabledReason = function() if state.disabled then return "Enable the effect first" end end,
                visibleIf = function() return not state.hidden end,
                valueColor = {callback = Write}, options = {{action = Write}}}
            local control = Render(definition)
            local picker = control.definition.valueColor.callback
            picker("first"); assert(state.writes == 1)
            state.disabled = true
            renderer:ApplyControlState(control, definition)
            control._disabledOverlay:Fire("OnEnter")
            assert(Tooltip.lines[1] == "Enable the effect first\nChoose the effect")
            picker("blocked"); control.change("blocked"); control.definition.options[1].action("blocked")
            assert(state.writes == 1)
            state.disabled = false; state.hidden = true; picker("hidden"); assert(state.writes == 1)
            state.hidden = false; control:Hide(); picker("hidden ancestor"); assert(state.writes == 1)
            control:Show(); picker("restored"); assert(state.writes == 2)
            layout:ReleaseControl(control); picker("released"); assert(state.writes == 2)
            assert(addon.LibOrbitUI.Config.GetDisabledReason(definition) == nil)
            state.disabled = true
            local disabled = Render(definition)
            assert(#layout.containerControls[container] == 2,"Disabled reasons never add a body row")
        ''')

    def test_unavailable_widgets_and_is_enabled_reject_commits(self):
        self.lua.execute(r'''
            state.unavailable = true
            local control = Render({type = "test", label = "Colour"})
            control.change(1); assert(state.writes == 0)
            state.unavailable = false
            local definition = {type = "test", label = "Feature", isEnabled = false}
            control = Render(definition); control.change(2); assert(state.writes == 0)
            definition.isEnabled = true; control.change(3); assert(state.writes == 1)
            definition.disabled = true
            addon.LibOrbitUI.Config.CommitValue({set = Write}, definition, 4)
            assert(state.writes == 1)
        ''')

    def test_real_slider_mixed_and_disabled_to_enabled_pool_reuse(self):
        self.lua.execute(r'''
            local definition = {type = "slider", label = "Width", default = 10, min = 1, max = 100, step = 1,
                mixed = true, mixedText = "Mixed", disabled = true}
            local control = Render(definition)
            assert(control.Value:GetText() == "Mixed" and not control.Slider.enabled and state.writes == 0)
            local stale = control.OnOrbitChange
            control.Slider.events.OnValueChanged(control.Slider, 15)
            assert(state.writes == 0 and control.Value:GetText() == "Mixed")
            layout:Reset(container)
            assert(control.Slider.enabled and control.alpha == 1 and not control._disabledOverlay:IsShown())
            definition.disabled = false
            local reused = Render(definition)
            assert(reused == control and control.Value:GetText() == "Mixed" and control.Slider.enabled)
            stale(18); assert(state.writes == 0)
            control.Slider.events.OnValueChanged(control.Slider, 20)
            assert(state.writes == 1 and state.value == 20 and not control.configMixed)
            assert(control.Value:GetText() == 20)
        ''')

    def test_checkbox_mixed_is_indeterminate_until_explicit_click(self):
        self.lua.execute(r'''
            local definition = {type = "checkbox", label = "Show", default = true, mixed = true, mixedText = "Mixed"}
            local control = Render(definition)
            assert(not control:GetChecked() and control.configMixedMark:IsShown())
            assert(control.Label:GetText() == "Show (Mixed)" and state.writes == 0)
            control._cb:SetChecked(true); control._cb:Fire("OnClick")
            assert(state.writes == 1 and state.value == true and not control.configMixedMark:IsShown())
            assert(control.Label:GetText() == "Show")
            layout:Reset(container); definition.mixed = false
            local reused = Render(definition)
            assert(reused == control and control:GetChecked() and not control.configMixedMark:IsShown())
        ''')

    def test_dropdown_mixed_does_not_claim_first_value_and_footer_actions_guard(self):
        self.lua.execute(r'''
            local definition = {type = "dropdown", label = "Orientation", default = 1, mixed = true,
                mixedText = "Mixed", options = {{text = "Horizontal", value = 1}, {text = "Vertical", value = 2}}}
            local control = Render(definition)
            assert(control.Control.Text:GetText() == "Mixed" and state.writes == 0)
            control.Control:Fire("OnClick")
            assert(not control.Dropdown.rows[1].Selected:IsShown() and not control.Dropdown.rows[2].Selected:IsShown())
            control.Dropdown.rows[2]:Fire("OnClick")
            assert(state.writes == 1 and not control.configMixed and control.Control.Text:GetText() == "Vertical")
            local action = {label = "Add", disabled = function() return state.full end, onClick = Write}
            local bound = addon.LibOrbitUI.Config.BindDefinition(action, function() return true end)
            local button = layout:CreateButton(container, action.label, bound.onClick)
            state.full = true; renderer:ApplyControlState(button, action)
            button:Fire("OnClick"); assert(state.writes == 1 and not button.enabled)
            state.full = false; renderer:ApplyControlState(button, action)
            button:Fire("OnClick"); assert(state.writes == 2 and button.enabled)
        ''')

    def test_readout_source_scope_and_action_have_no_value_writer_or_recycled_owner(self):
        self.lua.execute(r'''
            local definition = {type = "readout", key = "Width", label = "Width", default = 180,
                formatter = function(value) return value .. " logical units" end,
                sourceText = function() return "Synced to Target" end, scopeText = "This frame",
                actionText = "Change source", onAction = Write}
            local control = Render(definition)
            local metadata = layout.containerControls[container][2]
            assert(control.Value:GetText() == "180 logical units" and control.Label:GetText() == "Width")
            assert(metadata.text:GetText() == "")
            control._tooltipHover:Fire("OnEnter")
            assert(Tooltip.lines[1] == "This frame\nSynced to Target")
            assert(control._tooltipHover.allPoints==control.Label and control._tooltipHover.propagateMouseClicks)
            assert(metadata.Action:GetText() == "Change source")
            addon.LibOrbitUI.Config.CommitValue({set = Write}, definition, 300)
            assert(state.writes == 0)
            local stale = metadata.onAction
            metadata.Action:Fire("OnClick"); assert(state.writes == 1)
            layout:Reset(container)
            local nextControl = Render({type = "readout", label = "Height", default = 40, sourceText = "Docked"})
            assert(nextControl == control and #layout.containerControls[container]==1)
            assert(control.Value:GetText() == "40")
            control._tooltipHover:Fire("OnEnter");assert(Tooltip.lines[1]=="Docked")
            assert(not metadata.Action:IsShown() and metadata.onAction == nil)
            stale(); assert(state.writes == 1)
        ''')

    def test_metadata_inheritance_obeys_disabled_and_hidden_parent(self):
        self.lua.execute(r'''
            local definition = {type = "slider", key = "Width", label = "Width", default = 40,
                min = 1, max = 100, step = 1, inheritText = "Use Base", onInherit = Write,
                disabled = function() return state.disabled end}
            local control = Render(definition)
            local metadata = layout.containerControls[container][2]
            local action = metadata.onAction
            action(); assert(state.writes == 1)
            action = metadata.onAction
            state.disabled = true; action(); assert(state.writes == 1)
            state.disabled = false; control:Hide(); action(); assert(state.writes == 1)
            control:Show(); action(); assert(state.writes == 2)
        ''')

    def test_additional_metadata_actions_share_parent_guard_and_release_every_callback(self):
        self.lua.execute(r'''
            local definition = {type = "readout", label = "Colour", default = "Blue",
                inheritText = "Use global", onInherit = Write,
                metadataActions = {{text = "Use Base", callback = Write}, {text = "Hidden", visible = false, callback = Write}}}
            local control = Render(definition)
            local controls = layout.containerControls[container]
            assert(#controls == 3 and controls[3].Action:GetText() == "Use Base")
            local primary, extra = controls[2].onAction, controls[3].onAction
            primary(); controls[3].onAction(); assert(state.writes == 2)
            primary, extra = controls[2].onAction, controls[3].onAction
            definition.disabled = true; primary(); extra(); assert(state.writes == 2)
            definition.disabled = false; definition.metadataActions[1].disabled = true
            primary(); extra(); assert(state.writes == 3)
            definition.metadataActions[1].disabled = false
            extra = controls[3].onAction
            control:Hide(); extra(); assert(state.writes == 3)
            control:Show(); extra(); assert(state.writes == 4)
            layout:Reset(container)
            primary(); extra(); assert(state.writes == 4)
            for _, metadata in ipairs(layout.controlMetadataPool) do assert(metadata.onAction == nil) end
        ''')

    def test_commits_refresh_metadata_without_replacing_input_or_retaining_old_actions(self):
        self.lua.execute(r'''
            local definition = {type="slider",label="Width",default=20,min=1,max=100,step=1}
            definition.refreshPresentation = function()
                return {sourceText=state.value and "Local override" or "Inherited from Base",
                    inheritText=state.value and "Use Base" or nil,
                    onInherit=function() state.value=nil;state.writes=state.writes+1 end}
            end
            local control=Render(definition)
            local trailing=Render({type="readout",label="Height",default=40})
            local changes=0; container.configRelayout=function()changes=changes+1 end
            control._tooltipHover:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Inherited from Base" and #layout.containerControls[container]==2)
            control.Slider.events.OnValueChanged(control.Slider,30)
            local metadata=layout.containerControls[container][2]
            control._tooltipHover:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Local override" and metadata.Action:IsShown())
            local stale=metadata.onAction
            control.Slider.events.OnValueChanged(control.Slider,31)
            assert(state.value==31 and state.writes==2 and layout.containerControls[container][1]==control)
            stale();assert(state.value==31 and state.writes==2)
            metadata.onAction()
            assert(state.value==nil and state.writes==3 and not metadata:IsShown())
            control._tooltipHover:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Inherited from Base" and layout.containerControls[container][3]==trailing)
            local own=Render({type="test",label="Colour",valueColor={callback=Write},
                sourceText=function()return state.value and "Own colour" or "Global colour"end,
                inheritText=function()return state.value and "Use global" or nil end,
                onInherit=function()state.value=nil end})
            own.definition.valueColor.callback("red")
            local details=layout.containerControls[container][5]
            own._tooltipHover:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Own colour" and details.Action:IsShown())
            details.onAction()
            own._tooltipHover:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Global colour" and not details:IsShown())
        ''')

    def test_metadata_remeasures_text_when_pool_width_stays_the_same(self):
        self.lua.execute(r'''
            local frame = layout:CreateControlMetadata(container, "Short")
            local height = frame:GetHeight()
            layout:ReleaseControl(frame)
            local reused = layout:CreateControlMetadata(container, string.rep("A long inherited source ", 20))
            assert(reused == frame and frame:GetHeight() > height)
            frame:SetSize(100, frame:GetHeight())
            assert(frame.text:GetWidth() == 100)
        ''')

    def test_primary_buttons_refresh_metadata_and_reject_refresh_after_pooled_rebinding(self):
        self.lua.execute(r'''
            local definition={type="button",label="Change source",
                disabled=function()return state.disabled end,
                sourceText=function()return state.value and "After" or "Before"end}
            local button=Render(definition)
            local click=button:GetScript("OnClick")
            click()
            button._tooltipHover:Fire("OnEnter")
            assert(state.writes==1 and Tooltip.lines[1]=="After" and #layout.containerControls[container]==1)
            assert(layout.containerControls[container][1]==button,"The primary input survives its accepted action")
            state.disabled=true;click();assert(state.writes==1)
            state.disabled=false;button:Hide();click();assert(state.writes==1)
            layout:Reset(container);click();assert(state.writes==1)
            local reads=0
            local outgoing=renderer:RenderControl(container,{type="button",label="Rebind",
                sourceText=function()reads=reads+1;return "Outgoing"end},nil,nil,function()
                    layout:Reset(container)
                    Render({type="button",label="Incoming",sourceText="Incoming"})
                end)
            outgoing._tooltipHover:Fire("OnEnter")
            outgoing:Fire("OnClick")
            local incoming=layout.containerControls[container][1]
            incoming._tooltipHover:Fire("OnEnter")
            assert(reads==1,"Post-action refresh cannot read a definition after its control was rebound")
            assert(Tooltip.lines[1]=="Incoming")
        ''')

    def test_metadata_only_presentation_cannot_enable_a_disabled_parent_action(self):
        self.lua.execute(r'''
            local definition={type="slider",label="Width",default=20,min=1,max=100,step=1,
                disabled=function()return state.disabled end,
                refreshPresentation=function()return {sourceText="Local override",inheritText="Use Base",
                    onInherit=Write,isEnabled=not state.actionDisabled}end}
            state.disabled=true
            local control=Render(definition)
            local metadata=layout.containerControls[container][2]
            assert(not control.Slider.enabled and not metadata.Action.enabled)
            metadata.onAction();assert(state.writes==0)
            state.disabled=false
            renderer:ApplyControlState(control,definition)
            control.Slider.events.OnValueChanged(control.Slider,30)
            assert(control.Slider.enabled and metadata.Action.enabled and state.writes==1)
            state.actionDisabled=true
            control.Slider.events.OnValueChanged(control.Slider,31)
            assert(control.Slider.enabled and not metadata.Action.enabled and state.writes==2)
            metadata.onAction();assert(state.writes==2)
        ''')

    def test_dynamic_metadata_inserts_beside_owner_and_reuses_hidden_rows(self):
        self.lua.execute(r'''
            local definition={type="test",label="Optional override",
                sourceText=function()return state.value and "Override"end,
                inheritText=function()return state.value and "Use global"end,
                onInherit=function()state.value=nil end}
            local owner=Render(definition)
            local trailing=Render({type="readout",label="Next setting",default=100})
            local layouts=0;container.configRelayout=function()layouts=layouts+1 end
            owner.change("red")
            local controls=layout.containerControls[container]
            local metadata=controls[2]
            assert(#controls==3 and controls[1]==owner and controls[3]==trailing and layouts==1)
            metadata.onAction()
            assert(not metadata:IsShown() and metadata.onAction==nil and layouts==2)
            owner.change("blue")
            assert(#controls==3 and controls[2]==metadata and metadata:IsShown() and layouts==3)
            layout:Reset(container)
            assert(container.configRelayout==nil and #layout.controlMetadataPool==1)
        ''')

    def test_panel_keeps_common_scope_in_hover_and_explains_empty_schemas(self):
        self.lua.execute(r'''
            Constants.Panel = {ContentPadding=4,ScrollbarWidth=10,MaxHeight=500,TitlePadding=20,DialogWidth=340}
            function RunNextFrame(callback) callback() end
            local dialog=Frame()
            local panel=Frame(dialog)
            panel.configPanelOwner=renderer
            panel.Content=Frame(panel); panel.ScrollFrame=Frame(panel); panel.Header=Frame(panel)
            panel.Footer=Frame(panel); panel.HeaderDivider=Frame(panel.Header); panel.Tabs={}
            local options={controls={{type="readout",label="Width",default=100}},scopeText="This frame",
                emptyText="Move this frame in Edit Mode",cache=false,renderFooter=function()return 0 end}
            options.renderControl=function(target,def)
                return renderer:RenderControl(target,def,function()return def.default end)
            end
            renderer:Render(panel,options)
            local controls=layout.containerControls[panel.Content]
            assert(#controls==1 and controls[1].Value:GetText()=="100")
            controls[1]._tooltipHover:Fire("OnEnter");assert(Tooltip.lines[1]=="This frame")
            options.controls={}
            renderer:Render(panel,options)
            controls=layout.containerControls[panel.Content]
            assert(#controls==1 and controls[1].text=="Move this frame in Edit Mode")
        ''')

    def test_tooltips_preserve_format_help_deduplicate_details_and_allow_nil_providers(self):
        self.lua.execute(r'''
            local definition={type="formatinput",label="Format",default="{name}",
                tooltip=function()return nil end,
                tooltipLines={{title="Format help"},{hint="This layout"},{key="{name}",value="Name"}},
                sourceText="Inherited from global",scopeText="This layout",
                disabledReason="Enable the component",preview=function(text)return "Preview: "..text end}
            local control=Render(definition)
            assert(#layout.containerControls[container]==1,"Passive help never creates rows")
            control.EditBox:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Format" and Tooltip.lines[2]=="Preview: {name}")
            assert(Tooltip.lines[4]=="Format help" and Tooltip.lines[6]=="{name}  Name")
            control._tooltipHover:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Format help\nThis layout\n{name}  Name\nInherited from global")
            definition.disabled=true;renderer:ApplyControlState(control,definition)
            control._disabledOverlay:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Enable the component\nFormat help\nThis layout\n{name}  Name\nInherited from global")
            local action={label="Add",disabled=true,disabledReason="Limit reached",tooltip="Choose a slot",scopeText="Account"}
            local button=layout:CreateButton(container,action.label,Write)
            renderer:ApplyControlState(button,action)
            button._disabledOverlay:Fire("OnEnter")
            assert(Tooltip.lines[1]=="Limit reached\nChoose a slot\nAccount")
            local empty=Render({type="checkbox",label="Optional help",default=false,tooltip=function()return nil end})
            local shows=state.tooltips
            empty._tooltipHover:Fire("OnEnter");empty._cb:Fire("OnEnter")
            assert(state.tooltips==shows,"A nil tooltip provider does not create an empty or invalid tooltip")
        ''')

    def test_inline_colour_source_keeps_row_height_and_restores_pooled_width_policy(self):
        for source in ("Config/ConfigPickerWidgets.lua", "Config/Pickers/ConfigColorPicker.lua"):
            self.lua.execute((RUNTIME/source).read_text(encoding="utf-8"),"Test",self.lua.globals().addon)
        self.lua.execute(r'''
            Constants.Widget.ValueSwatchSize=20
            addon.LibOrbitUI.Config.InstallPickerWidgets(layout,{color={open=function()end}})
            state.source="Using global value"
            local definition={type="color",label="Health colour",inlineSource=true,
                sourceText=function()return state.source end,
                refreshPresentation=function()return {sourceText=function()return state.source end}end}
            local control=Render(definition)
            local text=control.configInlineSource
            local height=control:GetHeight()
            assert(text:GetText()==state.source and text:IsShown() and not control.OrbitHalfWidth)
            assert(not control.Label:CanWordWrap() and not text:CanWordWrap() and text.maxLines==1)
            assert(#layout.containerControls[container]==1 and height==32)
            control:SetSize(340,height)
            assert(control.Label:GetWidth()==control.Label:GetUnboundedStringWidth())
            assert(text.lastPoint[2]==control.Label and text.lastPoint[3]=="RIGHT")
            control.Label:SetText(string.rep("Localized colour label ",4))
            control:SetSize(88,height)
            assert(control.Label:GetWidth()<control.Label:GetUnboundedStringWidth())
            assert(control.Label:GetWidth()+text:GetWidth()+20+Constants.Widget.LabelGap+6<=88)
            assert(control:GetHeight()==height and #layout.containerControls[container]==1)
            control._tooltipHover:Fire("OnEnter")
            assert(Tooltip.lines[1]==state.source,"Clipped annotations retain the full hover explanation")
            local layouts=0;container.configRelayout=function()layouts=layouts+1 end
            state.source="Local override";control.UpdateColor(1,0,0,1)
            assert(text:GetText()==state.source and control:GetHeight()==height and layouts==0)
            state.source=nil;control.UpdateColor(0,1,0,1)
            assert(not text:IsShown() and control.OrbitHalfWidth and control.Label:CanWordWrap())
            assert(control.Label:GetWidth()==Constants.Widget.LabelWidth and layouts==1)
            state.source="Using global value";control.UpdateColor(0,0,1,1)
            assert(text:IsShown() and not control.OrbitHalfWidth and layouts==2)
            layout:Reset(container)
            assert(not text:IsShown() and text:GetText()=="" and control.configInlineSourceState==nil)
            local ordinary=Render({type="color",label="Plain colour",inlineSource=false,sourceText="Hover only"})
            assert(ordinary==control and ordinary.OrbitHalfWidth and ordinary.Label:CanWordWrap())
            assert(ordinary.Label:GetWidth()==Constants.Widget.LabelWidth and not text:IsShown())
            assert(#ordinary.hooks.OnSizeChanged==1,"Pool reuse never accumulates resize hooks")
        ''')


class TextureSwatchStates(unittest.TestCase):
    def setUp(self):
        ControlStates.setUp(self)
        self.lua.execute(r'''
            local BaseFrame = Frame
            function Frame(parent, kind, template)
                local frame = BaseFrame(parent, kind, template)
                function frame:RegisterForClicks(...) self.clicks = {...} end
                function frame:SetGradient(direction, first, last) self.gradient = {direction, first, last} end
                function frame:SetVertexColor(...) self.vertexColor = {...} end
                function frame:SetTexCoord(...) self.texCoords = {...} end
                if template == "UICheckButtonTemplate" then
                    frame.normalTexture, frame.pushedTexture, frame.highlightTexture = Frame(frame), Frame(frame), Frame(frame)
                    frame.checkedTexture, frame.disabledCheckedTexture = Frame(frame), Frame(frame)
                    function frame:GetNormalTexture() return self.normalTexture end
                    function frame:GetPushedTexture() return self.pushedTexture end
                    function frame:GetHighlightTexture() return self.highlightTexture end
                    function frame:GetDisabledCheckedTexture() return self.disabledCheckedTexture end
                end
                return frame
            end
            function CreateColor(r, g, b, a) return {r = r, g = g, b = b, a = a} end
            function Tooltip:GetOwner() return self.owner end
            function Tooltip:Hide() self.owner = nil; state.tooltipHides = (state.tooltipHides or 0) + 1 end
            Constants.Widget.ValueWidth = 80
            Constants.Widget.LabelGap = 3
            Constants.Widget.ValueInset = 3
            Constants.Widget.ValueSwatchSize = 21
            Constants.Widget.ValueCheckboxSize = 26
            state.opens, state.closed, state.colorWrites = {}, {}, {}
        ''')
        for source in (
            "Config/ConfigPickerWidgets.lua", "Config/Widgets/ConfigValueSwatch.lua",
            "Config/Pickers/ConfigTexturePicker.lua", "Config/Pickers/ConfigColorCurvePicker.lua",
        ):
            self.lua.execute((RUNTIME / source).read_text(encoding="utf-8"), "Test", self.lua.globals().addon)
        self.lua.execute(r'''
            Mixin(layout, addon.LibOrbitUI.Config)
            addon.LibOrbitUI.Config.InstallPickerWidgets(layout, {
                color = {
                    checkerboard = "checkerboard",
                    open = function(owner, options)
                        state.opens[#state.opens + 1] = {owner = owner, options = options}
                    end,
                    close = function(owner) state.closed[owner] = (state.closed[owner] or 0) + 1 end,
                },
                media = {defaultTexture = "Smooth", noneLabel = "None",
                    fetch = function(kind, name) return kind .. "/" .. name end,
                    isValid = function() return true end, list = function() return {"Smooth"} end},
            })
            function Curve(red, alpha)
                return {pins = {
                    {position = 1, color = {r = red, g = 0, b = 0, a = alpha}},
                    {position = 0, color = {r = 0, g = 0, b = 1, a = alpha}},
                }}
            end
            function Swatch(label, value)
                return {curve = true, initialValue = value, tooltip = label, callback = function(result)
                    state.colorWrites[label] = result
                    state.writes = state.writes + 1
                end}
            end
            function TextureDefinition()
                return {type = "texture", label = "Texture", default = "Smooth",
                    valueColors = {Swatch("Unit Health", Curve(1, 1)), Swatch("Background", Curve(0.3, 0.4))},
                    valueCheckbox = {initialValue = false, tooltip = "Use health gradient",
                        callback = function(value) state.gradient = value; state.writes = state.writes + 1 end}}
            end
            function HorizontalBounds(frame)
                local points = frame.points or {}
                local function Position(point)
                    local left, right = HorizontalBounds(point[2])
                    local anchor = point[3]
                    local x = anchor:find("LEFT") and left or anchor:find("RIGHT") and right or (left + right) / 2
                    return x + (point[4] or 0)
                end
                if points.LEFT and points.RIGHT then return Position(points.LEFT), Position(points.RIGHT) end
                if points.LEFT then local x = Position(points.LEFT); return x, x + frame:GetWidth() end
                if points.RIGHT then local x = Position(points.RIGHT); return x - frame:GetWidth(), x end
                if points.CENTER then local x = Position(points.CENTER); return x - frame:GetWidth()/2, x + frame:GetWidth()/2 end
                return 0, frame:GetWidth()
            end
        ''')

    def test_independent_curve_editors_and_hover_labels_share_one_texture_row(self):
        self.lua.execute(r'''
            local definition = TextureDefinition()
            local control = Render(definition)
            local health, background = unpack(control.ValueColorSwatches)
            assert(#layout.containerControls[container] == 1 and control:GetHeight() == 32)
            assert(health ~= background and health:IsShown() and background:IsShown())
            for index, swatch in ipairs({health, background}) do
                swatch:Fire("OnEnter")
                assert(Tooltip.title == definition.valueColors[index].tooltip and Tooltip.owner == swatch)
                swatch:Fire("OnClick", "LeftButton")
                assert(state.opens[index].owner == swatch)
                assert(state.opens[index].options.initialData == definition.valueColors[index].initialValue)
                assert(not state.opens[index].options.forceSingleColor)
            end
            assert(health.Color.gradient[2].b == 1 and health.Color.gradient[3].r == 1)
            assert(background.Color.gradient[2].a == 0.4 and background.Checkerboard.texture == "checkerboard")
            assert(definition.valueColors[1].initialValue.pins[1].position == 1, "Preview does not mutate saved pin order")
            local firstResult, secondResult = Curve(0.6, 1), Curve(0.2, 0.5)
            firstResult.desaturated = true
            state.opens[1].options.callback(firstResult, false)
            assert(state.colorWrites["Unit Health"].pins == firstResult.pins and state.colorWrites.Background == nil)
            assert(state.colorWrites["Unit Health"].desaturated == true)
            state.opens[2].options.callback(secondResult, false)
            assert(state.colorWrites.Background.pins == secondResult.pins and state.writes == 2)
            assert(health.value.pins == firstResult.pins and background.value.pins == secondResult.pins)
            control.ValueCheckbox:SetChecked(true); control.ValueCheckbox:Fire("OnClick")
            assert(state.gradient == true and state.writes == 3)
        ''')

    def test_value_groups_grow_left_from_the_right_edge_when_resized_or_reused(self):
        self.lua.execute(r'''
            for count = 3, 1, -1 do
                local definition = TextureDefinition()
                if count < 3 then table.remove(definition.valueColors) end
                if count == 1 then definition.valueCheckbox = nil end
                local control = Render(definition)
                local accessories = {}
                if count > 1 then
                    accessories[#accessories + 1] = control.ValueCheckbox
                    assert(control.ValueCheckbox:GetWidth() == Constants.Widget.ValueCheckboxSize)
                    assert(control.ValueCheckbox:GetNormalTexture().texCoords == nil, "Keep native checkbox artwork uncropped")
                end
                accessories[#accessories + 1] = control.ValueColorSwatches[1]
                if count == 3 then accessories[#accessories + 1] = control.ValueColorSwatches[2] end
                for _, width in ipairs({500, 340}) do
                    control:SetWidth(width)
                    local pickerRight = select(2, HorizontalBounds(control.Control))
                    local lastRight = pickerRight
                    for _, accessory in ipairs(accessories) do
                        local left, right = HorizontalBounds(accessory)
                        assert(left >= lastRight, "Value controls must not overlap the picker or each other")
                        assert(right <= width, "Accessories must remain inside their row")
                        lastRight = right
                    end
                    assert(lastRight == width - Constants.Widget.ValueInset,
                        "One, two and three controls share the same right edge")
                end
                layout:Reset(container)
            end
        ''')

    def test_standalone_curve_picker_retains_endpoint_alpha_and_legacy_solid_preview(self):
        self.lua.execute(r'''
            local data = Curve(0.7, 0.35)
            local control = Render({type = "colorcurve", label = "Curve", default = data})
            local gradient = control.GradientTexture.gradient
            assert(gradient[1] == "HORIZONTAL" and gradient[2].b == 1 and gradient[3].r == 0.7)
            assert(gradient[2].a == 0.35 and gradient[3].a == 0.35 and data.pins[1].position == 1)
            layout:Reset(container)
            local legacy = Render({type = "colorcurve", label = "Legacy", default = {r = 0.2, g = 0.3, b = 0.4, a = 0.5}})
            assert(legacy == control)
            gradient = legacy.GradientTexture.gradient
            assert(gradient[2].r == 0.2 and gradient[3].b == 0.4 and gradient[2].a == 0.5 and gradient[3].a == 0.5)
        ''')

    def test_pooled_array_to_absorb_to_plain_row_expires_every_editor_and_hover(self):
        self.lua.execute(r'''
            local control = Render(TextureDefinition())
            local health, background = unpack(control.ValueColorSwatches)
            health:Fire("OnClick", "LeftButton"); background:Fire("OnClick", "LeftButton")
            background:Fire("OnEnter")
            layout:Reset(container)
            assert(state.closed[health] and state.closed[background] and Tooltip.owner == nil)
            assert(not health:IsShown() and not background:IsShown())
            assert(health:GetScript("OnEnter") == nil and background:GetScript("OnClick") == nil)
            local absorb = Render({type = "texture", label = "Absorb", default = "Smooth",
                valueColor = {initialValue = {r = 0, g = 1, b = 1, a = 1}, tooltip = "Absorb", callback = Write},
                valueCheckbox = {initialValue = true, tooltip = "Show absorb", callback = Write}})
            assert(absorb == control and absorb.ValueColorSwatch:IsShown() and absorb.ValueCheckbox:GetChecked())
            assert(not health:IsShown() and not background:IsShown())
            for _, open in ipairs(state.opens) do open.options.callback(Curve(0.8, 1), false) end
            assert(state.writes == 0, "Recycled curve editors cannot write into the old or new row")
            absorb.ValueColorSwatch:Fire("OnEnter"); assert(Tooltip.title == "Absorb")
            absorb.ValueColorSwatch:Fire("OnClick", "LeftButton")
            local solidEditor = state.opens[#state.opens].options
            assert(solidEditor.forceSingleColor)
            solidEditor.callback({pins = {{color = {r = 0.2, g = 0.5, b = 1, a = 0.7}}}}, false)
            assert(state.writes == 1 and state.value.g == 0.5 and state.value.a == 0.7)
            layout:Reset(container)
            local plain = Render({type = "texture", label = "Overlay", default = "Smooth"})
            assert(plain == control and not plain.ValueColorSwatch:IsShown() and not plain.ValueCheckbox:IsShown())
            assert(not health:IsShown() and not background:IsShown())
            solidEditor.callback({pins = {{color = {r = 1}}}}, false); assert(state.writes == 1)
            layout:Reset(container)
            local again = Render(TextureDefinition())
            assert(again == control and again.ValueColorSwatches[1] == health and again.ValueColorSwatches[2] == background)
            assert(health:IsShown() and background:IsShown() and not again.ValueColorSwatch:IsShown())
            health:Fire("OnEnter"); assert(Tooltip.title == "Unit Health")
            health:Fire("OnClick", "LeftButton")
            state.opens[#state.opens].options.callback(Curve(0.4, 1), false)
            assert(state.writes == 2 and state.colorWrites["Unit Health"])
        ''')

    def test_deferred_array_writes_obey_parent_and_child_availability(self):
        self.lua.execute(r'''
            local definition = TextureDefinition()
            definition.disabled = function() return state.disabled end
            definition.valueColors[2].disabled = function() return state.backgroundDisabled end
            local control = Render(definition)
            control.ValueColorSwatches[1]:Fire("OnClick", "LeftButton")
            control.ValueColorSwatches[2]:Fire("OnClick", "LeftButton")
            local health, background = state.opens[1].options.callback, state.opens[2].options.callback
            state.disabled = true
            health(Curve(0.1, 1), false); background(Curve(0.2, 1), false)
            assert(state.writes == 0)
            state.disabled = false; state.backgroundDisabled = true
            health(Curve(0.3, 1), false); background(Curve(0.4, 1), false)
            assert(state.writes == 1 and state.colorWrites.Background == nil)
            control:Hide(); health(Curve(0.5, 1), false); assert(state.writes == 1)
            control:Show(); state.backgroundDisabled = false
            background(Curve(0.6, 1), true); assert(state.writes == 1)
            background(Curve(0.7, 1), false); assert(state.writes == 2)
        ''')


class CheckboxSwatchStates(unittest.TestCase):
    def setUp(self):
        TextureSwatchStates.setUp(self)
        self.lua.execute(r'''
            layout:InitializeBaseWidgetTypes()
            function CheckboxColorDefinition()
                local swatch = Swatch("Frame colour", {pins = {{position = 0,
                    color = {r = 0.7, g = 0.6, b = 1, a = 1}}}})
                swatch.singleColor = true
                return {type = "checkbox", label = "Show frames", default = true,
                    disabled = function() return state.disabled end, valueColor = swatch}
            end
        ''')

    def test_checkbox_value_swatch_keeps_single_colour_curve_and_separate_hit_targets(self):
        self.lua.execute(r'''
            local definition = CheckboxColorDefinition()
            definition.valueText = function() return "Ready" end
            local control = Render(definition)
            local swatch = control.ValueColorSwatch
            assert(#layout.containerControls[container] == 1 and control:GetHeight() == 30)
            assert(control:GetChecked() and swatch:IsShown() and control.ValueText:GetText() == "Ready")
            for _, width in ipairs({500, 340}) do
                control:SetWidth(width)
                local labelRight = select(2, HorizontalBounds(control.Label))
                local textLeft, textRight = HorizontalBounds(control.ValueText)
                local swatchLeft, swatchRight = HorizontalBounds(swatch)
                assert(labelRight <= textLeft and textRight < swatchLeft and swatchRight <= width)
                assert(swatchRight == width - Constants.Widget.ValueInset)
            end
            swatch:Fire("OnEnter"); assert(Tooltip.title == "Frame colour" and Tooltip.owner == swatch)
            swatch:Fire("OnClick", "LeftButton")
            local editor = state.opens[1].options
            assert(editor.forceSingleColor and editor.initialData == definition.valueColor.initialValue)
            local result = {pins = {{position = 0, color = {r = 0.2, g = 0.3, b = 0.4, a = 0.5}}}}
            editor.callback(result, false)
            assert(state.colorWrites["Frame colour"].pins == result.pins and control:GetChecked())
            control.Button:SetChecked(false); control.Button:Fire("OnClick")
            assert(state.value == false and state.writes == 2)
        ''')

    def test_checkbox_swatch_guards_writes_and_expires_on_plain_checkbox_reuse(self):
        self.lua.execute(r'''
            local definition = CheckboxColorDefinition()
            local control = Render(definition)
            local swatch = control.ValueColorSwatch
            swatch:Fire("OnClick", "LeftButton")
            local commit = state.opens[1].options.callback
            state.disabled = true
            renderer:ApplyControlState(control, definition)
            commit(Curve(0.3, 1), false); assert(state.writes == 0 and control._disabledOverlay:IsShown())
            state.disabled = false
            renderer:ApplyControlState(control, definition)
            commit(Curve(0.4, 1), false); assert(state.writes == 1 and not control._disabledOverlay:IsShown())
            swatch:Fire("OnEnter")
            layout:Reset(container)
            assert(state.closed[swatch] and Tooltip.owner == nil)
            local plain = Render({type = "checkbox", label = "Anchoring", default = true})
            assert(plain == control and not swatch:IsShown() and swatch:GetScript("OnClick") == nil)
            assert(plain.Label.points.RIGHT[4] == 0 and (not plain.ValueText or not plain.ValueText:IsShown()))
            commit(Curve(0.5, 1), false); assert(state.writes == 1)
            layout:Reset(container)
            local again = Render(CheckboxColorDefinition())
            assert(again == control and again.ValueColorSwatch == swatch and swatch:IsShown())
            swatch:Fire("OnClick", "LeftButton")
            state.opens[2].options.callback(Curve(0.6, 1), false)
            assert(state.writes == 2)
        ''')


class CheckboxAccessoryStates(unittest.TestCase):
    def setUp(self):
        TextureSwatchStates.setUp(self)
        self.lua.execute(r'''
            layout:RegisterWidgetType("accessories", function(parent, definition, get, change)
                local frame = layout:CreateTexturePicker(parent, definition.label, get(), change,
                    nil, definition.valueCheckbox)
                if definition.valueCheckboxes then
                    local controls = layout:ApplyValueCheckboxes(frame, definition.valueCheckboxes)
                    layout:LayoutValueControls(frame, unpack(controls))
                end
                return frame
            end)
            function CheckboxDefinition()
                return {type = "accessories", label = "Cooldown Swipe", default = "Smooth",
                    disabled = function() return state.disabled end,
                    valueCheckboxes = {
                        {initialValue = function() return state.inverse or false end, tooltip = "Inverse Swipe",
                            callback = function(value) state.inverse = value; state.writes = state.writes + 1 end},
                        {initialValue = false, tooltip = "Counterclockwise Swipe",
                            disabled = function() return state.directionDisabled end,
                            disabledReason = "Direction unavailable",
                            callback = function(value) state.direction = value; state.writes = state.writes + 1 end},
                    }}
            end
        ''')

    def test_independent_checkboxes_preserve_order_tooltips_and_native_art(self):
        self.lua.execute(r'''
            local definition = CheckboxDefinition()
            local control = Render(definition)
            local inverse, direction = unpack(control.ValueCheckboxes)
            for index, checkbox in ipairs(control.ValueCheckboxes) do
                assert(checkbox:GetWidth() == Constants.Widget.ValueCheckboxSize)
                assert(checkbox:GetNormalTexture().texCoords == nil)
                checkbox:Fire("OnEnter")
                assert(Tooltip.title == definition.valueCheckboxes[index].tooltip and Tooltip.owner == checkbox)
            end
            inverse:SetChecked(true); inverse:Fire("OnClick")
            assert(state.inverse and state.direction == nil and state.writes == 1)
            direction:SetChecked(true); direction:Fire("OnClick")
            assert(state.direction and state.writes == 2)
            for _, width in ipairs({340, 500}) do
                control:SetWidth(width)
                local firstLeft, firstRight = HorizontalBounds(inverse)
                local secondLeft, secondRight = HorizontalBounds(direction)
                assert(firstLeft >= 0 and firstRight + Constants.Widget.LabelGap == secondLeft)
                assert(secondRight == width - Constants.Widget.ValueInset)
            end
        ''')

    def test_parent_child_hidden_and_expired_bindings_reject_writes(self):
        self.lua.execute(r'''
            local definition = CheckboxDefinition()
            local control = Render(definition)
            local inverse, direction = unpack(control.ValueCheckboxes)
            state.disabled = true
            renderer:ApplyControlState(control, definition)
            assert(not inverse.enabled and not direction.enabled)
            inverse:Fire("OnClick"); direction:Fire("OnClick"); assert(state.writes == 0)
            state.disabled = false; state.directionDisabled = true
            renderer:ApplyControlState(control, definition)
            assert(inverse.enabled and not direction.enabled)
            inverse:SetChecked(true); inverse:Fire("OnClick")
            direction:SetChecked(true); direction:Fire("OnClick")
            assert(state.writes == 1 and state.direction == nil)
            direction:Fire("OnEnter"); assert(Tooltip.lines[1] == "Direction unavailable")
            control:Hide(); inverse:Fire("OnClick"); assert(state.writes == 1)
            control:Show(); state.directionDisabled = false
            renderer:ApplyControlState(control, definition)
            direction:Fire("OnClick"); assert(state.writes == 2)
            local current = true
            local bound = addon.LibOrbitUI.Config.BindDefinition(definition, function() return current end)
            current = false
            bound.valueCheckboxes[1].callback(false); bound.valueCheckboxes[2].callback(false)
            assert(state.writes == 2)
        ''')

    def test_indexed_single_empty_and_hidden_slot_reuse_expires_handlers(self):
        self.lua.execute(r'''
            local control = Render(CheckboxDefinition())
            local inverse, direction = unpack(control.ValueCheckboxes)
            local expired = inverse:GetScript("OnClick")
            direction:Fire("OnEnter")
            layout:Reset(container)
            assert(Tooltip.owner == nil and not inverse:IsShown() and not direction:IsShown())
            assert(inverse:GetScript("OnClick") == nil and direction.valueCheckboxDefinition == nil)
            local singular = Render({type = "accessories", label = "Single", default = "Smooth",
                valueCheckbox = {initialValue = true, tooltip = "Single", callback = Write}})
            assert(singular == control and singular.ValueCheckbox:IsShown())
            expired(inverse); assert(state.writes == 0)
            layout:Reset(container)
            local definition = CheckboxDefinition()
            definition.valueCheckboxes[1].visible = false
            local hidden = Render(definition)
            assert(hidden == control and not inverse:IsShown() and direction:IsShown())
            assert(not control.ValueCheckbox:IsShown())
            assert(select(2, HorizontalBounds(direction)) == control:GetWidth() - Constants.Widget.ValueInset)
            definition.valueCheckboxes[1].visible = true
            local controls = layout:ApplyValueCheckboxes(control, definition.valueCheckboxes)
            layout:LayoutValueControls(control, unpack(controls))
            assert(controls[1] == inverse and controls[2] == direction)
            expired(inverse); assert(state.writes == 0)
            controls = layout:ApplyValueCheckboxes(control, {})
            assert(#controls == 0 and not inverse:IsShown() and not direction:IsShown())
            local fresh = Frame()
            local list = layout:ApplyValueCheckboxes(fresh, {{visible = false}, {tooltip = "Second"}})
            assert(#list == 1 and fresh.ValueCheckboxes[1] == nil)
            layout:ApplyValueCheckboxes(fresh, {})
            assert(not fresh.ValueCheckboxes[2]:IsShown(), "Sparse pooled slots must also be released")
        ''')


if __name__ == "__main__":
    unittest.main()
