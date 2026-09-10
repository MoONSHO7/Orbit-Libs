local _, addon = ...
local Config = addon.LibOrbitUI.Config
local TRISTATE_YELLOW = { r = 1, g = 0.82, b = 0 }
local COMPACT_SIZE = 26
local CHECKBOX_HEIGHT = 30
local COMPACT_GAP = 4

-- [ CHECKBOX WIDGET ]--------------------------------------------------------------------------------------------------
function Config:CreateCheckbox(parent, label, tooltip, initialValue, callback, opts)
    local Constants = self.configOptions.constants
    local GameTooltip = self.configOptions.tooltip
    local GameTooltip_Hide = self.configOptions.tooltipHide
    local CHECK_TEX = Constants.Texture.CheckboxCheck
    local CROSS_TEX = Constants.Texture.ReadyCheckNotReady
    opts = opts or {}
    local frame
    if opts.compact then
        self.compactCheckboxPool = self.compactCheckboxPool or {}
        frame = table.remove(self.compactCheckboxPool)
        if not frame then
            frame = CreateFrame("Frame", nil, parent)
            frame:SetHeight(COMPACT_SIZE)
            frame.OrbitType = "Checkbox"
            frame._compact = true
            local cb = CreateFrame("CheckButton", nil, frame, "UICheckButtonTemplate")
            cb:SetSize(COMPACT_SIZE, COMPACT_SIZE)
            cb:SetPoint("LEFT")
            frame._cb = cb
            local text = cb.text or cb:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
            text:SetTextColor(1, 1, 1)
            text:SetJustifyH("LEFT")
            text:SetPoint("LEFT", cb, "RIGHT", COMPACT_GAP, 0)
            cb.text = text
            frame.SetLabel = function(self, t)
                text:SetText(t)
            end
            frame.SetLabelColor = function(self, r, g, b)
                text:SetTextColor(r, g, b)
            end
            frame.SetEnabled = function(self, enabled)
                if enabled then
                    cb:Enable()
                else
                    cb:Disable()
                end
            end
            frame.SetChecked = function(self, v)
                cb:SetChecked(v)
            end
            frame.GetChecked = function(self)
                return cb:GetChecked()
            end
            frame.SetOnClick = function(self, fn)
                cb:SetScript("OnClick", fn)
            end
            frame.SetTooltip = function(self, enterFn, leaveFn)
                cb:SetScript("OnEnter", enterFn)
                cb:SetScript("OnLeave", leaveFn or GameTooltip_Hide)
            end
        end
        frame:SetParent(parent)
        local cb = frame._cb
        cb.text:SetText(label)
        cb.text:SetTextColor(1, 1, 1)
        cb:Enable()
        cb:SetScript("OnEnter", nil)
        cb:SetScript("OnLeave", nil)
        cb:GetCheckedTexture():SetVertexColor(1, 1, 1)
        frame._triState = nil
        frame._isTriState = opts.triState and true or false
        frame._initialTriState = nil
        frame._initialState = nil
        frame._allLiveToggle = nil
    else
        if not self.checkboxPool then
            self.checkboxPool = {}
        end
        frame = table.remove(self.checkboxPool)
        if not frame then
            frame = CreateFrame("Frame", nil, parent, "EditModeSettingCheckboxTemplate")
            frame.OrbitType = "Checkbox"
        end
        frame:SetParent(parent)
        frame:SetHeight(CHECKBOX_HEIGHT)
        local C = Constants
        if frame.Button then
            frame.Button:ClearAllPoints()
            frame.Button:SetPoint("LEFT", frame, "LEFT", 0, 0)
        end
        if frame.Label then
            frame.Label:SetText(label)
            frame.Label:SetFontObject(C.UI.LabelFont)
            frame.Label:SetWidth(0)
            frame.Label:SetJustifyH("LEFT")
            frame.Label:ClearAllPoints()
            frame.Label:SetPoint("LEFT", frame, "LEFT", C.Widget.LabelWidth + C.Widget.LabelGap, 0)
            local rightInset = opts.valueText ~= nil and C.Widget.ValueWidth or 0
            frame.Label:SetPoint("RIGHT", frame, "RIGHT", -rightInset, 0)
        end
        if opts.valueText ~= nil then
            if not frame.ValueText then
                frame.ValueText = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
            end
            frame.ValueText:ClearAllPoints()
            frame.ValueText:SetPoint("RIGHT", frame, "RIGHT", -C.Widget.ValueInset, 0)
            frame.ValueText:SetWidth(C.Widget.ValueWidth - C.Widget.ValueInset)
            frame.ValueText:SetJustifyH("RIGHT")
            frame.ValueText:SetText(tostring(opts.valueText))
            frame.ValueText:Show()
        elseif frame.ValueText then
            frame.ValueText:Hide()
        end
        frame._cb = frame.Button
        frame.SetLabel = function(self, t)
            if self.Label then
                self.Label:SetText(t)
            end
        end
        frame.SetLabelColor = function(self, r, g, b)
            if self.Label then
                self.Label:SetTextColor(r, g, b)
            end
        end
        frame.SetEnabled = function(self, enabled)
            if self.Button then
                if enabled then
                    self.Button:Enable()
                else
                    self.Button:Disable()
                end
            end
        end
        frame.SetChecked = function(self, v)
            if self.Button then
                self.Button:SetChecked(v)
            end
        end
        frame.GetChecked = function(self)
            return self.Button and self.Button:GetChecked()
        end
        frame.SetOnClick = function(self, fn)
            if self.Button then
                self.Button:SetScript("OnClick", fn)
            end
        end
        frame.SetTooltip = function(self, enterFn, leaveFn)
            if self.Button then
                self.Button:SetScript("OnEnter", enterFn)
                self.Button:SetScript("OnLeave", leaveFn or GameTooltip_Hide)
            end
        end
    end
    local cb = frame._cb
    if opts.triState then
        frame._triState = initialValue or 0
        local function ApplyVisual(state)
            if state == 0 then
                cb:SetChecked(false)
                cb:SetCheckedTexture(CHECK_TEX)
            elseif state == 1 then
                cb:SetChecked(true)
                cb:SetCheckedTexture(CHECK_TEX)
                cb:GetCheckedTexture():SetVertexColor(TRISTATE_YELLOW.r, TRISTATE_YELLOW.g, TRISTATE_YELLOW.b)
            else
                cb:SetChecked(true)
                cb:SetCheckedTexture(CROSS_TEX)
                cb:GetCheckedTexture():SetVertexColor(1, 0.3, 0.3)
            end
        end
        ApplyVisual(frame._triState)
        cb:SetScript("OnClick", function()
            frame._triState = (frame._triState + 1) % 3
            ApplyVisual(frame._triState)
            if callback then
                callback(frame._triState)
            end
        end)
        frame.SetTriState = function(self, state)
            self._triState = state
            ApplyVisual(state)
        end
        frame.GetTriState = function(self)
            return self._triState
        end
    else
        cb:SetChecked(initialValue or false)
        cb:SetCheckedTexture(CHECK_TEX)
        if initialValue then
            cb:GetCheckedTexture():SetVertexColor(1, 1, 1)
        end
        cb:SetScript("OnClick", function(self)
            local checked = self:GetChecked()
            if callback then
                callback(checked)
            end
        end)
    end
    if tooltip then
        cb:SetScript("OnEnter", function(self)
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:SetText(label, 1, 1, 1)
            if type(tooltip) == "function" then
                GameTooltip:AddLine(tooltip(frame), nil, nil, nil, true)
            else
                GameTooltip:AddLine(tooltip, nil, nil, nil, true)
            end
            GameTooltip:Show()
        end)
        cb:SetScript("OnLeave", GameTooltip_Hide)
    end
    return frame
end

function Config:ReleaseCompactCheckbox(frame)
    if frame and frame._compact then
        frame:Hide()
        frame:SetParent(nil)
        frame:ClearAllPoints()
        frame._triState = nil
        frame._isTriState = nil
        frame._initialTriState = nil
        frame._initialState = nil
        frame._allLiveToggle = nil
        self.compactCheckboxPool = self.compactCheckboxPool or {}
        table.insert(self.compactCheckboxPool, frame)
    end
end
