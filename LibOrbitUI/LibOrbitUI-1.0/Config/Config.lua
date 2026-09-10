local _, addon = ...
local UI = addon.LibOrbitUI
local Config = {}
UI.Config = Config

local DEFAULT_CONSTANTS = {
    UI = { LabelFont = "GameFontHighlight", ValueFont = "GameFontHighlightSmall" },
    Panel = {
        Width = 340,
        DialogWidth = 370,
        MaxHeight = 400,
        ScrollbarWidth = 12,
        ScrollbarReach = 8,
        ContentPadding = 3,
        DividerWidth = 280,
        DividerHeight = 16,
        HeaderHeight = 55,
        TitlePadding = 50,
        TitleGap = 8,
    },
    Footer = {
        TopPadding = 12,
        BottomPadding = 12,
        ButtonHeight = 20,
        RowSpacing = 6,
        SidePadding = 5,
        ButtonSpacing = 8,
    },
    Widget = {
        Width = 240,
        Height = 26,
        LabelWidth = 100,
        LabelGap = 3,
        ValueWidth = 65,
        ValueInset = 3,
        ValueSwatchSize = 21,
        ValueCheckboxSize = 26,
        CheckboxIconWidth = 32,
        CheckboxIconGap = 4,
    },
    Texture = {
        CheckboxCheck = 130751,
        ReadyCheckNotReady = 136813,
        White = 130871,
        ChatBackground = 130937,
        TooltipBorder = 137057,
    },
    Strata = { Dialog = "DIALOG", FullscreenDialog = "FULLSCREEN_DIALOG", Topmost = "TOOLTIP" },
    DialogBackdrop = { r = 0, g = 0, b = 0, a = 0.85 },
}
for _, values in pairs(DEFAULT_CONSTANTS) do
    table.freeze(values)
end
table.freeze(DEFAULT_CONSTANTS)
Config.Defaults = DEFAULT_CONSTANTS

function Config.Install(target, options)
    assert(options.tooltip and options.tooltipHide, "LibOrbitUI config needs a private tooltip")
    local context = target.context
        or { pixel = options.pixel, tooltip = options.tooltip, tooltipHide = options.tooltipHide }
    assert(context.pixel, "LibOrbitUI config needs a pixel context")
    target.configOptions = {
        constants = options.constants or DEFAULT_CONSTANTS,
        tooltip = options.tooltip,
        tooltipHide = options.tooltipHide,
        mergedLabel = options.mergedLabel,
        pixel = context.pixel,
    }
    target.CreateSlider = Config.CreateSlider
    target.CreateRangeSlider = Config.CreateRangeSlider
    target.CreateCheckbox = Config.CreateCheckbox
    target.ReleaseCompactCheckbox = Config.ReleaseCompactCheckbox
    target.CreateButton = Config.CreateButton
    target.CreateEditBox = Config.CreateEditBox
    target.CreateFormatInput = Config.CreateFormatInput
    target.CreatePickerControl = Config.CreatePickerControl
    target.BindPickerDropdown = Config.BindPickerDropdown
    target.LayoutPickerLabelAndControl = Config.LayoutPickerLabelAndControl
    target.CreateDropdown = Config.CreateDropdown
    target.mediaMenu =
        UI.MediaMenu:CreateProvider(context, target, target.configOptions.constants, options.isPreferredItem)
    Config.InstallPickerWidgets(target, {
        color = options.color or Config.CreateColorProvider(context),
        media = options.media,
    })
    return target
end
