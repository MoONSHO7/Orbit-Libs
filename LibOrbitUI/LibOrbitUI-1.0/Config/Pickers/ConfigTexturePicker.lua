local _, addon = ...
local Config = addon.LibOrbitUI.Config

local ROW_HEIGHT = 22
local MAX_HEIGHT = 300

function Config:CreateTexturePicker(
    parent,
    label,
    initialTexture,
    callback,
    previewColor,
    valueCheckboxCfg,
    valueColorCfg,
    mediaCategory
)
    local media = self.pickerOptions.media
    local NONE_LABEL = media.noneLabel
    local MediaMenu = self.mediaMenu
    local Layout = self
    local Constants = self.configOptions.constants
    local Pixel = self.configOptions.pixel
    if not self.texturePool then
        self.texturePool = {}
    end
    local frame = table.remove(self.texturePool)

    if not frame then
        frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
        frame.OrbitType = "Texture"
        frame.Label = frame:CreateFontString(nil, "ARTWORK", Constants.UI.LabelFont)

        local control = self:CreatePickerControl(frame, { justify = "CENTER", fontObject = Constants.UI.LabelFont })

        control.Texture = control:CreateTexture(nil, "BACKGROUND")
        Pixel:Point(control.Texture, "TOPLEFT", 1, -1)
        Pixel:Point(control.Texture, "BOTTOMRIGHT", -1, 1)

        Pixel:Point(control.Text, "LEFT", 4, 0)
        local shadowOffset = Pixel:Multiple(1, control.Text:GetEffectiveScale())
        control.Text:SetShadowOffset(shadowOffset, -shadowOffset)
        control.Text:SetShadowColor(0, 0, 0, 1)
    end

    frame:SetParent(parent)
    frame.selectedTexture = initialTexture or media.defaultTexture
    frame.previewColor = previewColor or { r = 0.8, g = 0.8, b = 0.8 }
    frame.textureCallback = callback
    frame.mediaCategory = mediaCategory or "fill"

    local function UpdatePreview()
        local color = frame.previewColor
        local tex = frame.Control.Texture
        if frame.selectedTexture == NONE_LABEL then
            tex:SetColorTexture(color.r or 0.3, color.g or 0.3, color.b or 0.3, 1)
        else
            local path = media.fetch("statusbar", frame.selectedTexture)
            if path and path ~= "" and media.isValid(path) then
                tex:SetTexture(path)
                tex:SetVertexColor(color.r or 0.8, color.g or 0.8, color.b or 0.8, 1)
                tex:SetTexCoord(0, 1, 0, 1)
            else
                tex:SetColorTexture(0.3, 0.3, 0.3, 1)
            end
        end
        frame.Control.Text:SetText(frame.selectedTexture)
    end

    function frame:ShowDropdown()
        if not frame.Dropdown then
            frame.Dropdown = MediaMenu:Create(frame.Control, {
                rowHeight = ROW_HEIGHT,
                maxHeight = MAX_HEIGHT,
                firstItem = NONE_LABEL,
                createRow = function(rowParent)
                    local row = CreateFrame("Button", nil, rowParent)
                    row.Texture = row:CreateTexture(nil, "BACKGROUND")
                    Pixel:Point(row.Texture, "TOPLEFT", 2, -1)
                    Pixel:Point(row.Texture, "BOTTOMRIGHT", -2, 1)
                    row.Text = row:CreateFontString(nil, "OVERLAY", Constants.UI.LabelFont)
                    Pixel:Point(row.Text, "LEFT", 8, 0)
                    Pixel:Point(row.Text, "RIGHT", -MediaMenu.ROW_TEXT_RIGHT_INSET, 0)
                    row.Text:SetJustifyH("CENTER")
                    local rowShadowOffset = Pixel:Multiple(1, row.Text:GetEffectiveScale())
                    row.Text:SetShadowOffset(rowShadowOffset, -rowShadowOffset)
                    row.Text:SetShadowColor(0, 0, 0, 1)
                    return row
                end,
                renderRow = function(row, name, isSelected)
                    row.Text:SetText(name)
                    if name == NONE_LABEL then
                        row.Texture:SetColorTexture(0.15, 0.15, 0.15, 1)
                    else
                        local path = media.fetch("statusbar", name)
                        if path and path ~= "" and media.isValid(path) then
                            row.Texture:SetTexture(path)
                            row.Texture:SetVertexColor(0.7, 0.7, 0.7, 1)
                            row.Texture:SetTexCoord(0, 1, 0, 1)
                        else
                            row.Texture:SetColorTexture(0.3, 0.3, 0.3, 1)
                        end
                    end
                end,
                onSelect = function(name)
                    frame.selectedTexture = name
                    UpdatePreview()
                    if frame.textureCallback then
                        frame.textureCallback(name)
                    end
                end,
            })
            Layout:BindPickerDropdown(frame.Control, frame.Dropdown)
        end
        local list = media.list("statusbar", frame.mediaCategory, frame.selectedTexture)
        frame.Dropdown:Populate(list, frame.selectedTexture)
    end

    UpdatePreview()

    local C = Constants

    self:LayoutPickerLabelAndControl(frame, label)

    if valueCheckboxCfg then
        self:ApplyValueCheckbox(frame, valueCheckboxCfg)
    elseif frame.ValueCheckbox then
        frame.ValueCheckbox:Hide()
    end

    if valueColorCfg then
        local swatchX = valueCheckboxCfg and (C.Widget.ValueInset + C.Widget.ValueSwatchSize * 1.5 + 1) or nil
        self:ApplyValueColorSwatch(frame, valueColorCfg, swatchX)
    elseif frame.ValueColorSwatch then
        frame.ValueColorSwatch:Hide()
    end

    frame:SetSize(C.Widget.Width, C.Widget.Height)
    return frame
end
