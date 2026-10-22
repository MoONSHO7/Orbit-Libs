-- [ REPUTATION SOURCE ]-------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract
local Reputation = {
    kind = "reputation",
    events = {
        "UPDATE_FACTION",
        "FACTION_STANDING_CHANGED",
        "MAJOR_FACTION_RENOWN_LEVEL_CHANGED",
        "MAJOR_FACTION_UNLOCKED",
    },
}

function Reputation:GetAvailability()
    return Native.Require(
        C_Reputation,
        "GetNumFactions",
        "GetFactionDataByIndex",
        "ExpandFactionHeader",
        "CollapseFactionHeader",
        "GetSelectedFaction",
        "SetSelectedFaction"
    )
end

function Reputation:ShouldInvalidate(event)
    return not (self.expandingHeaders and event == "UPDATE_FACTION")
end

local function WithExpandedFactions(callback, retainExpansion)
    local expanded = {}
    local selected = C_Reputation.GetSelectedFaction()
    Reputation.expandingHeaders = true
    local ok, result = pcall(function()
        local index = 1
        while index <= C_Reputation.GetNumFactions() do
            local info = C_Reputation.GetFactionDataByIndex(index)
            if info and info.isHeader and info.isCollapsed then
                expanded[#expanded + 1] = index
                C_Reputation.ExpandFactionHeader(index)
            end
            index = index + 1
        end
        return callback()
    end)
    -- Header expansion changes list indices; restore in reverse before restoring native selection.
    local restored, restoreError = pcall(function()
        if not (ok and result and retainExpansion) then
            for index = #expanded, 1, -1 do
                C_Reputation.CollapseFactionHeader(expanded[index])
            end
            if C_Reputation.GetSelectedFaction() ~= selected then
                C_Reputation.SetSelectedFaction(selected)
                if EventRegistry then
                    EventRegistry:TriggerEvent("ReputationFrame.NewFactionSelected")
                end
            end
        end
    end)
    Reputation.expandingHeaders = nil
    if not restored then
        error(restoreError, 0)
    end
    if not ok then
        error(result, 0)
    end
    return result
end

local function OpenFaction(factionID)
    if InCombatLockdown() or Reputation:GetAvailability() ~= "ready" then
        return
    end
    if not ReputationFrame and C_AddOns and C_AddOns.LoadAddOn then
        C_AddOns.LoadAddOn("Blizzard_UIPanels_Game")
    end
    if not ReputationFrame or not ToggleCharacter then
        return
    end
    WithExpandedFactions(function()
        for index = 1, C_Reputation.GetNumFactions() do
            local info = C_Reputation.GetFactionDataByIndex(index)
            if info and info.factionID == factionID then
                ToggleCharacter("ReputationFrame", true)
                C_Reputation.SetSelectedFaction(index)
                if CharacterFrame and CharacterFrame.SetRightPaneCollapsed then
                    CharacterFrame:SetRightPaneCollapsed(false)
                end
                if EventRegistry then
                    EventRegistry:TriggerEvent("ReputationFrame.NewFactionSelected")
                end
                return true
            end
        end
    end, true)
end

local function GetStanding(info)
    if
        not C_GossipInfo
        or not C_GossipInfo.GetFriendshipReputation
        or not C_Reputation.IsMajorFaction
        or not info.reaction
    then
        return ""
    end
    local friendship = C_GossipInfo.GetFriendshipReputation(info.factionID)
    if friendship and friendship.friendshipFactionID > 0 then
        return friendship.reaction or ""
    end
    if C_Reputation.IsMajorFaction(info.factionID) then
        return ""
    end
    local key = "FACTION_STANDING_LABEL" .. info.reaction
    local standing
    if GetText and UnitSex then
        standing = GetText(key, UnitSex("player"))
    else
        standing = _G[key]
    end
    if
        standing
        and info.reaction ~= MAX_REPUTATION_REACTION
        and type(info.currentStanding) == "number"
        and type(info.currentReactionThreshold) == "number"
        and type(info.nextReactionThreshold) == "number"
        and info.nextReactionThreshold > info.currentReactionThreshold
        and REPUTATION_PROGRESS_FORMAT
        and BreakUpLargeNumbers
    then
        local current = info.currentStanding - info.currentReactionThreshold
        local maximum = info.nextReactionThreshold - info.currentReactionThreshold
        standing = standing
            .. " · "
            .. string.format(REPUTATION_PROGRESS_FORMAT, BreakUpLargeNumbers(current), BreakUpLargeNumbers(maximum))
    end
    return standing or ""
end

function Reputation:Build()
    if C_Reputation.GetNumFactions() == nil then
        return nil, "pending", "reputation"
    end
    return WithExpandedFactions(function()
        local entries = {}
        for index = 1, C_Reputation.GetNumFactions() do
            local info = C_Reputation.GetFactionDataByIndex(index)
            if
                info
                and info.factionID
                and info.factionID > 0
                and (not info.isHeader or info.isHeaderWithRep)
                and info.name
                and info.name ~= ""
            then
                local factionID = info.factionID
                local standing = GetStanding(info)
                entries[#entries + 1] = {
                    kind = "reputation",
                    id = factionID,
                    name = info.name,
                    lowerName = lib.Fold(info.name .. " " .. standing .. " " .. (info.description or "")),
                    topic = standing ~= "" and standing or nil,
                    description = info.description,
                    onClick = function()
                        OpenFaction(factionID)
                    end,
                }
            end
        end
        return entries
    end)
end

lib:RegisterIndexSource("reputation", Reputation)
