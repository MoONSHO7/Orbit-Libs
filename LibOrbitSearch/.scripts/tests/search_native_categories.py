"""Execute native skill, reputation, equipment-set and outfit search contracts in Lua 5.1."""

import unittest

from lupa.lua51 import LuaRuntime

import search_engine as engine


SOURCE_NAMES = ("Skills.lua", "EquipmentSets.lua", "Outfits.lua", "Reputation.lua")


def runtime():
    lua = LuaRuntime()
    lua.execute(engine.HARNESS)
    for path in engine.manifest_files():
        if path.parent.name == "Sources":
            continue
        if path.name == "Finalize.lua":
            for name in SOURCE_NAMES:
                source = engine.RUNTIME / "Sources" / name
                lua.eval("LoadSource")(source.read_text(encoding="utf-8"), name)
        lua.eval("LoadSource")(path.read_text(encoding="utf-8"), path.name)
    lua.execute("""
        lib = LibStub("LibOrbitSearch-1.0")
        options = {maxResults=100, fuzzy=false, hidePassives=false}
        function Search(kind)
            local search=lib:NewSearch({kinds={{kind=kind,label=kind}}})
            search:Enable()
            return search
        end
        function InCombatLockdown() return mock.combat == true end
        function ToggleCharacter(panel, onlyShow)
            assert(onlyShow == true)
            mock.openedPanel=panel
        end
        CharacterFrame = {SetRightPaneCollapsed=function(_,collapsed) mock.paneCollapsed=collapsed end}
        EventRegistry = {TriggerEvent=function(_,event) mock.selectedEvent=event end}
        function MakeList(kind)
            local state={selected=2, calls=0}
            local isSkills = kind == "skills"
            local idKey=isSkills and "skillID" or "factionID"
            local header={name="Native Category", isHeader=true, isCollapsed=true, [idKey]=500}
            local child={name="Needle", description="Localized description", [idKey]=43,
                rank=75, maxRank=300, modifier=5, parentSkillLineID=0, skillLineCategoryID=6,
                reaction=5,currentReactionThreshold=3000,nextReactionThreshold=9000,currentStanding=3500}
            local other={name="Other", description="", [idKey]=55, rank=10, maxRank=50,
                parentSkillLineID=0, skillLineCategoryID=6, reaction=4}
            state.header, state.child, state.other=header,child,other
            local function Rows()
                if state.header.isCollapsed then return {state.header,state.other} end
                if state.removed then return {state.header,state.other} end
                return {state.header,state.child,state.other}
            end
            local function Get(index)
                state.calls=state.calls+1
                if state.failRead and not state.header.isCollapsed and index==2 then error("native read failed") end
                return Rows()[index]
            end
            local event=isSkills and "SKILL_LINES_CHANGED" or "UPDATE_FACTION"
            local function Expand(index)
                assert(index==1)
                state.header.isCollapsed=false
                state.selected=1
                FireEvent(event)
            end
            local function Collapse(index)
                assert(index==1)
                state.header.isCollapsed=true
                FireEvent(event)
            end
            local function Select(index) state.selected=index end
            local function Count() return #Rows() end
            local function Selected() return state.selected end
            if isSkills then
                C_SkillInfo={GetNumSkillLines=Count, GetSkillLineInfo=Get, ExpandSkillHeader=Expand,
                    CollapseSkillHeader=Collapse, GetSelectedSkill=Selected, SetSelectedSkill=Select}
                SkillsFrame={}
            else
                C_Reputation={GetNumFactions=Count, GetFactionDataByIndex=Get, ExpandFactionHeader=Expand,
                    CollapseFactionHeader=Collapse, GetSelectedFaction=Selected, SetSelectedFaction=Select,
                    IsMajorFaction=function() return false end}
                C_GossipInfo={GetFriendshipReputation=function() return {friendshipFactionID=0} end}
                MAX_REPUTATION_REACTION=8
                REPUTATION_PROGRESS_FORMAT="%s / %s"
                BreakUpLargeNumbers=tostring
                ReputationFrame={}
                function UnitSex() return 2 end
                function GetText(key, sex) assert(sex==2); return key=="FACTION_STANDING_LABEL5" and "Honored" or "Neutral" end
            end
            return state
        end
    """)
    return lua


