-- [ EQUIPMENT SETS SOURCE ]---------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract
local EquipmentSets = {
    kind = "equipmentsets",
    events = { "EQUIPMENT_SETS_CHANGED", "EQUIPMENT_SWAP_FINISHED", "PLAYER_EQUIPMENT_CHANGED" },
}

function EquipmentSets:GetAvailability()
    return Native.Require(C_EquipmentSet, "GetEquipmentSetIDs", "GetEquipmentSetInfo")
end

function EquipmentSets:Build()
    local ids = C_EquipmentSet.GetEquipmentSetIDs()
    if not ids then
        return nil, "pending", "equipment-sets"
    end
    local canEquip = Native.Require(C_EquipmentSet, "GetEquipmentSetID", "UseEquipmentSet") == "ready"
    local entries = {}
    for _, setID in ipairs(ids) do
        local name, icon, nativeID, _, numItems, numEquipped = C_EquipmentSet.GetEquipmentSetInfo(setID)
        if name and name ~= "" and nativeID == setID then
            entries[#entries + 1] = {
                kind = "equipmentsets",
                id = setID,
                name = name,
                lowerName = lib.Fold(name),
                icon = icon,
                topic = numItems and numEquipped and (numEquipped .. " / " .. numItems) or nil,
                secure = canEquip and { type = "equipmentset", equipmentset = name } or nil,
            }
        end
    end
    return entries
end

lib:RegisterIndexSource("equipmentsets", EquipmentSets)
