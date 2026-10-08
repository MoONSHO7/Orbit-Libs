local _, addon = ...
local Config = addon.LibOrbitUI.Config
local ROW_HEIGHT = 24
local TEXT_PADDING = 4
local ACTION_PADDING = 20
local ACTION_GAP = 8
local DETAIL_COLOR = { 0.72, 0.72, 0.72 }

local function UpdateMetadataLayout(frame, width)
    if width > 1 then
        local inset = frame.Action:IsShown() and frame.Action:GetWidth() + ACTION_GAP or 0
        frame.text:SetWidth(math.max(1, width - inset))
        frame:SetHeight(math.max(ROW_HEIGHT, frame.text:GetStringHeight() + TEXT_PADDING))
    end
end

function Config:CreateReadout(parent, label, value)
    local constants = self.configOptions.constants
    local frame = table.remove(self.readoutPool)
    if not frame then
        frame = CreateFrame("Frame", nil, parent)
        frame.OrbitType = "Readout"
        frame.Label = frame:CreateFontString(nil, "ARTWORK", constants.UI.LabelFont)
        frame.Label:SetJustifyH("LEFT")
        frame.Label:SetPoint("LEFT")
        frame.Label:SetWidth(constants.Widget.LabelWidth)
        frame.Value = frame:CreateFontString(nil, "ARTWORK", constants.UI.ValueFont)
        frame.Value:SetJustifyH("LEFT")
        frame.Value:SetPoint("LEFT", frame.Label, "RIGHT", constants.Widget.LabelGap, 0)
        frame.Value:SetPoint("RIGHT")
    end
    frame:SetParent(parent)
    frame:SetHeight(ROW_HEIGHT)
    frame.Label:SetText(label)
    frame.Value:SetText(value == nil and "" or tostring(value))
    return frame
end

function Config:CreateControlMetadata(parent, text, actionText, callback, frame)
    frame = frame or table.remove(self.controlMetadataPool)
    if not frame then
        frame = CreateFrame("Frame", nil, parent)
        frame.OrbitType = "ControlMetadata"
        frame.text = frame:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
        frame.text:SetPoint("TOPLEFT")
        frame.text:SetJustifyH("LEFT")
        frame.text:SetWordWrap(true)
        frame.text:SetTextColor(unpack(DETAIL_COLOR))
        frame.Action = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
        frame.Action:SetPoint("TOPRIGHT")
        frame.Action:SetHeight(ROW_HEIGHT)
        frame.Action:SetScript("OnClick", function()
            if frame.onAction then
                frame.onAction()
            end
        end)
        frame:SetScript("OnSizeChanged", UpdateMetadataLayout)
    end
    frame:SetParent(parent)
    frame:SetHeight(ROW_HEIGHT)
    frame.text:SetText(text or "")
    frame.onAction = callback
    frame.Action:SetShown(actionText ~= nil and callback ~= nil)
    frame.Action:SetEnabled(true)
    if actionText then
        frame.Action:SetText(actionText)
        frame.Action:SetWidth(frame.Action:GetFontString():GetStringWidth() + ACTION_PADDING)
    end
    UpdateMetadataLayout(frame, frame:GetWidth())
    return frame
end
