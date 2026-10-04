local _, addon = ...
local UI = addon.LibOrbitUI
local Text = {}
UI.Text = Text

local SHADOW_BACKING_FONT = "GameFontHighlight"
local SETTLED_REPAIR_FRAMES = 2
local REPAIR_TIMEOUT_SECONDS = 10
local REPAIR_SOURCE = "Text.RepairRefusedFonts"

local refusedFonts = setmetatable({}, { __mode = "k" })
local repairFrame, repairUpdate

function Text.ApplyShadow(region, enabled, offsetX, offsetY)
    if enabled then
        region:SetShadowColor(0, 0, 0, 1)
        region:SetShadowOffset(offsetX, offsetY)
    else
        region:SetShadowOffset(0, 0)
    end
end

-- A font-object backing enables shadows, but replacing it resets the region's colour and justification.
local function SetBackedFont(region, path, size, flags)
    local r, g, b, a = region:GetTextColor()
    local justifyH = region.GetJustifyH and region:GetJustifyH()
    local justifyV = region.GetJustifyV and region:GetJustifyV()
    region:SetFontObject(SHADOW_BACKING_FONT)
    local accepted = region:SetFont(path, size, flags) ~= false
    region:SetTextColor(r, g, b, a)
    if justifyH then
        region:SetJustifyH(justifyH)
    end
    if justifyV then
        region:SetJustifyV(justifyV)
    end
    return accepted
end

local function RepairRefusedFonts(frame)
    local now = GetTime()
    for region, request in pairs(refusedFonts) do
        request.expiresAt = request.expiresAt or now + REPAIR_TIMEOUT_SECONDS
        local shadowR, shadowG, shadowB, shadowA = region:GetShadowColor()
        local shadowX, shadowY = region:GetShadowOffset()
        local accepted = SetBackedFont(region, request.path, request.size, request.flags)
        region:SetShadowColor(shadowR, shadowG, shadowB, shadowA)
        region:SetShadowOffset(shadowX, shadowY)
        request.acceptedFrames = accepted and request.acceptedFrames + 1 or 0
        if request.acceptedFrames >= SETTLED_REPAIR_FRAMES or now > request.expiresAt then
            refusedFonts[region] = nil
        end
    end
    if not next(refusedFonts) then
        frame:SetScript("OnUpdate", nil)
    end
end

-- A cold client refuses SetFont until the file loads, then applies the refused request on a later frame, overwriting
-- newer fonts; reapplying the latest request after that frame keeps the caller's final font.
local function TrackRefusedFont(region, path, size, flags, accepted)
    local request = refusedFonts[region]
    if accepted and not request then
        return
    end
    if not request then
        request = {}
        refusedFonts[region] = request
    end
    request.path, request.size, request.flags, request.acceptedFrames = path, size, flags, 0
    if not repairFrame then
        repairFrame = CreateFrame("Frame")
        repairUpdate = UI.Callbacks:Wrap(RepairRefusedFonts, REPAIR_SOURCE)
    end
    repairFrame:SetScript("OnUpdate", repairUpdate)
end

function Text.ApplyFont(region, path, size, flags)
    TrackRefusedFont(region, path, size, flags, SetBackedFont(region, path, size, flags))
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
        refusedFonts[region] = nil
        region:SetFontObject(font)
    end
end

table.freeze(Text)
