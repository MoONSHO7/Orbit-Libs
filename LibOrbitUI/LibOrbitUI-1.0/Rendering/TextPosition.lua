local _, addon = ...
local TextPosition = {}
addon.LibOrbitUI.TextPosition = TextPosition

function TextPosition.BuildAnchorPoint(anchorX, anchorY)
    if anchorY == "CENTER" and anchorX == "CENTER" then
        return "CENTER"
    elseif anchorY == "CENTER" then
        return anchorX
    elseif anchorX == "CENTER" then
        return anchorY
    end
    return anchorY .. anchorX
end

function TextPosition.PlaceLogical(pixel, region, parent, point, relativePoint, x, y, scale, width, height)
    x, y = pixel:SnapPosition(x, y, point, width, height, scale)
    region:SetPoint(point, parent, relativePoint, x, y)
end

function TextPosition.CreateSetter(pixel)
    return function(region, parent, position, anchor, x, y)
        local point = anchor
        if position and position.anchorX and position.anchorY then
            point = TextPosition.BuildAnchorPoint(position.anchorX, position.anchorY)
            x, y = position.offsetX or 0, position.offsetY or 0
        end
        region:ClearAllPoints()
        pixel:Point(region, point, parent, point, x, y)
        if region.SetJustifyH then
            region:SetJustifyH(position and position.justifyH or "CENTER")
        end
    end
end

table.freeze(TextPosition)
