local _, addon = ...
local Config = addon.LibOrbitUI.Config

local ROW_HEIGHT = 24
local MAX_HEIGHT = 300
local ROW_PREVIEW = 13
local CONTROL_PREVIEW = 12

function Config:CreateFontPicker(parent, label, initialFont, callback, valueColorCfg)
    local media = self.pickerOptions.media
    local MediaMenu = self.mediaMenu
    local Layout = self
    local Constants = self.configOptions.constants
    local Pixel = self.configOptions.pixel
    if not self.fontPool then
        self.fontPool = {}
    end
    local frame = table.remove(self.fontPool)

    if not frame then
        frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
        frame.OrbitType = "Font"
        frame.Label = frame:CreateFontString(nil, "ARTWORK", Constants.UI.LabelFont)

        local control = self:CreatePickerControl(frame)
        Pixel:Point(control.Text, "LEFT", 6, 0)
        control.Text:SetTextColor(1, 1, 1, 1)
    end

    frame:SetParent(parent)
    frame.selectedFont = initialFont or media.defaultFont
    frame.fontCallback = callback

    local function UpdatePreview()
        local path = media.fetch("font", frame.selectedFont)
        frame.Control.Text:SetFont(path and media.isValid(path) and path or media.fallbackFont, CONTROL_PREVIEW, "")
        frame.Control.Text:SetText(frame.selectedFont)
    end

    function frame:ShowDropdown()
        if not frame.Dropdown then
            frame.Dropdown = MediaMenu:Create(frame.Control, {
                rowHeight = ROW_HEIGHT,
                maxHeight = MAX_HEIGHT,
                createRow = function(rowParent)
                    local row = CreateFrame("Button", nil, rowParent)
                    row.Text = row:CreateFontString(nil, "OVERLAY")
                    Pixel:Point(row.Text, "LEFT", 10, 0)
                    Pixel:Point(row.Text, "RIGHT", -MediaMenu.ROW_TEXT_RIGHT_INSET, 0)
                    row.Text:SetJustifyH("LEFT")
                    row.Text:SetWordWrap(false)
                    return row
                end,
                renderRow = function(row, name, isSelected)
                    local path = media.fetch("font", name)
                    if path and media.isValid(path) then
                        row.Text:SetFont(path, ROW_PREVIEW, "")
                        row.Text:SetText(name)
                        local color = isSelected and 1 or 0.9
                        row.Text:SetTextColor(color, color, color, 1)
                    else
                        row.Text:SetFont(media.fallbackFont, ROW_PREVIEW, "")
                        row.Text:SetText(name .. " (!)")
                        row.Text:SetTextColor(1, 0.5, 0.5, 1)
                    end
                end,
                onSelect = function(name)
                    frame.selectedFont = name
                    UpdatePreview()
                    if frame.fontCallback then
                        frame.fontCallback(name)
                    end
                end,
            })
            Layout:BindPickerDropdown(frame.Control, frame.Dropdown)
        end
        local list = media.list("font", nil, frame.selectedFont)
        frame.Dropdown:Populate(list, frame.selectedFont)
    end

    UpdatePreview()

    local C = Constants

    self:LayoutPickerLabelAndControl(frame, label)

    if valueColorCfg then
        self:ApplyValueColorSwatch(frame, valueColorCfg)
    elseif frame.ValueColorSwatch then
        frame.ValueColorSwatch:Hide()
    end

    frame:SetSize(C.Widget.Width, C.Widget.Height)
    return frame
end
