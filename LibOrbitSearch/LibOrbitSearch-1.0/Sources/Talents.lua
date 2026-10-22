local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract
local SPELL_REQUEST_CAPACITY = 256
local SPELL_RETRY_INTERVAL = 30
local Talents = {
    kind = "talents",
    spellRequests = lib._BoundedCache.Create(SPELL_REQUEST_CAPACITY),
    spellIDs = {},
    events = {
        "PLAYER_TALENT_UPDATE",
        "ACTIVE_TALENT_GROUP_CHANGED",
        { event = "PLAYER_SPECIALIZATION_CHANGED", unit = "player" },
        "TRAIT_CONFIG_UPDATED",
        "TRAIT_TREE_CHANGED",
        "TRAIT_NODE_CHANGED",
        "TRAIT_NODE_CHANGED_PARTIAL",
        "TRAIT_NODE_ENTRY_UPDATED",
        "TRAIT_SUB_TREE_CHANGED",
        "SPELL_TEXT_UPDATE",
        "SPELL_DATA_LOAD_RESULT",
    },
}

function Talents:ShouldInvalidate(event, spellID, success)
    if event == "SPELL_DATA_LOAD_RESULT" then
        return self.spellIDs[spellID] == true and success == true
    end
    if event == "SPELL_TEXT_UPDATE" then
        return self.spellIDs[spellID] == true
    end
    return true
end

function Talents:IsExpired()
    return self.nextRetry ~= nil and GetTime() >= self.nextRetry
end

local function GetConfigID()
    if C_SpecializationInfo and C_SpecializationInfo.GetCombatConfigIDForSpecGroup then
        if C_SpecializationInfo.GetActiveSpecGroup then
            return C_SpecializationInfo.GetCombatConfigIDForSpecGroup(C_SpecializationInfo.GetActiveSpecGroup())
        end
    elseif C_ClassTalents and C_ClassTalents.GetActiveConfigID then
        return C_ClassTalents.GetActiveConfigID()
    end
end

function Talents:GetAvailability()
    local state, reason =
        Native.Require(C_Traits, "GetConfigInfo", "GetTreeNodes", "GetNodeInfo", "GetEntryInfo", "GetDefinitionInfo")
    if state ~= "ready" then
        return state, reason
    end
    if not C_ClassTalents or not C_ClassTalents.GetActiveConfigID then
        state, reason = Native.Require(C_SpecializationInfo, "GetCombatConfigIDForSpecGroup", "GetActiveSpecGroup")
        if state ~= "ready" then
            return state, reason
        end
    end
    if not GetConfigID() then
        return "pending", "talent-config"
    end
    return "ready"
end

local function OpenTalent(entry)
    if InCombatLockdown() or GetConfigID() ~= entry.configID then
        return
    end
    if not PlayerSpellsUtil or not PlayerSpellsUtil.OpenToClassTalentsTab then
        return
    end
    PlayerSpellsUtil.OpenToClassTalentsTab()
    local frame = PlayerSpellsFrame and PlayerSpellsFrame.TalentsFrame
    if frame and frame.GetActiveTab and frame.SetTab then
        frame:SetTab(frame:GetActiveTab())
    end
    if frame and frame.OnPreviewSearchResultClicked then
        frame:OnPreviewSearchResultClicked({ name = entry.name })
    end
end

local function GetSpellField(spellID, method)
    if spellID and C_Spell and C_Spell[method] then
        return C_Spell[method](spellID)
    end
end

local function RequestSpell(spellID)
    if
        lib._indexSources.talents ~= Talents
        or not lib._includedKinds.talents
        or not spellID
        or not C_Spell
        or not C_Spell.RequestLoadSpellData
    then
        return
    end
    local now = GetTime()
    if Talents.requestSweepAt then
        Talents.lastRequestSweepAt = Talents.requestSweepAt
    end
    local requestedAt = Talents.spellRequests:Get(spellID)
    local shouldRequest = Talents.requestSweepAt ~= nil
        and (not requestedAt or now >= requestedAt + SPELL_RETRY_INTERVAL)
    if shouldRequest then
        requestedAt = now
        Talents.spellRequests:Set(spellID, requestedAt)
    end
    Talents.nextRetry = Talents.lastRequestSweepAt + SPELL_RETRY_INTERVAL
    if shouldRequest then
        C_Spell.RequestLoadSpellData(spellID)
    end
end

