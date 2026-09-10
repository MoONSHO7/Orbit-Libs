local _, addon = ...
local UI = addon.LibOrbitUI
local WOW_REFERENCE_HEIGHT = 768

UI.Pixel = {}

function UI.Pixel:Create(options)
    options = options or {}
    local Pixel = {}
    local screenScale = 1

    local function UpdateScreenScale()
        local _, physicalHeight = GetPhysicalScreenSize()
        local newScale
        if not physicalHeight or physicalHeight == 0 then
            newScale = WOW_REFERENCE_HEIGHT / 1080
        else
            newScale = WOW_REFERENCE_HEIGHT / physicalHeight
        end

        if screenScale == newScale then
            return
        end
        screenScale = newScale
        if options.onDisplayChanged then
            options.onDisplayChanged(screenScale)
        end
    end

    local eventFrame = CreateFrame("Frame")
    eventFrame:RegisterEvent("DISPLAY_SIZE_CHANGED")
    eventFrame:RegisterEvent("UI_SCALE_CHANGED")
    eventFrame:RegisterEvent("PLAYER_ENTERING_WORLD")
    eventFrame:SetScript("OnEvent", function()
        local ok, err = pcall(UpdateScreenScale)
        if not ok then
            geterrorhandler()(err)
        end
    end)
    UpdateScreenScale()

    function Pixel:GetScale()
        return screenScale
    end

    function Pixel:Snap(value, scale)
        if not value then
            return 0
        end
        if issecretvalue(value) then
            return value
        end

        local pixelScale = screenScale
        local frameScale = scale or 1
        if frameScale < 0.01 then
            frameScale = 1
        end

        local step = pixelScale / frameScale
        return math.floor(value / step + 0.5) * step
    end

    -- Center-anchored odd pixel sizes cannot place both edges on the grid.
    function Pixel:EvenSnap(value, scale)
        if not value then
            return 0
        end
        if issecretvalue(value) then
            return value
        end
        local frameScale = scale or 1
        if frameScale < 0.01 then
            frameScale = 1
        end
        local step = screenScale / frameScale
        return math.floor(value / (2 * step) + 0.5) * 2 * step
    end

    function Pixel:SnapSize(width, height, scale, centerAnchored)
        if centerAnchored then
            return self:EvenSnap(width, scale), self:EvenSnap(height, scale)
        end
        return self:Snap(width, scale), self:Snap(height, scale)
    end

    function Pixel:SnapDockedSize(width, height, scale, edge, componentReference, span, align)
        local centerX = componentReference == "CENTER" and (edge == "LEFT" or edge == "RIGHT")
        local centerY = componentReference == "CENTER" and (edge == "TOP" or edge == "BOTTOM")
        if not span and (align or "CENTER") == "CENTER" then
            centerX = centerX or edge == "TOP" or edge == "BOTTOM"
            centerY = centerY or edge == "LEFT" or edge == "RIGHT"
        end
        width = centerX and self:EvenSnap(width, scale) or self:Snap(width, scale)
        height = centerY and self:EvenSnap(height, scale) or self:Snap(height, scale)
        return width, height
    end

    function Pixel:Point(frame, point, a, b, c, d)
        local s = frame:GetEffectiveScale()
        if type(a) == "number" or a == nil then
            frame:SetPoint(point, self:Multiple(a or 0, s), self:Multiple(b or 0, s))
        else
            frame:SetPoint(point, a, b, self:Multiple(c or 0, s), self:Multiple(d or 0, s))
        end
    end

    function Pixel:Multiple(count, scale)
        local n = count or 0
        if issecretvalue(n) then
            return n
        end
        if n == 0 then
            return 0
        end
        local sign = n > 0 and 1 or -1
        local abs = math.abs(n)
        if issecretvalue(scale) then
            return n
        end
        local frameScale = scale or 1
        if frameScale < 0.01 then
            frameScale = 1
        end
        local step = screenScale / frameScale
        return sign * math.max(math.floor(abs + 0.5), 1) * step
    end

    function Pixel:ToCount(value, scale)
        if not value or issecretvalue(value) then
            return 0
        end
        local frameScale = scale or 1
        if frameScale < 0.01 then
            frameScale = 1
        end
        local count = value / (screenScale / frameScale)
        local sign = count < 0 and -1 or 1
        return sign * math.floor(math.abs(count) + 0.5)
    end

    function Pixel:BorderInset(frame, fallbackSize)
        if frame and frame.borderPixelSize then
            return frame.borderPixelSize
        end
        return self:Multiple(fallbackSize or 0, frame:GetEffectiveScale())
    end

    function Pixel:DefaultBorderSize(scale)
        return self:Multiple(1, scale)
    end

    function Pixel:SnapPosition(x, y, point, width, height, scale)
        local centerX = not (point:find("LEFT", 1, true) or point:find("RIGHT", 1, true))
        local centerY = not (point:find("TOP", 1, true) or point:find("BOTTOM", 1, true))

        if centerX and width and not issecretvalue(width) then
            x = self:Snap(x - (width / 2), scale) + (width / 2)
        else
            x = self:Snap(x, scale)
        end
        if centerY and height and not issecretvalue(height) then
            y = self:Snap(y - (height / 2), scale) + (height / 2)
        else
            y = self:Snap(y, scale)
        end
        return x, y
    end

    function Pixel:Enforce(frame, opts)
        if not frame then
            return
        end
        if opts and opts.centerAnchored then
            frame.orbitEvenSnap = true
        end

        if not frame.OrbitNativeSetWidth then
            frame.OrbitNativeSetWidth = frame.SetWidth
            frame.SetWidth = function(self, width)
                local snap = self.orbitEvenSnap and Pixel.EvenSnap or Pixel.Snap
                self:OrbitNativeSetWidth(snap(Pixel, width, self:GetEffectiveScale()))
            end
        end

        if not frame.OrbitNativeSetHeight then
            frame.OrbitNativeSetHeight = frame.SetHeight
            frame.SetHeight = function(self, height)
                local snap = self.orbitEvenSnap and Pixel.EvenSnap or Pixel.Snap
                self:OrbitNativeSetHeight(snap(Pixel, height, self:GetEffectiveScale()))
            end
        end

        if not frame.OrbitNativeSetSize then
            frame.OrbitNativeSetSize = frame.SetSize
            frame.SetSize = function(self, width, height)
                local scale = self:GetEffectiveScale()
                local snap = self.orbitEvenSnap and Pixel.EvenSnap or Pixel.Snap
                self:OrbitNativeSetSize(snap(Pixel, width, scale), snap(Pixel, height, scale))
            end
        end

        if opts and opts.scale and not frame.OrbitNativeSetScale then
            frame.OrbitNativeSetScale = frame.SetScale
            frame.SetScale = function(self, s)
                self:OrbitNativeSetScale(s)
                local w, h = self:GetSize()
                if w and h and w > 0 and h > 0 then
                    self:SetSize(w, h)
                end
            end
        end

        local w, h = frame:GetSize()
        if w and h then
            frame:SetSize(w, h)
        end
    end

    function Pixel:Destroy()
        eventFrame:UnregisterAllEvents()
        eventFrame:SetScript("OnEvent", nil)
    end

    return Pixel
end
