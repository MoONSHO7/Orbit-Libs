"""Verify prompt actions remain visible when their buttons come from the layout pool."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"

HARNESS = r'''
addon = {LibOrbitUI = {Config = {ReleaseValueControls = function() end}}}
UISpecialFrames = {}
NineSliceUtil = {ApplyLayoutByName = function() end}
function Frame(parent)
    local frame = {parent = parent, shown = true, scripts = {}, level = 1, text = ""}
    function frame:SetParent(value) self.parent = value end
    function frame:SetText(value) self.text = value end
    function frame:SetWidth(value) self.width = value end
    function frame:SetHeight(value) self.height = value end
    function frame:SetPoint(...) self.point = {...} end
    function frame:ClearAllPoints() self.point = nil end
    function frame:SetFrameStrata(value) self.strata = value end
    function frame:SetFrameLevel(value) self.level = value end
    function frame:GetFrameLevel() return self.level end
    function frame:SetToplevel() end
    function frame:SetClampedToScreen() end
    function frame:EnableMouse() end
    function frame:SetJustifyH() end
    function frame:SetSpacing() end
    function frame:Raise() end
    function frame:SetScript(name, callback) self.scripts[name] = callback end
    function frame:Hide()
        local shown = self.shown
        self.shown = false
        if shown and self.scripts.OnHide then self.scripts.OnHide(self) end
    end
    function frame:Show() self.shown = true end
    function frame:SetShown(value) if value then self:Show() else self:Hide() end end
    function frame:IsShown() return self.shown end
    function frame:IsVisible() return self.shown and (not self.parent or self.parent:IsVisible()) end
    function frame:Click() if self:IsVisible() and self.scripts.OnClick then self.scripts.OnClick(self) end end
    function frame:CreateTexture() return Frame(self) end
    function frame:CreateFontString() return Frame(self) end
    function frame:GetFontString() return self end
    function frame:GetStringWidth() return #self.text * 6 end
    function frame:GetStringHeight() return 24 end
    return frame
end
UIParent = Frame()
function CreateFrame(_, name, parent)
    local frame = Frame(parent)
    if name then _G[name] = frame end
    return frame
end
'''


class PromptButtons(unittest.TestCase):
    def runtime(self, pooled):
        lua = LuaRuntime()
        lua.execute(HARNESS)
        for source in (
            "Config/Layout.lua",
            "Config/Widgets/ConfigButton.lua",
            "Config/Dialogs/ConfigConfirmPopup.lua",
        ):
            lua.execute("return function(...)\n" + (RUNTIME / source).read_text(encoding="utf-8") + "\nend")(
                "Host", lua.globals().addon
            )
        lua.execute('''
            layout = setmetatable({
                buttonPool = {}, controlPools = {Button = {name = "buttonPool"}},
                configOptions = {constants = {Strata = {Topmost = "FULLSCREEN_DIALOG"}}},
                chrome = {ApplyBackdrop = function() end},
                CreateButton = addon.LibOrbitUI.Config.CreateButton,
            }, {__index = addon.LibOrbitUI.Layout.Methods})
            addon.LibOrbitUI.Config.InstallPrompts(layout, {name = "Test", labels = {cancel = "Cancel"}})
            accepted, obsolete = 0, 0
        ''')
        lua.globals().pooled = pooled
        lua.execute('''
            local controls = {}
            for index = 1, pooled do
                controls[index] = layout:CreateButton(UIParent, "Old", function() obsolete = obsolete + 1 end)
            end
            layout:RecycleControls(controls)
            for _, button in ipairs(layout.buttonPool) do assert(not button:IsShown()) end
        ''')
        return lua

    def test_confirmation_reuses_hidden_controls(self):
        for pooled in (0, 1, 2):
            with self.subTest(pooled=pooled):
                lua = self.runtime(pooled)
                lua.execute('''
                    local prompt = layout:ShowConfirm({title = "Delete Category", text = "Delete Damage Meters?",
                        acceptText = "Delete", data = "category", onAccept = function(data)
                            assert(data == "category")
                            accepted = accepted + 1
                        end})
                    assert(prompt.acceptBtn:IsVisible(), "confirmation button remained hidden after pool reuse")
                    assert(prompt.cancelBtn:IsVisible() and prompt.acceptBtn ~= prompt.cancelBtn)
                    assert(prompt.acceptBtn.text == "Delete" and prompt.cancelBtn.text == "Cancel")
                    assert(accepted == 0)
                    prompt.acceptBtn:Click()
                    prompt.acceptBtn:Click()
                    assert(accepted == 1 and obsolete == 0 and not prompt:IsShown())
                    local reopened = layout:ShowConfirm({acceptText = "Delete", onAccept = function()
                        accepted = accepted + 10
                    end})
                    assert(reopened == prompt and prompt.acceptBtn:IsVisible())
                    prompt.cancelBtn:Click()
                    assert(accepted == 1 and not prompt:IsShown())
                ''')


if __name__ == "__main__":
    unittest.main()
