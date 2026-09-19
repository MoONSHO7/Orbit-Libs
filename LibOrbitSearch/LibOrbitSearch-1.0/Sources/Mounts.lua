-- [ MOUNTS SOURCE ]----------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end
local Native = lib._NativeContract

local Mounts = {
    kind = "mounts",
    events = {
        "NEW_MOUNT_ADDED",
        "COMPANION_LEARNED",
        "COMPANION_UNLEARNED",
        "MOUNT_JOURNAL_SEARCH_UPDATED",
        "SPELLS_CHANGED",
    },
}

function Mounts:GetAvailability()
    return Native.Require(C_MountJournal, "GetMountIDs", "GetMountInfoByID")
end

function Mounts:Build()
    local entries = {}
    local ids = C_MountJournal.GetMountIDs()
    if not ids then
        return nil, "pending", "mount-list"
    end
    local MountTypeTags = lib._MountTypeTags
    MountTypeTags.RefreshDragonriding()
    for _, mountID in ipairs(ids) do
        local name, _, icon, _, _, _, favorite, _, _, _, isCollected, _, steadyFlight =
            C_MountJournal.GetMountInfoByID(mountID)
        if name and isCollected then
            local folded = lib.Fold(name)
            local tags = MountTypeTags.ForMount(mountID, steadyFlight)
            if tags then
                folded = folded .. " " .. tags
            end
            entries[#entries + 1] = {
                kind = "mounts",
                id = mountID,
                name = name,
                lowerName = folded,
                icon = icon,
                favorite = favorite or false,
                passive = not C_MountJournal.SummonByID,
                secure = C_MountJournal.SummonByID
                        and { type = "macro", macrotext = "/run C_MountJournal.SummonByID(" .. mountID .. ")" }
                    or nil,
            }
        end
    end
    return entries
end

lib:RegisterIndexSource("mounts", Mounts)
