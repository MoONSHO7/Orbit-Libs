local _, addon = ...
local Config = addon.LibOrbitUI.Config
local WIDTH = 380
local PAD = 16
local BG_INSET_TOP = 21
local BTN_HEIGHT = 24
local FIELD_HEIGHT = 22
local FIELD_LABEL_WIDTH = 150
local FIELD_GAP = 10
local TEXT_GAP = 12
local TRANSFER_HEIGHT = 140
local TRANSFER_STATUS_HEIGHT = 28
local TRANSFER_STATUS_GAP = 8
local CONTENT_LEVEL_OFFSET = 10
local STATUS_ERROR = { 1, 0.35, 0.35 }

local function SubmitInput(frame)
    local values = {}
    for index, field in ipairs(frame._fields) do
        values[field.key] = strtrim(frame.rows[index].Input.EditBox:GetText())
    end
    local onAccept = frame._onAccept
    frame:Hide()
    if onAccept then
        onAccept(values)
    end
end

local function CreateInputFrame(layout)
    local frame = Config.CreatePromptFrame(layout, "InputPopup", WIDTH, "LEFT")
    frame.rows = {}
    frame.transferStatus = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    frame.transferStatus:SetHeight(TRANSFER_STATUS_HEIGHT)
    frame.transferStatus:SetJustifyH("LEFT")
    frame.transferStatus:SetJustifyV("TOP")
    frame.transferStatus:SetNonSpaceWrap(true)
    frame.transferStatus:Hide()

    frame.transferImport = layout:CreateEditBox(frame, nil, "", function()
        frame.transferStatus:SetText("")
    end, nil, TRANSFER_HEIGHT, true, { hideScrollBar = true })
    frame.transferImport:SetFrameLevel(frame.NineSlice:GetFrameLevel() + CONTENT_LEVEL_OFFSET)
    frame.transferImport:Hide()
    frame.transferExport = layout:CreateEditBox(frame, nil, "", nil, nil, TRANSFER_HEIGHT, true, {
        hideScrollBar = true,
        readOnly = true,
    })
    frame.transferExport:SetFrameLevel(frame.NineSlice:GetFrameLevel() + CONTENT_LEVEL_OFFSET)
    frame.transferExport:Hide()

    local function CloseTransfer(editBox)
        editBox:ClearFocus()
        frame:Hide()
    end
    frame.transferImport.EditBox:SetScript("OnEscapePressed", CloseTransfer)
    frame.transferExport.EditBox:SetScript("OnEscapePressed", CloseTransfer)
    frame:HookScript("OnHide", function(self)
        self._fields, self._onTransferAccept, self._mode, self._transferKind = nil, nil, nil, nil
        self.transferImport.EditBox:ClearFocus()
        self.transferImport.EditBox:SetText("")
        self.transferExport.EditBox:ClearFocus()
        self.transferExport:SetFrozenText("")
        self.transferStatus:SetText("")
        for _, row in ipairs(self.rows) do
            row.Input.EditBox:SetScript("OnEnterPressed", nil)
            row.Input.EditBox:SetScript("OnEscapePressed", nil)
            row.Input.EditBox:ClearFocus()
            row.Input.EditBox:SetText("")
            row:Hide()
        end
    end)
    return frame
end

local function AcquireRow(layout, frame, index)
    local row = frame.rows[index]
    if row then
        return row
    end
    row = CreateFrame("Frame", nil, frame)
    row:SetFrameLevel(frame.NineSlice:GetFrameLevel() + CONTENT_LEVEL_OFFSET)
    row:SetHeight(FIELD_HEIGHT)
    row.Label = row:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    row.Label:SetPoint("LEFT", row, "LEFT", 0, 0)
    row.Label:SetWidth(FIELD_LABEL_WIDTH)
    row.Label:SetJustifyH("LEFT")
    row.Input = layout:CreateEditBox(row, nil, "", nil, WIDTH - PAD * 2 - FIELD_LABEL_WIDTH, FIELD_HEIGHT)
    row.Input:SetPoint("RIGHT", row, "RIGHT", 0, 0)
    row.Input:SetFrameLevel(row:GetFrameLevel() + 1)
    frame.rows[index] = row
    return row
end

local function GetInputFrame(layout)
    local frame = layout.inputPopup
    if not frame then
        frame = CreateInputFrame(layout)
        layout.inputPopup = frame
    end
    frame:Hide()
    frame._request = {}
    return frame
end

