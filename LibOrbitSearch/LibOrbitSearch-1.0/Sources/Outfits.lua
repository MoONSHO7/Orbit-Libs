-- [ OUTFITS SOURCE ]----------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract
local Outfits = {
    kind = "outfits",
    events = { "TRANSMOG_OUTFITS_CHANGED", "TRANSMOG_DISPLAYED_OUTFIT_CHANGED" },
}

function Outfits:GetAvailability()
    local state, reason = Native.Require(C_TransmogOutfitInfo, "GetOutfitsInfo", "IsTransmogEnabled")
    if state ~= "ready" then
        return state, reason
    end
    if not C_TransmogOutfitInfo.IsTransmogEnabled() then
        return "pending", "transmog-disabled"
    end
    return "ready"
end

function Outfits:Build()
    local outfits = C_TransmogOutfitInfo.GetOutfitsInfo()
    if not outfits then
        return nil, "pending", "outfits"
    end
    local canChange = Native.Require(C_TransmogOutfitInfo, "ChangeToOutfit") == "ready"
    local entries = {}
    for _, info in ipairs(outfits) do
        if info.outfitID and info.name and info.name ~= "" then
            local topic = info.situationCategories and table.concat(info.situationCategories, ", ") or nil
            topic = topic ~= "" and topic or nil
            local index = info.playerFacingOutfitIndex
            entries[#entries + 1] = {
                kind = "outfits",
                id = info.outfitID,
                name = info.name,
                lowerName = lib.Fold(info.name .. " " .. (topic or "")),
                icon = info.icon,
                topic = topic,
                -- Secure outfit actions address the player-facing index, never the stable collection ID.
                secure = canChange and not info.isDisabled and type(index) == "number" and {
                    type = "outfit",
                    action = "change",
                    ["outfit-index"] = index,
                } or nil,
            }
        end
    end
    return entries
end

lib:RegisterIndexSource("outfits", Outfits)