class NativeCategories(unittest.TestCase):
    def test_missing_native_contracts_are_local_and_recover(self):
        lua = runtime()
        lua.execute("""
            for _,kind in ipairs({"skills","equipmentsets","outfits","reputation"}) do
                local search=Search(kind)
                assert(#search:Query("needle",options)==0)
                assert(lib:GetIndexSourceState(kind)=="unsupported",kind)
                search:Disable()
            end
            local search=Search("skills")
            local state=MakeList("skills")
            FireEvent("ADDON_LOADED")
            assert(search:Query("needle",options)[1].id==43)
            assert(#mock.errors==0)
        """)

    def test_header_transactions_preserve_selection_and_other_consumers(self):
        for kind, event in (("skills", "SKILL_LINES_CHANGED"), ("reputation", "UPDATE_FACTION")):
            with self.subTest(kind=kind):
                lua = runtime()
                lua.globals().kind = kind
                lua.globals().nativeEvent = event
                lua.execute("""
                    local state=MakeList(kind)
                    lib:RegisterIndexSource("witness",{events={nativeEvent},Build=function()
                        return {{kind="witness",id=1,name="witness",lowerName="witness"}}
                    end})
                    local witness=Search("witness")
                    local prior=witness:Query("witness",options)[1]
                    local search=Search(kind)
                    local entry=search:Query("needle",options)[1]
                    assert(entry and entry.id==43)
                    assert(search:IsEntryCurrent(entry))
                    assert(not witness:IsEntryCurrent(prior))
                    assert(state.header.isCollapsed and state.selected==2)
                    assert(not lib._indexSources[kind].expandingHeaders)
                    local calls=state.calls
                    assert(search:Query("needle",options)[1]==entry and state.calls==calls)
                    FireEvent(nativeEvent)
                    assert(not search:IsEntryCurrent(entry))
                    assert(search:Query("needle",options)[1].id==43)
                    assert(#mock.errors==0)
                """)

    def test_navigation_resolves_current_identity_and_rejects_missing_or_combat(self):
        for kind in ("skills", "reputation"):
            with self.subTest(kind=kind):
                lua = runtime()
                lua.globals().kind = kind
                lua.execute("""
                    local state=MakeList(kind)
                    local search=Search(kind)
                    local entry=search:Query("needle",options)[1]
                    mock.combat=true;entry.onClick()
                    assert(not mock.openedPanel and state.header.isCollapsed)
                    mock.combat=false;state.removed=true;entry.onClick()
                    assert(not mock.openedPanel and state.header.isCollapsed and state.selected==2)
                    state.removed=false;entry.onClick()
                    assert(mock.openedPanel==(kind=="skills" and "SkillsFrame" or "ReputationFrame"))
                    assert(not state.header.isCollapsed and state.selected==2 and mock.paneCollapsed==false)
                    local selected=(kind=="skills" and C_SkillInfo.GetSkillLineInfo(2) or C_Reputation.GetFactionDataByIndex(2))
                    assert(selected.name=="Needle")
                    assert(#mock.errors==0)
                """)

    def test_mixed_query_keeps_other_skill_event_sources_current(self):
        lua = runtime()
        lua.execute("""
            local state=MakeList("skills")
            for _,kind in ipairs({"spellbook","professions"}) do
                local sourceKind=kind
                lib:RegisterIndexSource(sourceKind,{events={"SKILL_LINES_CHANGED"},Build=function()
                    return {{kind=sourceKind,id=1,name="Needle",lowerName="needle"}}
                end})
            end
            local search=lib:NewSearch({kinds={
                {kind="spellbook",label="spellbook"},
                {kind="professions",label="professions"},
                {kind="skills",label="skills"},
            }})
            search:Enable()
            local entries=search:Query("needle",options)
            assert(#entries==3, "all demanded sources must survive a synchronous header event")
            for _,entry in ipairs(entries) do assert(search:IsEntryCurrent(entry),entry.kind) end
            assert(state.header.isCollapsed and state.selected==2)
            assert(#mock.errors==0)
        """)

    def test_failed_native_read_restores_transaction_before_reporting(self):
        for kind in ("skills", "reputation"):
            with self.subTest(kind=kind):
                lua = runtime()
                lua.globals().kind = kind
                lua.execute("""
                    local state=MakeList(kind)
                    state.failRead=true
                    local search=Search(kind)
                    assert(#search:Query("needle",options)==0)
                    assert(state.header.isCollapsed and state.selected==2)
                    assert(not lib._indexSources[kind].expandingHeaders and #mock.errors==1)
                    state.failRead=false
                    FireEvent(kind=="skills" and "SKILL_LINES_CHANGED" or "UPDATE_FACTION")
                    assert(search:Query("needle",options)[1].id==43)
                """)

    def test_restore_callback_failure_clears_event_suppression(self):
        for kind in ("skills", "reputation"):
            with self.subTest(kind=kind):
                lua = runtime()
                lua.globals().kind = kind
                lua.execute("""
                    local state=MakeList(kind)
                    EventRegistry.TriggerEvent=function() error("native selection callback failed") end
                    local search=Search(kind)
                    assert(#search:Query("needle",options)==0)
                    assert(state.header.isCollapsed and state.selected==2)
                    assert(not lib._indexSources[kind].expandingHeaders and #mock.errors==1)
                    EventRegistry.TriggerEvent=function() end
                    FireEvent(kind=="skills" and "SKILL_LINES_CHANGED" or "UPDATE_FACTION")
                    assert(search:Query("needle",options)[1].id==43)
                """)

    def test_native_panels_are_loaded_only_on_explicit_navigation(self):
        for kind in ("skills", "reputation"):
            with self.subTest(kind=kind):
                lua = runtime()
                lua.globals().kind = kind
                lua.execute("""
                    local state=MakeList(kind)
                    SkillsFrame,ReputationFrame=nil,nil
                    C_AddOns={LoadAddOn=function(name)
                        mock.loadedAddon=name
                        SkillsFrame,ReputationFrame={},{}
                        return true
                    end}
                    local search=Search(kind)
                    local entry=search:Query("needle",options)[1]
                    assert(not mock.loadedAddon)
                    entry.onClick()
                    assert(mock.loadedAddon=="Blizzard_UIPanels_Game")
                    assert(mock.openedPanel and state.selected==2 and #mock.errors==0)
                """)

    def test_skill_details_and_retail_capability_isolation(self):
        lua = runtime()
        lua.execute("""
            local state=MakeList("skills")
            local search=Search("skills")
            local entry=search:Query("description",options)[1]
            assert(entry.id==43 and entry.topic=="75 / 300 (+5)" and entry.icon==nil)
            state.child.skillLineCategoryID=7
            FireEvent("SKILL_LINES_CHANGED")
            assert(#search:Query("needle",options)==0)
            C_SkillInfo={}
            FireEvent("PLAYER_ENTERING_WORLD")
            assert(lib:GetIndexSourceState("skills")=="unsupported")
            assert(not lib._eventFrame.events.SKILL_LINES_CHANGED)
            assert(#mock.errors==0)
        """)

    def test_nested_duplicate_headers_restore_in_reverse(self):
        lua = runtime()
        lua.execute("""
            local top={skillID=501,name="Same",isHeader=true,isCollapsed=true}
            local inner={skillID=502,name="Same",isHeader=true,isCollapsed=true}
            local target={skillID=43,name="Needle",rank=75,maxRank=300,parentSkillLineID=0,skillLineCategoryID=6}
            local other={skillID=55,name="Other",rank=10,maxRank=50,parentSkillLineID=0,skillLineCategoryID=6}
            local selected=2
            local order={}
            local function Rows()
                if top.isCollapsed then return {top,other} end
                if inner.isCollapsed then return {top,inner,other} end
                return {top,inner,target,other}
            end
            C_SkillInfo={
                GetNumSkillLines=function() return #Rows() end,
                GetSkillLineInfo=function(index) return Rows()[index] end,
                GetSelectedSkill=function() return selected end,
                SetSelectedSkill=function(index) selected=index end,
                ExpandSkillHeader=function(index)
                    local row=Rows()[index]
                    assert(row.isHeader)
                    row.isCollapsed=false
                    selected=1
                    FireEvent("SKILL_LINES_CHANGED")
                end,
                CollapseSkillHeader=function(index)
                    local row=Rows()[index]
                    assert(row.isHeader)
                    order[#order+1]=row.skillID
                    row.isCollapsed=true
                    FireEvent("SKILL_LINES_CHANGED")
                end,
            }
            local search=Search("skills")
            local entry=search:Query("needle",options)[1]
            assert(entry.id==43 and search:IsEntryCurrent(entry))
            assert(top.isCollapsed and inner.isCollapsed and selected==2)
            assert(order[1]==502 and order[2]==501)
            search:Disable()
            assert(next(lib._eventFrame.events)==nil and #mock.errors==0)
        """)

    def test_reputation_searches_native_standing_and_description_without_policy_mutation(self):
        lua = runtime()
        lua.execute("""
            local state=MakeList("reputation")
            C_Reputation.ToggleFactionAtWar=function() error("must not set war") end
            C_Reputation.SetFactionActive=function() error("must not set inactive") end
            local search=Search("reputation")
            local entry=search:Query("honored",options)[1]
            assert(entry.id==43 and entry.topic=="Honored · 500 / 6000" and entry.description=="Localized description")
            assert(entry.icon==nil and not entry.secure)
            assert(search:Query("description",options)[1]==entry)
            entry.onClick()
            assert(#mock.errors==0)
        """)

    def test_reputation_omits_standard_progress_for_friendship_renown_or_unknown_type(self):
        lua = runtime()
        lua.execute("""
            local state=MakeList("reputation")
            local search=Search("reputation")
            C_GossipInfo.GetFriendshipReputation=function() return {friendshipFactionID=22,reaction="Trusted"} end
            local entry=search:Query("needle",options)[1]
            assert(entry.topic=="Trusted")
            C_GossipInfo.GetFriendshipReputation=function() return {friendshipFactionID=0} end
            C_Reputation.IsMajorFaction=function() return true end
            FireEvent("UPDATE_FACTION")
            assert(search:Query("needle",options)[1].topic==nil)
            C_Reputation.IsMajorFaction=nil
            FireEvent("UPDATE_FACTION")
            assert(search:Query("needle",options)[1].topic==nil)
            assert(#mock.errors==0)
        """)

    def test_equipment_sets_keep_stable_ids_and_native_name_action(self):
        lua = runtime()
        lua.execute("""
            local name="Needle";local ids={42}
            C_EquipmentSet={
                GetEquipmentSetIDs=function() return ids end,
                GetEquipmentSetInfo=function(id) return name,99,id,true,10,8 end,
                GetEquipmentSetID=function(setName) assert(setName==name);return 42 end,
                UseEquipmentSet=function() error("build must not equip") end,
            }
            local search=Search("equipmentsets")
            local entry=search:Query("needle",options)[1]
            assert(entry.id==42 and entry.icon==99 and entry.topic=="8 / 10")
            assert(entry.secure.type=="equipmentset" and entry.secure.equipmentset=="Needle")
            name="Renamed";FireEvent("EQUIPMENT_SETS_CHANGED")
            assert(not search:IsEntryCurrent(entry))
            entry=search:Query("renamed",options)[1]
            assert(entry.id==42 and entry.secure.equipmentset=="Renamed")
            C_EquipmentSet.UseEquipmentSet=nil
            FireEvent("ADDON_LOADED")
            assert(not search:Query("renamed",options)[1].secure)
            ids=nil;FireEvent("EQUIPMENT_SETS_CHANGED")
            assert(#search:Query("renamed",options)==0)
            assert(lib:GetIndexSourceState("equipmentsets")=="pending")
            ids={};FireEvent("EQUIPMENT_SETS_CHANGED")
            assert(#search:Query("renamed",options)==0)
            assert(lib:GetIndexSourceState("equipmentsets")=="ready" and #mock.errors==0)
        """)

    def test_outfits_use_player_index_and_retire_on_unlock_and_index_changes(self):
        lua = runtime()
        lua.execute("""
            local enabled=false
            local info={outfitID=901,name="Needle",icon=55,playerFacingOutfitIndex=3,
                situationCategories={"Localized Situation"},isDisabled=false}
            C_TransmogOutfitInfo={
                IsTransmogEnabled=function() return enabled end,
                GetOutfitsInfo=function() return {info} end,
                ChangeToOutfit=function() error("build must not equip") end,
            }
            local search=Search("outfits")
            assert(#search:Query("needle",options)==0 and lib:GetIndexSourceState("outfits")=="pending")
            assert(lib._eventFrame.events.TRANSMOG_OUTFITS_CHANGED)
            enabled=true;FireEvent("TRANSMOG_OUTFITS_CHANGED")
            local entry=search:Query("situation",options)[1]
            assert(entry.id==901 and entry.secure["outfit-index"]==3 and entry.secure.action=="change")
            info.playerFacingOutfitIndex=8;FireEvent("TRANSMOG_OUTFITS_CHANGED")
            assert(not search:IsEntryCurrent(entry))
            entry=search:Query("needle",options)[1]
            assert(entry.id==901 and entry.secure["outfit-index"]==8)
            info.playerFacingOutfitIndex=0;FireEvent("TRANSMOG_OUTFITS_CHANGED")
            assert(search:Query("needle",options)[1].secure["outfit-index"]==0)
            info.isDisabled=true;FireEvent("TRANSMOG_OUTFITS_CHANGED")
            assert(not search:Query("needle",options)[1].secure)
            enabled=false;FireEvent("TRANSMOG_OUTFITS_CHANGED")
            assert(#search:Query("needle",options)==0)
            search:Disable()
            assert(next(lib._eventFrame.events)==nil and #mock.errors==0)
        """)


if __name__ == "__main__":
    unittest.main()
