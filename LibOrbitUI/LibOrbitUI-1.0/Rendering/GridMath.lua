local _, addon = ...

local GridMath = {}
addon.LibOrbitUI.GridMath = GridMath

function GridMath.ComputeGridPosition(index, limitPerLine, orientation, width, height, padding)
    local row, column
    if orientation == 0 then
        row = math.floor((index - 1) / limitPerLine)
        column = (index - 1) % limitPerLine
    else
        column = math.floor((index - 1) / limitPerLine)
        row = (index - 1) % limitPerLine
    end
    return column * (width + padding), -row * (height + padding)
end

function GridMath.ComputeGridContainerSize(numItems, limitPerLine, orientation, width, height, padding)
    local rows, columns
    if orientation == 0 then
        columns = math.min(numItems, limitPerLine)
        rows = math.ceil(numItems / limitPerLine)
    else
        rows = math.min(numItems, limitPerLine)
        columns = math.ceil(numItems / limitPerLine)
    end
    local finalWidth = (columns * width) + (math.max(0, columns - 1) * padding)
    local finalHeight = (rows * height) + (math.max(0, rows - 1) * padding)
    return math.max(finalWidth, width), math.max(finalHeight, height)
end

table.freeze(GridMath)
