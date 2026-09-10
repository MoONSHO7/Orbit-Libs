local _, addon = ...
local UI = addon.LibOrbitUI
local Config = UI.Config
local WIDTH = 360
local PAD = 16
local BG_INSET_LEFT = 6
local BG_INSET_TOP = 21
local BG_INSET_RIGHT = 2
local BG_INSET_BOTTOM = 2
local TITLE_OFFSET = 6
local BTN_HEIGHT = 24
local BTN_GAP = 8
local NINESLICE_LEVEL_OFFSET = 1
local CONTENT_LEVEL_OFFSET = 10
local TEXT_SPACING = 2
local BACKGROUND_SUBLEVEL = -6

function Config.InstallPrompts(target, options)
    assert(type(options.name) == "string" and options.name ~= "", "LibOrbitUI prompts need a unique name")
    assert(type(options.labels) == "table", "LibOrbitUI prompts need localized labels")
    assert(not target.promptOptions, "LibOrbitUI prompts are already installed on this layout")
    target.promptOptions = options
    target.ShowConfirm = Config.ShowConfirm
    target.ShowInput = Config.ShowInput
    target.ShowTextTransfer = Config.ShowTextTransfer
    target.HidePrompts = Config.HidePrompts
    return target
end

function Config:HidePrompts()
    if self.confirmPopup then
        self.confirmPopup:Hide()
    end
    if self.inputPopup then
        self.inputPopup:Hide()
    end
end

function Config.GetPromptLabel(layout, key)
    local label = layout.promptOptions.labels[key]
    if type(label) == "function" then
        label = label()
    end
    assert(type(label) == "string", "LibOrbitUI prompt needs a localized " .. key .. " label")
    return label
end

function Config.CreatePromptFrame(layout, suffix, width, justify)
    local name = layout.promptOptions.name .. suffix
    assert(not _G[name], "LibOrbitUI prompt name is already in use")
    local constants = layout.configOptions.constants
    local chrome = layout.chrome or UI.DialogChrome:Create(constants.DialogBackdrop)
    local frame = CreateFrame("Frame", name, UIParent)
    frame:SetWidth(width)
    frame:SetPoint("CENTER")
    frame:SetFrameStrata(layout.promptOptions.strata or constants.Strata.Topmost)
    frame:SetToplevel(true)
    frame:SetClampedToScreen(true)
    frame:EnableMouse(true)
    frame:Hide()

    frame.NineSlice = CreateFrame("Frame", nil, frame, "NineSlicePanelTemplate")
    frame.NineSlice.layoutType = "ButtonFrameTemplateNoPortrait"
    NineSliceUtil.ApplyLayoutByName(frame.NineSlice, "ButtonFrameTemplateNoPortrait")
    frame.NineSlice:SetFrameLevel(frame:GetFrameLevel() + NINESLICE_LEVEL_OFFSET)

    frame.Bg = frame:CreateTexture(nil, "BACKGROUND", nil, BACKGROUND_SUBLEVEL)
    chrome:ApplyBackdrop(frame.Bg)
    frame.Bg:SetPoint("TOPLEFT", BG_INSET_LEFT, -BG_INSET_TOP)
    frame.Bg:SetPoint("BOTTOMRIGHT", -BG_INSET_RIGHT, BG_INSET_BOTTOM)

    frame.TitleContainer = CreateFrame("Frame", nil, frame)
    frame.TitleContainer:SetFrameLevel(frame.NineSlice:GetFrameLevel() + CONTENT_LEVEL_OFFSET)
    frame.TitleContainer:SetPoint("TOPLEFT", BG_INSET_LEFT, -TITLE_OFFSET)
    frame.TitleContainer:SetPoint("TOPRIGHT", -BG_INSET_LEFT, -TITLE_OFFSET)
    frame.TitleContainer:SetHeight(BG_INSET_TOP)
    frame.title = frame.TitleContainer:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    frame.title:SetPoint("TOP", frame.TitleContainer, "TOP")

    frame.text = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    if justify == "CENTER" then
        frame.text:SetPoint("TOP", frame, "TOP", 0, -(BG_INSET_TOP + PAD))
    else
        frame.text:SetPoint("TOPLEFT", frame, "TOPLEFT", PAD, -(BG_INSET_TOP + PAD))
    end
    frame.text:SetWidth(width - PAD * 2)
    frame.text:SetJustifyH(justify)
    frame.text:SetSpacing(TEXT_SPACING)

    frame.acceptBtn = layout:CreateButton(frame, "")
    frame.acceptBtn:SetHeight(BTN_HEIGHT)
    frame.acceptBtn:SetFrameLevel(frame.NineSlice:GetFrameLevel() + CONTENT_LEVEL_OFFSET)
    frame.cancelBtn = layout:CreateButton(frame, "")
    frame.cancelBtn:SetHeight(BTN_HEIGHT)
    frame.cancelBtn:SetFrameLevel(frame.NineSlice:GetFrameLevel() + CONTENT_LEVEL_OFFSET)
    frame:SetScript("OnHide", function(self)
        self._onAccept, self._data, self._request = nil, nil, nil
        self.acceptBtn:SetScript("OnClick", nil)
        self.cancelBtn:SetScript("OnClick", nil)
    end)
    UISpecialFrames[#UISpecialFrames + 1] = name
    return frame
end

function Config.LayoutPromptButtons(frame, width, showCancel)
    local availableWidth = width - PAD * 2
    local btnWidth = showCancel and (availableWidth - BTN_GAP) / 2 or availableWidth
    frame.acceptBtn:SetWidth(btnWidth)
    frame.cancelBtn:SetWidth(btnWidth)
    frame.acceptBtn:ClearAllPoints()
    frame.acceptBtn:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", PAD, PAD)
    frame.cancelBtn:ClearAllPoints()
    frame.cancelBtn:SetPoint("BOTTOMLEFT", frame.acceptBtn, "BOTTOMRIGHT", BTN_GAP, 0)
    frame.cancelBtn:SetShown(showCancel)
    frame.cancelBtn:SetScript("OnClick", function()
        frame:Hide()
    end)
end

function Config:ShowConfirm(opts)
    local frame = self.confirmPopup
    if not frame then
        frame = Config.CreatePromptFrame(self, "ConfirmPopup", WIDTH, "CENTER")
        self.confirmPopup = frame
    end
    frame:Hide()
    frame.title:SetText(opts.title or "")
    frame.text:SetText(opts.text or "")
    frame._onAccept, frame._data = opts.onAccept, opts.data
    frame.acceptBtn:SetText(opts.acceptText or "")
    frame.cancelBtn:SetText(opts.cancelText or Config.GetPromptLabel(self, "cancel"))
    frame.acceptBtn:SetScript("OnClick", function()
        local onAccept, data = frame._onAccept, frame._data
        frame:Hide()
        if onAccept then
            onAccept(data)
        end
    end)
    Config.LayoutPromptButtons(frame, WIDTH, true)
    frame:SetHeight(BG_INSET_TOP + PAD + frame.text:GetStringHeight() + PAD + BTN_HEIGHT + PAD)
    frame:Show()
    frame:Raise()
    return frame
end
