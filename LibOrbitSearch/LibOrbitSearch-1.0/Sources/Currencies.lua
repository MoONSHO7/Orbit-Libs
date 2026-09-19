-- [ CURRENCIES SOURCE ]------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end
local Native = lib._NativeContract

local function OpenCurrencyTab()
    if not TokenFrame or not ToggleCharacter then
        return
    end
    ToggleCharacter("TokenFrame")
end

local Currencies = {
    kind = "currencies",
    events = { "CURRENCY_DISPLAY_UPDATE" },
}

function Currencies:GetAvailability()
    return Native.Require(
        C_CurrencyInfo,
        "GetCurrencyListSize",
        "GetCurrencyListInfo",
        "ExpandCurrencyList",
        "GetCurrencyListLink"
    )
end

local function WithAllExpanded(fn)
    local expanded = {}
    -- Restore the exact expanded indices in reverse, including nested headers with identical names.
    local ok, err = pcall(function()
        local index = 1
        while index <= C_CurrencyInfo.GetCurrencyListSize() do
            local info = C_CurrencyInfo.GetCurrencyListInfo(index)
            if info and info.isHeader and not info.isHeaderExpanded then
                expanded[#expanded + 1] = index
                C_CurrencyInfo.ExpandCurrencyList(index, true)
            end
            index = index + 1
        end
        fn()
    end)
    for index = #expanded, 1, -1 do
        C_CurrencyInfo.ExpandCurrencyList(expanded[index], false)
    end
    if not ok then
        error(err, 0)
    end
end

function Currencies:Build()
    if C_CurrencyInfo.GetCurrencyListSize() == nil then
        return nil, "pending", "currency-list"
    end
    local entries = {}
    WithAllExpanded(function()
        local size = C_CurrencyInfo.GetCurrencyListSize() or 0
        local currentHeader
        for i = 1, size do
            local info = C_CurrencyInfo.GetCurrencyListInfo(i)
            if info and info.name and info.name ~= "" and not info.isTypeUnused then
                if info.isHeader then
                    currentHeader = info.name
                elseif info.currencyID and info.currencyID > 0 then
                    local folded = lib.Fold(info.name)
                    if currentHeader then
                        folded = folded .. " " .. lib.Fold(currentHeader)
                    end
                    entries[#entries + 1] = {
                        kind = "currencies",
                        id = info.currencyID,
                        name = info.name,
                        lowerName = folded,
                        icon = info.iconFileID,
                        count = info.quantity,
                        tooltipLink = C_CurrencyInfo.GetCurrencyListLink(i),
                        onClick = TokenFrame and ToggleCharacter and OpenCurrencyTab or nil,
                    }
                end
            end
        end
    end)
    return entries
end

lib:RegisterIndexSource("currencies", Currencies)
