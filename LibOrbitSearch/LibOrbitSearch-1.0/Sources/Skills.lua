-- [ SKILLS SOURCE ]-----------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = lib._NativeContract
local CLASS_SKILLS_CATEGORY = 7
local Skills = {
    kind = "skills",
    events = { "SKILL_LINES_CHANGED" },
}

function Skills:GetAvailability()
    return Native.Require(
        C_SkillInfo,
        "GetNumSkillLines",
        "GetSkillLineInfo",
        "ExpandSkillHeader",
        "CollapseSkillHeader",
        "GetSelectedSkill",
        "SetSelectedSkill"
    )
end

function Skills:ShouldInvalidate(event)
    return not (self.expandingHeaders and event == "SKILL_LINES_CHANGED")
end

local function WithExpandedSkills(callback, retainExpansion)
    local expanded = {}
    local selected = C_SkillInfo.GetSelectedSkill()
    Skills.expandingHeaders = true
    local ok, result = pcall(function()
        local index = 1
        while index <= C_SkillInfo.GetNumSkillLines() do
            local info = C_SkillInfo.GetSkillLineInfo(index)
            if info and info.isHeader and info.isCollapsed then
                expanded[#expanded + 1] = index
                C_SkillInfo.ExpandSkillHeader(index)
            end
            index = index + 1
        end
        return callback()
    end)
    -- Native expansion fires synchronous events; restore both headers and selection before ending this transaction.
    local restored, restoreError = pcall(function()
        if not (ok and result and retainExpansion) then
            for index = #expanded, 1, -1 do
                C_SkillInfo.CollapseSkillHeader(expanded[index])
            end
            if C_SkillInfo.GetSelectedSkill() ~= selected then
                C_SkillInfo.SetSelectedSkill(selected)
                if EventRegistry then
                    EventRegistry:TriggerEvent("SkillsFrame.NewSkillLineSelected")
                end
            end
        end
    end)
    Skills.expandingHeaders = nil
    if not restored then
        error(restoreError, 0)
    end
    if not ok then
        error(result, 0)
    end
    return result
end

local function OpenSkill(skillID)
    if InCombatLockdown() or Skills:GetAvailability() ~= "ready" then
        return
    end
    if not SkillsFrame and C_AddOns and C_AddOns.LoadAddOn then
        C_AddOns.LoadAddOn("Blizzard_UIPanels_Game")
    end
    if not SkillsFrame or not ToggleCharacter then
        return
    end
    WithExpandedSkills(function()
        for index = 1, C_SkillInfo.GetNumSkillLines() do
            local info = C_SkillInfo.GetSkillLineInfo(index)
            if info and info.skillID == skillID and not info.isHeader then
                ToggleCharacter("SkillsFrame", true)
                C_SkillInfo.SetSelectedSkill(index)
                if CharacterFrame and CharacterFrame.SetRightPaneCollapsed then
                    CharacterFrame:SetRightPaneCollapsed(false)
                end
                if EventRegistry then
                    EventRegistry:TriggerEvent("SkillsFrame.NewSkillLineSelected")
                end
                return true
            end
        end
    end, true)
end

function Skills:Build()
    if C_SkillInfo.GetNumSkillLines() == nil then
        return nil, "pending", "skills"
    end
    return WithExpandedSkills(function()
        local entries = {}
        local category
        for index = 1, C_SkillInfo.GetNumSkillLines() do
            local info = C_SkillInfo.GetSkillLineInfo(index)
            if info and info.isHeader then
                category = info.name
            elseif
                info
                and info.skillID
                and info.name
                and info.name ~= ""
                and info.parentSkillLineID == 0
                and info.skillLineCategoryID ~= CLASS_SKILLS_CATEGORY
            then
                local skillID = info.skillID
                local topic = info.rank .. " / " .. info.maxRank
                if info.modifier and info.modifier ~= 0 then
                    topic = topic .. string.format(" (%+d)", info.modifier)
                end
                entries[#entries + 1] = {
                    kind = "skills",
                    id = skillID,
                    name = info.name,
                    lowerName = lib.Fold(
                        info.name .. " " .. (category or "") .. " " .. (info.description or "") .. " " .. topic
                    ),
                    topic = topic,
                    description = info.description,
                    onClick = function()
                        OpenSkill(skillID)
                    end,
                }
            end
        end
        return entries
    end)
end

lib:RegisterIndexSource("skills", Skills)
