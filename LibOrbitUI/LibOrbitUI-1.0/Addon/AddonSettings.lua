local _, addon = ...
local UI = addon.LibOrbitUI
local AddonMixin = UI.AddonMixin

function AddonMixin:ShowSettings(index)
    index = index or 1
    local options = self.options
    if not self.ready then
        print(options.title .. ": " .. options.labels.notReady)
        return
    end
    local dialog = self.dialogs[index]
    if not dialog then
        local tabs = {}
        for tabIndex, descriptor in ipairs(options.tabs(index)) do
            local tab = {}
            for key, value in pairs(descriptor) do
                tab[key] = value
            end
            tabs[tabIndex] = tab
        end
        local first = tabs[1]
        local controls = first.controls
        first.controls = function()
            local result = {
                {
                    type = "checkbox",
                    label = options.labels.enabled,
                    default = true,
                    getValue = function()
                        return self:IsEnabled()
                    end,
                    onChange = function(enabled)
                        self:SetEnabled(enabled)
                    end,
                },
            }
            for _, control in ipairs(type(controls) == "function" and controls() or controls) do
                result[#result + 1] = control
            end
            return result
        end
        dialog = UI.Config.CreateDialog(self.context, {
            name = options.name .. "Settings" .. index,
            title = options.settingsTitles and options.settingsTitles[index] or options.title,
            closeLabel = options.labels.close,
            tabs = tabs,
            color = options.color,
            media = options.media,
            registerWidgets = options.registerWidgets,
            get = function(key)
                return self.controller:GetSetting(index, key)
            end,
            set = function(key, value)
                self.controller:SetSetting(index, key, value)
            end,
            onChange = function()
                self:Apply()
            end,
            footerButtons = function()
                local buttons = {}
                if not self:IsEditMode() then
                    buttons[#buttons + 1] = {
                        label = options.labels.edit,
                        onClick = function()
                            self:EnterEditMode()
                        end,
                    }
                end
                buttons[#buttons + 1] = {
                    label = options.labels.reset,
                    onClick = function()
                        self:ResetPosition(index)
                    end,
                }
                return buttons
            end,
        })
        self.dialogs[index] = dialog
        EventRegistry:RegisterCallback("EditMode.Enter", dialog.Refresh, dialog)
        EventRegistry:RegisterCallback("EditMode.Exit", dialog.Refresh, dialog)
    end
    if dialog:IsShown() then
        dialog:Refresh()
    else
        dialog:Show()
    end
end

table.freeze(AddonMixin)
