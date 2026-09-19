-- [ MACROS SOURCE ]----------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract

local Macros = {
    kind = "macros",
    events = { "UPDATE_MACROS" },
}

function Macros:GetAvailability()
    if not Constants or not Constants.MacroConsts or type(Constants.MacroConsts.MAX_ACCOUNT_MACROS) ~= "number" then
        return "unsupported", "missing:macro-limits"
    end
    return Native.Require(_G, "GetNumMacros", "GetMacroInfo")
end

function Macros:Build()
    local entries = {}
    local global, perChar = GetNumMacros()
    global = global or 0
    perChar = perChar or 0

    for i = 1, global do
        local name, iconID = GetMacroInfo(i)
        if name then
            entries[#entries + 1] = {
                kind = "macros",
                id = i,
                name = name,
                lowerName = lib.Fold(name),
                icon = iconID,
                secure = { type = "macro", macro = i },
            }
        end
    end

    local charStart = Constants.MacroConsts.MAX_ACCOUNT_MACROS + 1
    for i = charStart, charStart + perChar - 1 do
        local name, iconID = GetMacroInfo(i)
        if name then
            entries[#entries + 1] = {
                kind = "macros",
                id = i,
                name = name,
                lowerName = lib.Fold(name),
                icon = iconID,
                secure = { type = "macro", macro = i },
            }
        end
    end
    return entries
end

lib:RegisterIndexSource("macros", Macros)
