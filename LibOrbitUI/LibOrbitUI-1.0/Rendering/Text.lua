local _, addon = ...
local Text = {}
addon.LibOrbitUI.Text = Text

local SHADOW_BACKING_FONT = "GameFontHighlight"

function Text.ApplyShadow(region, enabled, offsetX, offsetY)
    if enabled then
        region:SetShadowColor(0, 0, 0, 1)
        region:SetShadowOffset(offsetX, offsetY)
    else
        region:SetShadowOffset(0, 0)
    end
end

-- A font-object backing enables shadows, but replacing it resets the region's colour and justification.
function Text.ApplyFont(region, path, size, flags)
    local r, g, b, a = region:GetTextColor()
    local justifyH = region.GetJustifyH and region:GetJustifyH()
    local justifyV = region.GetJustifyV and region:GetJustifyV()
    region:SetFontObject(SHADOW_BACKING_FONT)
    region:SetFont(path, size, flags)
    region:SetTextColor(r, g, b, a)
    if justifyH then
        region:SetJustifyH(justifyH)
    end
    if justifyV then
        region:SetJustifyV(justifyV)
    end
end

function Text.CreateFontSetter(pixel, namePrefix, shadowOffsetX, shadowOffsetY)
    local fonts = {}
    local fontCount = 0
    return function(region, path, size, flags)
        flags = flags or ""
        local key = path .. ":" .. tostring(size) .. ":" .. flags
        local font = fonts[key]
        if not font then
            fontCount = fontCount + 1
            font = CreateFont(namePrefix .. tostring(fontCount))
            font:SetFont(path, size, flags)
            local scale = UIParent:GetEffectiveScale()
            Text.ApplyShadow(font, true, pixel:Multiple(shadowOffsetX, scale), pixel:Multiple(shadowOffsetY, scale))
            fonts[key] = font
        end
        region:SetFontObject(font)
    end
end

table.freeze(Text)
