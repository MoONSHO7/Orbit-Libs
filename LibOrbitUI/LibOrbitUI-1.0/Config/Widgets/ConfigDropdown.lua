local _, addon = ...
local Config = addon.LibOrbitUI.Config

-- [ DROPDOWN WIDGET ]--------------------------------------------------------------------------------------------------
local ROW_HEIGHT = 22
local MAX_HEIGHT = 300
local SEARCH_THRESHOLD = 12
local TEXT_INSET = 8
local ROW_TEXT_INSET = 10
local ROW_CHECK_INSET = 8
local ROW_CHECK_GAP = 4
local TITLE_COLOR = { 0.8, 0.65, 0.3 }

local function LabelFor(option)
    if type(option) ~= "table" then
        return tostring(option)
    end
    return option.label or option.text or tostring(option.value)
end

local function ValueFor(option)
    return type(option) == "table" and option.value or option
end

local function BuildItems(options, MediaMenu)
    local items = {}
    for _, option in ipairs(options) do
        if option.divider and not option.title then
            items[#items + 1] = MediaMenu.DIVIDER
        else
            items[#items + 1] = option
        end
    end
    return items
end

local function CopySelection(values)
    local copy = {}
    local seen = {}
    for _, value in ipairs(type(values) == "table" and values or {}) do
        if not seen[value] then
            seen[value] = true
            copy[#copy + 1] = value
        end
    end
    table.sort(copy, function(a, b)
        return tostring(a) < tostring(b)
    end)
    return copy
end

local function FindSelection(values, target)
    for index, value in ipairs(values) do
        if value == target then
            return index
        end
    end
end

local function ShowOptionTooltip(row, GameTooltip)
    local option = row.option
    if type(option) ~= "table" or not option.tooltip then
        return
    end
    GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
    GameTooltip:SetText(LabelFor(option), 1, 1, 1)
    local color = option.tooltipColor
    GameTooltip:AddLine(option.tooltip, color and color[1], color and color[2], color and color[3], true)
    GameTooltip:Show()
end

function Config:CreateDropdown(
    parent,
    label,
    options,
    initialValue,
    callback,
    valueCheckboxCfg,
    valueColorCfg,
    multiSelectCfg
)
    local Layout = self
    local Constants = self.configOptions.constants
    local Pixel = self.configOptions.pixel
    local MediaMenu = self.mediaMenu
    local GameTooltip = self.configOptions.tooltip
    local GameTooltip_Hide = self.configOptions.tooltipHide
    self.dropdownPool = self.dropdownPool or {}
    local frame = table.remove(self.dropdownPool)

    if not frame then
        frame = CreateFrame("Frame", nil, parent, "BackdropTemplate")
        frame.OrbitType = "Dropdown"
        frame.Label = frame:CreateFontString(nil, "ARTWORK", Constants.UI.LabelFont)

        local control = self:CreatePickerControl(frame, { fontObject = Constants.UI.LabelFont })
        Pixel:Point(control.Text, "LEFT", TEXT_INSET, 0)
    end

    frame:SetParent(parent)
    frame.dropOptions = options
    frame.dropValue = multiSelectCfg and CopySelection(initialValue) or initialValue
    frame.dropCallback = callback
    frame.dropMultiSelect = multiSelectCfg

    local function SelectedOption()
        if frame.dropMultiSelect then
            return
        end
        for _, option in ipairs(frame.dropOptions) do
            if not option.divider and not option.action and ValueFor(option) == frame.dropValue then
                return option
            end
        end
    end

    local function IsOptionSelected(option)
        return frame.dropMultiSelect and FindSelection(frame.dropValue, ValueFor(option)) ~= nil
    end

    local function UpdatePreview()
        if frame.dropMultiSelect then
            local count = #frame.dropValue
            if count == 0 then
                frame.Control.Text:SetText(frame.dropMultiSelect.emptyText)
            elseif count == 1 then
                for _, option in ipairs(frame.dropOptions) do
                    if not option.divider and not option.action and IsOptionSelected(option) then
                        frame.Control.Text:SetText(LabelFor(option))
                        return
                    end
                end
                frame.Control.Text:SetText(frame.dropMultiSelect.summary(count))
            else
                frame.Control.Text:SetText(frame.dropMultiSelect.summary(count))
            end
            return
        end
        local option = SelectedOption()
        frame.Control.Text:SetText(option and LabelFor(option) or tostring(frame.dropValue))
    end

    function frame:ShowDropdown()
        if not frame.Dropdown then
            frame.Dropdown = MediaMenu:Create(frame.Control, {
                rowHeight = ROW_HEIGHT,
                maxHeight = MAX_HEIGHT,
                sorted = false,
                search = #frame.dropOptions > SEARCH_THRESHOLD,
                itemText = LabelFor,
                itemTextLeftInset = function(option, row)
                    local showCheck = frame.dropMultiSelect and option.title == nil and option.action == nil
                    if showCheck then
                        local scale = row:GetEffectiveScale()
                        return row.Check:GetWidth() + Pixel:Multiple(ROW_CHECK_INSET + ROW_CHECK_GAP, scale)
                    end
                    return Pixel:Multiple(ROW_TEXT_INSET, row:GetEffectiveScale())
                end,
                createRow = function(rowParent)
                    local row = CreateFrame("Button", nil, rowParent)
                    row.Check = CreateFrame("CheckButton", nil, row, "UIRadialButtonTemplate")
                    row.Check:EnableMouse(false)
                    Pixel:Point(row.Check, "LEFT", ROW_CHECK_INSET, 0)
                    row.Text = row:CreateFontString(nil, "OVERLAY", Constants.UI.LabelFont)
                    Pixel:Point(row.Text, "LEFT", ROW_TEXT_INSET, 0)
                    Pixel:Point(row.Text, "RIGHT", -MediaMenu.ROW_TEXT_RIGHT_INSET, 0)
                    row.Text:SetJustifyH("LEFT")
                    row.Text:SetWordWrap(false)
                    row:SetScript("OnEnter", function(owner)
                        ShowOptionTooltip(owner, GameTooltip)
                    end)
                    row:SetScript("OnLeave", GameTooltip_Hide)
                    return row
                end,
                renderRow = function(row, option, isSelected)
                    local isTitle = option.title ~= nil
                    local isAction = option.action ~= nil
                    local showCheck = frame.dropMultiSelect and not isTitle and not isAction
                    row.option = option
                    row.Check:SetShown(showCheck)
                    row.Check:SetChecked(showCheck and isSelected == true)
                    row.Text:ClearAllPoints()
                    if showCheck then
                        Pixel:Point(row.Text, "LEFT", row.Check, "RIGHT", ROW_CHECK_GAP, 0)
                    else
                        Pixel:Point(row.Text, "LEFT", ROW_TEXT_INSET, 0)
                    end
                    Pixel:Point(row.Text, "RIGHT", -MediaMenu.ROW_TEXT_RIGHT_INSET, 0)
                    row.Text:SetText(isTitle and option.title or LabelFor(option))
                    if isTitle or isAction then
                        row.Text:SetTextColor(unpack(TITLE_COLOR))
                    elseif isSelected then
                        row.Text:SetTextColor(1, 1, 1, 1)
                    else
                        row.Text:SetTextColor(0.9, 0.9, 0.9, 1)
                    end
                    row:EnableMouse(not isTitle)
                    if option.font then
                        row.Text:SetFont(option.font, 14, "")
                    end
                end,
                onSelect = function(option)
                    if option.title then
                        return
                    end
                    if option.action then
                        option.action()
                        return
                    end
                    if frame.dropMultiSelect then
                        local value = ValueFor(option)
                        local nextValues = CopySelection(frame.dropValue)
                        local index = FindSelection(nextValues, value)
                        if index then
                            table.remove(nextValues, index)
                        else
                            nextValues[#nextValues + 1] = value
                        end
                        frame.dropValue = nextValues
                        UpdatePreview()
                        frame.Dropdown:SetSelected(IsOptionSelected)
                        if frame.dropCallback then
                            frame.dropCallback(CopySelection(nextValues))
                        end
                        return MediaMenu.KEEP_OPEN
                    end
                    frame.dropValue = ValueFor(option)
                    UpdatePreview()
                    if frame.dropCallback then
                        frame.dropCallback(frame.dropValue)
                    end
                end,
            })
            frame.Dropdown:HookScript("OnHide", GameTooltip_Hide)
            Layout:BindPickerDropdown(frame.Control, frame.Dropdown)
        end
        frame.Dropdown:SetSearchEnabled(#frame.dropOptions > SEARCH_THRESHOLD)
        frame.Dropdown:Populate(
            BuildItems(frame.dropOptions, MediaMenu),
            frame.dropMultiSelect and IsOptionSelected or SelectedOption()
        )
    end

    UpdatePreview()

    function frame:RefreshOptions(newOptions, newValue, newCallback, newMultiSelectCfg)
        frame.dropOptions = newOptions
        frame.dropMultiSelect = newMultiSelectCfg
        frame.dropValue = newMultiSelectCfg and CopySelection(newValue) or newValue
        frame.dropCallback = newCallback
        UpdatePreview()
    end

    local C = Constants
    self:LayoutPickerLabelAndControl(frame, label)

    if valueCheckboxCfg then
        self:ApplyValueCheckbox(frame, valueCheckboxCfg)
        if frame.ValueColorSwatch then
            frame.ValueColorSwatch:Hide()
        end
    elseif valueColorCfg then
        self:ApplyValueColorSwatch(frame, valueColorCfg)
        if frame.ValueCheckbox then
            frame.ValueCheckbox:Hide()
        end
    else
        if frame.ValueCheckbox then
            frame.ValueCheckbox:Hide()
        end
        if frame.ValueColorSwatch then
            frame.ValueColorSwatch:Hide()
        end
    end

    frame:SetSize(C.Widget.Width, C.Widget.Height)
    return frame
end