local function AppendEntry(entries, configID, treeID, node, entryID, info, rank, treeName, groups)
    if not info or not info.definitionID then
        return
    end
    local definition = C_Traits.GetDefinitionInfo(info.definitionID)
    if not definition then
        return
    end
    local spellID = definition.spellID
    if spellID then
        Talents.spellIDs[spellID] = true
    end
    local name = definition.overrideName
    if not name or name == "" then
        name = GetSpellField(spellID, "GetSpellName")
    end
    if not name or name == "" then
        Talents.pendingNames = true
        RequestSpell(spellID)
        return
    end
    local description = definition.overrideDescription or GetSpellField(spellID, "GetSpellDescription")
    if
        definition.overrideDescription == nil
        and C_Spell
        and C_Spell.GetSpellDescription
        and (not description or description == "")
    then
        RequestSpell(spellID)
    end
    local subtext = definition.overrideSubtext or GetSpellField(spellID, "GetSpellSubtext")
    local passive = GetSpellField(spellID, "IsSpellPassive") == true
    local keywords = lib._sourceKeywordTerms and lib._sourceKeywordTerms.talents
    local stateName = keywords and keywords[rank > 0 and "learned" or "unlearned"] or ""
    local rankText = TALENT_BUTTON_TOOLTIP_RANK_FORMAT and TALENT_BUTTON_TOOLTIP_RANK_FORMAT:format(rank, info.maxRanks)
    local labels = {}
    if treeName then
        labels[#labels + 1] = treeName
    end
    for _, groupID in ipairs(node.groupIDs or {}) do
        if groups[groupID] then
            labels[#labels + 1] = groups[groupID]
        end
    end
    local treeLabel = table.concat(labels, " / ")
    if rankText then
        labels[#labels + 1] = rankText
    end
    if stateName ~= "" then
        labels[#labels + 1] = stateName
    end
    local topic = table.concat(labels, " · ")
    local terms = { name, description or "", subtext or "", passive and SPELL_PASSIVE or "", topic }
    entries[#entries + 1] = {
        kind = "talents",
        id = treeID .. ":" .. node.ID .. ":" .. entryID,
        configID = configID,
        treeID = treeID,
        nodeID = node.ID,
        entryID = entryID,
        spellID = spellID,
        name = name,
        lowerName = lib.Fold(table.concat(terms, " ")),
        icon = definition.overrideIcon or GetSpellField(spellID, "GetSpellTexture"),
        description = description,
        treeName = treeLabel,
        topic = topic,
        subtext = subtext,
        rank = rank,
        maxRank = info.maxRanks,
        learned = rank > 0,
        passive = passive,
        onClick = PlayerSpellsUtil and PlayerSpellsUtil.OpenToClassTalentsTab and OpenTalent or nil,
    }
end

function Talents:Build()
    self.spellIDs = {}
    self.pendingNames = false
    self.nextRetry = nil
    local now = GetTime()
    local canRequest = not self.lastRequestSweepAt or now >= self.lastRequestSweepAt + SPELL_RETRY_INTERVAL
    self.requestSweepAt = canRequest and now or nil
    local configID = GetConfigID()
    local config = configID and C_Traits.GetConfigInfo(configID)
    if not config then
        return nil, "pending", "talent-config-info"
    end
    local entries, seen = {}, {}
    local tieredType = Enum and Enum.TraitNodeType and Enum.TraitNodeType.Tiered
    for _, treeID in ipairs(config.treeIDs) do
        local nodes = C_Traits.GetTreeNodes(treeID)
        if not nodes then
            return nil, "pending", "talent-tree"
        end
        local tree = C_Traits.GetTreeInfo and C_Traits.GetTreeInfo(configID, treeID)
        local groups = {}
        if C_Traits.GetGroupDisplayInfoByTreeID then
            for _, group in ipairs(C_Traits.GetGroupDisplayInfoByTreeID(treeID) or {}) do
                groups[group.groupID] = group.displayName
            end
        end
        for _, nodeID in ipairs(nodes) do
            if not seen[nodeID] then
                seen[nodeID] = true
                local node = C_Traits.GetNodeInfo(configID, nodeID)
                if node and node.isVisible then
                    local isTiered = tieredType ~= nil and node.type == tieredType
                    local remainingRanks = isTiered and node.ranksPurchased or 0
                    for _, entryID in ipairs(node.entryIDs) do
                        local info = C_Traits.GetEntryInfo(configID, entryID)
                        local rank = node.activeEntry and node.activeEntry.entryID == entryID and node.activeEntry.rank
                            or 0
                        if isTiered then
                            if not info then
                                return nil, "pending", "talent-entry"
                            end
                            rank = math.min(remainingRanks, info.maxRanks)
                            remainingRanks = math.max(remainingRanks - info.maxRanks, 0)
                        end
                        AppendEntry(
                            entries,
                            configID,
                            treeID,
                            node,
                            entryID,
                            info,
                            rank,
                            tree and tree.titleText,
                            groups
                        )
                    end
                end
            end
        end
    end
    if #entries == 0 and self.pendingNames then
        return nil, "pending", "talent-spell-data"
    end
    return entries
end

lib:RegisterIndexSource("talents", Talents)
