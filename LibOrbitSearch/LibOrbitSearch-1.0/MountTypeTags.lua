-- [ MOUNT TYPE TAGS ]--------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

-- Unknown mount types stay unclassified; native steady-flight evidence supplies the flying tag.
local EXPLICIT = {
    [230] = "ground",
    [231] = "aquatic",
    [232] = "aquatic",
    [254] = "aquatic",
    [269] = "ground",
    [284] = "ridealong",
    [412] = "aquatic",
}
local FLYING_TAG = "flying"
local SKYRIDING_TAG = "skyriding"
table.freeze(EXPLICIT)

local Tags = {}
lib._MountTypeTags = Tags

local function BuildDragonridingSet()
    local set = {}
    if
        C_MountJournal
        and C_MountJournal.GetCollectedDragonridingMounts
        and C_MountJournal.IsDragonridingUnlocked
        and C_MountJournal.IsDragonridingUnlocked()
    then
        for _, id in ipairs(C_MountJournal.GetCollectedDragonridingMounts() or {}) do
            set[id] = true
        end
    end
    return set
end

function Tags.RefreshDragonriding()
    Tags._dragonridingSet = BuildDragonridingSet()
end

function Tags.ForMount(mountID, steadyFlight)
    if not mountID then
        return nil
    end
    if not Tags._dragonridingSet then
        Tags.RefreshDragonriding()
    end
    local mountTypeID
    if C_MountJournal and C_MountJournal.GetMountInfoExtraByID then
        mountTypeID = select(5, C_MountJournal.GetMountInfoExtraByID(mountID))
    end
    local base = steadyFlight and FLYING_TAG or mountTypeID and EXPLICIT[mountTypeID]
    if Tags._dragonridingSet[mountID] then
        base = base and base .. " " .. SKYRIDING_TAG or SKYRIDING_TAG
    end
    return base
end