function Config:ShowInput(opts)
    local frame = GetInputFrame(self)
    frame._mode = "input"
    frame.title:SetText(opts.title or "")
    frame.text:SetText(opts.text or "")
    frame._onAccept = opts.onAccept
    frame._fields = opts.fields or {}
    frame.transferImport:Hide()
    frame.transferExport:Hide()
    frame.transferStatus:Hide()

    local top = BG_INSET_TOP + PAD + frame.text:GetStringHeight() + TEXT_GAP
    for index, field in ipairs(frame._fields) do
        local row = AcquireRow(self, frame, index)
        row.Label:SetText(field.label or "")
        row:ClearAllPoints()
        row:SetPoint("TOPLEFT", frame, "TOPLEFT", PAD, -top)
        row:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -PAD, -top)
        local editBox = row.Input.EditBox
        editBox:SetNumeric(field.numeric and true or false)
        editBox:SetText(field.value ~= nil and tostring(field.value) or "")
        editBox:SetScript("OnEnterPressed", function()
            SubmitInput(frame)
        end)
        editBox:SetScript("OnEscapePressed", function()
            frame:Hide()
        end)
        row:Show()
        top = top + FIELD_HEIGHT + FIELD_GAP
    end
    for index = #frame._fields + 1, #frame.rows do
        frame.rows[index]:Hide()
    end

    frame.acceptBtn:SetText(opts.acceptText or Config.GetPromptLabel(self, "accept"))
    frame.cancelBtn:SetText(opts.cancelText or Config.GetPromptLabel(self, "cancel"))
    frame.acceptBtn:SetScript("OnClick", function()
        SubmitInput(frame)
    end)
    Config.LayoutPromptButtons(frame, WIDTH, true)
    frame:SetHeight(top - FIELD_GAP + PAD + BTN_HEIGHT + PAD)
    frame:Show()
    frame:Raise()
    if frame._fields[1] then
        local editBox = frame.rows[1].Input.EditBox
        editBox:SetFocus()
        if frame._fields[1].selectAll then
            editBox:HighlightText()
        end
    end
    return frame
end

function Config:ShowTextTransfer(opts)
    assert(opts.mode == "import" or opts.mode == "export", "ShowTextTransfer requires import or export mode")
    assert(opts.mode ~= "import" or type(opts.onAccept) == "function", "Import requires an acceptance callback")
    local frame = GetInputFrame(self)
    frame._mode, frame._transferKind = "transfer", opts.mode
    frame._onTransferAccept = opts.onAccept
    frame._fields = {}
    frame.title:SetText(opts.title or "")
    frame.text:SetText(opts.text or "")
    for _, row in ipairs(frame.rows) do
        row:Hide()
    end

    local top = BG_INSET_TOP + PAD + frame.text:GetStringHeight() + TEXT_GAP
    local isImport = opts.mode == "import"
    local transferBox = isImport and frame.transferImport or frame.transferExport
    local hiddenBox = isImport and frame.transferExport or frame.transferImport
    hiddenBox:Hide()
    transferBox:ClearAllPoints()
    transferBox:SetPoint("TOPLEFT", frame, "TOPLEFT", PAD, -top)
    transferBox:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -PAD, -top)
    transferBox:SetHeight(TRANSFER_HEIGHT)
    transferBox:Show()

    frame.transferStatus:ClearAllPoints()
    frame.transferStatus:SetPoint("TOPLEFT", transferBox, "BOTTOMLEFT", 0, -TRANSFER_STATUS_GAP)
    frame.transferStatus:SetPoint("TOPRIGHT", transferBox, "BOTTOMRIGHT", 0, -TRANSFER_STATUS_GAP)
    frame.transferStatus:SetText("")
    frame.transferStatus:Show()
    frame.acceptBtn:SetText(opts.acceptText or Config.GetPromptLabel(self, isImport and "import" or "close"))
    frame.cancelBtn:SetText(opts.cancelText or Config.GetPromptLabel(self, "cancel"))
    frame.acceptBtn:SetScript("OnClick", function()
        if frame._transferKind == "export" then
            frame:Hide()
            return
        end
        local request = frame._request
        local success, message = frame._onTransferAccept(frame.transferImport.EditBox:GetText())
        if frame._request ~= request then
            return
        end
        if success then
            frame:Hide()
            return
        end
        frame.transferStatus:SetText(message or "")
        frame.transferStatus:SetTextColor(unpack(STATUS_ERROR))
    end)
    Config.LayoutPromptButtons(frame, WIDTH, isImport)
    frame:SetHeight(top + TRANSFER_HEIGHT + TRANSFER_STATUS_GAP + TRANSFER_STATUS_HEIGHT + PAD + BTN_HEIGHT + PAD)
    frame:Show()
    frame:Raise()
    if isImport then
        frame.transferImport.EditBox:SetText("")
        frame.transferImport.EditBox:SetFocus()
    else
        frame.transferExport:SetFrozenText(opts.value or "")
        frame.transferExport.EditBox:SetFocus()
        frame.transferExport.EditBox:HighlightText()
    end
    return frame
end
