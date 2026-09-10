local _, addon = ...
local UI = addon.LibOrbitUI
local math_max, math_min = math.max, math.min
local tsort = table.sort
local SamplerMixin = {}
UI.ColorCurve = {}

local function DefaultPin(pin)
    if pin.type == "class" then
        local _, class = UnitClass("player")
        local color = not issecretvalue(class) and class and RAID_CLASS_COLORS[class]
        if color then
            return { r = color.r, g = color.g, b = color.b, a = 1 }
        end
    end
    return pin.color or { r = 1, g = 1, b = 1, a = 1 }
end

function SamplerMixin:GetSortedPins(curveData)
    if self.sortedPinCache[curveData] then
        return self.sortedPinCache[curveData]
    end
    local sorted = {}
    for _, p in ipairs(curveData.pins) do
        sorted[#sorted + 1] = p
    end
    tsort(sorted, function(a, b)
        return a.position < b.position
    end)
    self.sortedPinCache[curveData] = sorted
    return sorted
end

function SamplerMixin:CurveHasClassPin(curveData)
    if not curveData or not curveData.pins then
        return false
    end
    if self.classPinCache[curveData] ~= nil then
        return self.classPinCache[curveData]
    end
    for _, pin in ipairs(curveData.pins) do
        if pin.type == "class" then
            self.classPinCache[curveData] = true
            return true
        end
    end
    self.classPinCache[curveData] = false
    return false
end

local function FindBracket(self, curveData, position)
    local sorted = self:GetSortedPins(curveData)
    position = math_max(0, math_min(1, position))
    local first, last = sorted[1], sorted[#sorted]
    if position <= first.position then
        return first
    end
    if position >= last.position then
        return last
    end
    for i = 1, #sorted - 1 do
        local left, right = sorted[i], sorted[i + 1]
        if left.position <= position and right.position >= position then
            local range = right.position - left.position
            local t = (range > 0) and math_max(0, math_min(1, (position - left.position) / range)) or 0
            return left, right, t
        end
    end
    return last
end

function SamplerMixin:SampleColorCurve(curveData, position)
    if not curveData or not curveData.pins or #curveData.pins == 0 then
        return nil
    end
    local left, right, t = FindBracket(self, curveData, position)
    if not right then
        return self.resolvePin(left)
    end
    local leftColor = self.resolvePin(left)
    local rightColor = self.resolvePin(right)
    return {
        r = leftColor.r + (rightColor.r - leftColor.r) * t,
        g = leftColor.g + (rightColor.g - leftColor.g) * t,
        b = leftColor.b + (rightColor.b - leftColor.b) * t,
        a = (leftColor.a or 1) + ((rightColor.a or 1) - (leftColor.a or 1)) * t,
    }
end

function SamplerMixin:SampleColorCurveUnpacked(curveData, position)
    if not curveData or not curveData.pins or #curveData.pins == 0 then
        return nil
    end
    local left, right, t = FindBracket(self, curveData, position)
    if not right then
        return self.resolvePinUnpacked(left)
    end
    local lr, lg, lb, la = self.resolvePinUnpacked(left)
    local rr, rg, rb, ra = self.resolvePinUnpacked(right)
    return lr + (rr - lr) * t, lg + (rg - lg) * t, lb + (rb - lb) * t, la + (ra - la) * t
end

function SamplerMixin:GetFirstColorFromCurve(curveData)
    if not curveData or not curveData.pins or #curveData.pins == 0 then
        return nil
    end
    return self.resolvePin(self:GetSortedPins(curveData)[1])
end

function SamplerMixin:GetFirstColorFromCurveUnpacked(curveData)
    if not curveData or not curveData.pins or #curveData.pins == 0 then
        return nil
    end
    return self.resolvePinUnpacked(self:GetSortedPins(curveData)[1])
end

table.freeze(SamplerMixin)

function UI.ColorCurve:Create(options)
    options = options or {}
    local resolvePin = options.resolvePin or DefaultPin
    return Mixin({
        resolvePin = resolvePin,
        resolvePinUnpacked = options.resolvePinUnpacked or function(pin)
            local color = resolvePin(pin)
            return color.r, color.g, color.b, color.a or 1
        end,
        sortedPinCache = setmetatable({}, { __mode = "k" }),
        classPinCache = setmetatable({}, { __mode = "k" }),
    }, SamplerMixin)
end
