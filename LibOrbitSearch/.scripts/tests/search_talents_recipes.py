"""Exercise native talent and current-profession search through the shipped Lua 5.1 index owner."""

import unittest

from lupa.lua51 import LuaRuntime

import search_engine as engine


COMMON = r"""
function InCombatLockdown() return mock.combat == true end
function GetTime() return mock.now end
SPELL_PASSIVE = "Passive"
RANK = "Rank"
TALENT_BUTTON_TOOLTIP_RANK_FORMAT = "Rank %d/%d"
PROFESSION_RECIPES_SHOW_LEARNED = "Show learned"
PROFESSION_RECIPES_SHOW_UNLEARNED = "Show unlearned"
mock.calls = {trees=0,nodes=0,entries=0,recipes=0,categories=0,opens=0}
mock.spellRequests={}
mock.itemRequests={}
C_Spell.RequestLoadSpellData=function(id) mock.spellRequests[id]=(mock.spellRequests[id] or 0)+1 end
C_Item.RequestLoadItemDataByID=function(id) mock.itemRequests[id]=(mock.itemRequests[id] or 0)+1 end
function NewSearch(kind)
    local search=lib:NewSearch({kinds={{kind=kind,label=kind}}})
    search:Enable()
    return search
end
options={maxResults=100,fuzzy=false,hidePassives=false}
function Query(search,text) return search:Query(text,options) end
"""

TALENTS = r"""
mock.configID=81
mock.group=2
mock.config={ID=81,treeIDs={7}}
mock.nodes={
    [11]={ID=11,isVisible=true,entryIDs={21,22},groupIDs={9},activeEntry={entryID=21,rank=2}},
    [12]={ID=12,isVisible=false,entryIDs={23}},
    [13]={ID=13,isVisible=true,entryIDs={24}},
}
mock.entries={
    [21]={definitionID=31,maxRanks=3,isAvailable=true},
    [22]={definitionID=32,maxRanks=1,isAvailable=false},
    [23]={definitionID=33,maxRanks=1,isAvailable=true},
    [24]={subTreeID=99,maxRanks=1,isAvailable=true},
}
mock.definitions={
    [31]={spellID=101,overrideName="Needle Focus",overrideDescription="Improves weaving precision",
        overrideSubtext="Rank 2",overrideIcon=501},
    [32]={spellID=102},
    [33]={spellID=103,overrideName="Needle Hidden"},
}
mock.spellNames[102]="Needle Choice"
C_Spell.GetSpellDescription=function(id) return "Amplifies threaded damage" end
C_Spell.GetSpellSubtext=function(id) return "Rank 1" end
C_Spell.IsSpellPassive=function(id) return id==101 end
C_ClassTalents={GetActiveConfigID=function() return mock.configID end}
C_Traits={
    GetConfigInfo=function(id) assert(id==mock.configID);return mock.config end,
    GetTreeNodes=function(id) mock.calls.trees=mock.calls.trees+1;assert(id==7);return {11,12,13} end,
    GetNodeInfo=function(configID,id)
        mock.calls.nodes=mock.calls.nodes+1;assert(configID==mock.configID);return mock.nodes[id]
    end,
    GetEntryInfo=function(configID,id) mock.calls.entries=mock.calls.entries+1;return mock.entries[id] end,
    GetDefinitionInfo=function(id) return mock.definitions[id] end,
    GetTreeInfo=function() return {titleText="Needlecraft"} end,
    GetGroupDisplayInfoByTreeID=function() return {{groupID=9,displayName="Weaving"}} end,
    PurchaseRank=function() error("search must never purchase talents") end,
    SetSelection=function() error("search must never select talents") end,
}
PlayerSpellsUtil={OpenToClassTalentsTab=function()
    mock.calls.opens=mock.calls.opens+1
    PlayerSpellsFrame={TalentsFrame={OnPreviewSearchResultClicked=function(_,info) mock.highlight=info.name end}}
end}
"""

RECIPES = r"""
mock.profession={professionID=164,professionName="Blacksmithing",sourceCounter=4}
mock.recipeIDs={201,202,201,203}
mock.recipeInfo={
    [201]={recipeID=201,name="Needle Sword",categoryID=8,learned=true,favorite=true,icon=601,hyperlink="spell:201"},
    [202]={recipeID=202,name="Needle Plate",categoryID=8,learned=false,disabledReason="Requires training"},
    [203]={recipeID=203,name="Needle Placeholder",categoryID=9,isDummyRecipe=true},
}
C_TradeSkillUI={
    GetBaseProfessionInfo=function() return mock.profession end,
    IsDataSourceChanging=function() return mock.changing or false end,
    GetFilteredRecipeIDs=function()
        mock.calls.recipes=mock.calls.recipes+1;return mock.recipeIDs
    end,
    GetRecipeInfo=function(id) return mock.recipeInfo[id] end,
    GetCategoryInfo=function(id) mock.calls.categories=mock.calls.categories+1;return {name="Armaments"} end,
    OpenRecipe=function(id) mock.openedRecipe=id;mock.calls.opens=mock.calls.opens+1 end,
    SetRecipeItemNameFilter=function() error("search must preserve native filters") end,
    SetShowLearned=function() error("search must preserve native filters") end,
    SetShowUnlearned=function() error("search must preserve native filters") end,
    CraftRecipe=function() error("search must never craft") end,
}
"""


def runtime(setup=""):
    lua = LuaRuntime()
    lua.execute(engine.HARNESS + COMMON)
    lua.execute(setup)
    paths = engine.manifest_files()
    extra = [engine.RUNTIME / "Sources" / name for name in ("Talents.lua", "Recipes.lua")]
    for path in paths:
        if path.name == "Finalize.lua":
            for source in extra:
                if source not in paths:
                    lua.eval("LoadSource")(source.read_text(encoding="utf-8"), source.name)
        lua.eval("LoadSource")(path.read_text(encoding="utf-8"), path.name)
    lua.execute('lib=LibStub("LibOrbitSearch-1.0")')
    return lua


class TalentsAndRecipes(unittest.TestCase):
    def test_unsupported_declarations_and_cold_probes_do_not_construct_ui_or_collect(self):
        lua = runtime()
        lua.execute(r"""
            local talents,recipes=NewSearch("talents"),NewSearch("recipes")
            assert(#Query(talents,"needle")==0 and #Query(recipes,"needle")==0)
            assert(lib:GetIndexSourceState("talents")=="unsupported")
            assert(lib:GetIndexSourceState("recipes")=="unsupported")
            assert(mock.calls.trees==0 and mock.calls.recipes==0 and mock.calls.opens==0)
            assert(#mock.errors==0)
        """)
        lua = runtime(TALENTS + RECIPES)
        lua.execute(r"""
            local talents,recipes=NewSearch("talents"),NewSearch("recipes")
            for i=1,10 do lib:GetIndexSourceState("talents");lib:GetIndexSourceState("recipes") end
            assert(mock.calls.trees==0 and mock.calls.recipes==0 and mock.calls.opens==0)
            assert(not PlayerSpellsFrame and not ProfessionsFrame)
        """)

    def test_talent_identity_keywords_hidden_nodes_and_choice_ranks(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            local search=NewSearch("talents")
            assert(#Query(search,"needle")==2)
            local focus=Query(search,"precision")[1]
            assert(focus.id=="7:11:21" and focus.spellID==101 and focus.rank==2 and focus.maxRank==3)
            assert(focus.learned and focus.passive and focus.icon==501 and not focus.secure)
            assert(focus.topic=="Needlecraft · Weaving · Rank 2/3")
            assert(#Query(search,"weaving")==2)
            assert(Query(search,"passive")[1]==focus and Query(search,"rank 2")[1]==focus)
            local choice=Query(search,"threaded")[1]
            assert(choice.id=="7:11:22" and choice.rank==0 and not choice.learned)
            assert(choice.description=="Amplifies threaded damage")
            assert(#Query(search,"hidden")==0 and mock.calls.entries==3)
            assert(mock.calls.trees==1 and #mock.errors==0)
            options.hidePassives=true
            assert(#Query(search,"needle")==1)
        """)

    def test_forever_uses_the_active_spec_group_not_retail_config_or_player_specialization(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            C_ClassTalents.GetActiveConfigID=function() error("wrong Forever config path") end
            C_SpecializationInfo={
                GetActiveSpecGroup=function() return mock.group end,
                GetCombatConfigIDForSpecGroup=function(group)
                    assert(group==2);return mock.configID
                end,
                GetSpecialization=function() error("Forever has no player specialization") end,
            }
            local search=NewSearch("talents")
            local row=Query(search,"precision")[1]
            assert(row.configID==81 and row.id=="7:11:21")
            PlayerSpellsUtil.OpenToClassTalentsTab=function()
                mock.calls.opens=mock.calls.opens+1
                PlayerSpellsFrame={TalentsFrame={
                    GetActiveTab=function() return 2 end,
                    SetTab=function(_,tab) mock.viewedTab=tab end,
                    OnPreviewSearchResultClicked=function(_,info)
                        assert(mock.viewedTab==2);mock.highlight=info.name
                    end,
                }}
            end
            row.onClick(row);assert(mock.highlight=="Needle Focus" and mock.calls.opens==1)
        """)

    def test_talent_late_config_event_refresh_and_disabled_mutations(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            mock.configID=nil
            local search=NewSearch("talents");search:SetOpen(true)
            assert(#Query(search,"needle")==0 and lib:GetIndexSourceState("talents")=="pending")
            assert(lib._eventFrame.events.PLAYER_TALENT_UPDATE)
            mock.configID=81;FireEvent("PLAYER_TALENT_UPDATE");FlushTimers()
            local row=Query(search,"precision")[1]
            assert(row and mock.calls.trees==1)
            for i=1,15 do Query(search,"needle") end
            assert(mock.calls.trees==1)
            mock.nodes[11].activeEntry.rank=3
            for i=1,15 do FireEvent("TRAIT_NODE_CHANGED",11) end
            assert(not search:IsEntryCurrent(row));FlushTimers()
            assert(Query(search,"precision")[1].rank==3 and mock.calls.trees==2)
            search:Disable()
            assert(not lib._eventFrame.events.TRAIT_NODE_CHANGED)
            mock.nodes[11].activeEntry.rank=1
            search:Enable()
            assert(Query(search,"precision")[1].rank==1 and mock.calls.trees==3)
        """)

    def test_talent_navigation_never_allocates_and_obeys_combat_and_config(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            local search=NewSearch("talents")
            local row=Query(search,"precision")[1]
            assert(mock.calls.opens==0)
            mock.combat=true;row.onClick(row);assert(mock.calls.opens==0)
            mock.combat=false;mock.configID=82;row.onClick(row);assert(mock.calls.opens==0)
            mock.configID=81;row.onClick(row)
            assert(mock.calls.opens==1 and mock.highlight==row.name)
            PlayerSpellsUtil=nil;row.onClick(row);assert(mock.calls.opens==1)
            assert(#mock.errors==0)
        """)

    def test_talent_missing_tree_waits_and_recovers_without_publishing_partial_results(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            local treeGetter=C_Traits.GetTreeNodes
            C_Traits.GetTreeNodes=function() return nil end
            local search=NewSearch("talents")
            assert(#Query(search,"needle")==0 and lib:GetIndexSourceState("talents")=="pending")
            C_Traits.GetTreeNodes=treeGetter;FireEvent("TRAIT_TREE_CHANGED",7)
            assert(#Query(search,"needle")==2 and #mock.errors==0)
        """)

    def test_recipes_preserve_filtered_context_and_native_metadata(self):
        lua = runtime(RECIPES)
        lua.execute(r"""
            local search=NewSearch("recipes")
            assert(#Query(search,"needle")==2)
            local row=Query(search,"sword")[1]
            assert(row.id==201 and row.recipeID==201 and row.professionID==164 and row.sourceCounter==4)
            assert(row.favorite and row.learned and row.tooltipLink=="spell:201" and not row.secure)
            assert(not row.spellID and row.topic=="Blacksmithing · Armaments · Show learned")
            assert(#Query(search,"blacksmithing")==2 and #Query(search,"armaments")==2)
            assert(Query(search,"unlearned")[1].recipeID==202)
            assert(mock.calls.categories==1 and mock.calls.recipes==1 and mock.calls.opens==0)
            for i=1,10 do Query(search,"needle") end
            assert(mock.calls.recipes==1)
            mock.recipeIDs={201};FireEvent("TRADE_SKILL_LIST_UPDATE")
            assert(not search:IsEntryCurrent(row) and #Query(search,"needle")==1)
            assert(mock.calls.recipes==2 and #mock.errors==0)
        """)

    def test_recipe_pending_context_transition_close_and_recovery(self):
        lua = runtime(RECIPES)
        lua.execute(r"""
            local profession=mock.profession;mock.profession=nil
            local search=NewSearch("recipes");search:SetOpen(true)
            assert(#Query(search,"needle")==0 and mock.calls.recipes==0)
            assert(lib:GetIndexSourceState("recipes")=="pending")
            mock.profession=profession;FireEvent("TRADE_SKILL_SHOW");FlushTimers()
            local row=Query(search,"sword")[1]
            mock.changing=true;FireEvent("TRADE_SKILL_DATA_SOURCE_CHANGING")
            assert(not search:IsEntryCurrent(row) and #Query(search,"needle")==0)
            mock.changing=false;mock.profession={professionID=165,professionName="Leatherworking",sourceCounter=5}
            mock.recipeIDs={202};FireEvent("TRADE_SKILL_DATA_SOURCE_CHANGED");FlushTimers()
            local replacement=Query(search,"leatherworking")[1]
            assert(replacement.recipeID==202 and replacement.professionID==165)
            mock.profession=nil;FireEvent("TRADE_SKILL_CLOSE")
            assert(not search:IsEntryCurrent(replacement) and #Query(search,"needle")==0)
            assert(#mock.errors==0)
        """)

    def test_recipe_click_only_opens_current_context_and_never_crafts(self):
        lua = runtime(RECIPES)
        lua.execute(r"""
            local search=NewSearch("recipes")
            local row=Query(search,"sword")[1]
            mock.combat=true;row.onClick(row);assert(mock.calls.opens==0)
            mock.combat=false;mock.profession.sourceCounter=5;row.onClick(row)
            assert(mock.calls.opens==0)
            mock.profession.sourceCounter=4;mock.changing=true;row.onClick(row)
            assert(mock.calls.opens==0)
            mock.changing=false;row.onClick(row)
            assert(mock.openedRecipe==201 and mock.calls.opens==1)
            C_TradeSkillUI.OpenRecipe=nil;row.onClick(row);assert(mock.calls.opens==1)
        """)

    def test_recipe_event_burst_is_debounced_and_disable_drops_observation(self):
        lua = runtime(RECIPES)
        lua.execute(r"""
            local search=NewSearch("recipes");search:SetOpen(true)
            Query(search,"needle")
            for i=1,20 do FireEvent("TRADE_SKILL_LIST_UPDATE") end
            assert(mock.calls.recipes==1);FlushTimers();assert(mock.calls.recipes==2)
            search:Disable();assert(not lib._eventFrame.events.TRADE_SKILL_LIST_UPDATE)
            mock.recipeIDs={202};FireEvent("TRADE_SKILL_LIST_UPDATE");FlushTimers()
            assert(mock.calls.recipes==2)
            search:Enable()
            assert(#Query(search,"needle")==1 and mock.calls.recipes==3)
        """)

    def test_talent_async_name_and_description_recover_without_request_loops(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            mock.spellNames[102]=nil
            local search=NewSearch("talents")
            assert(#Query(search,"needle")==1 and mock.spellRequests[102]==1)
            local builds=mock.calls.trees
            FireEvent("SPELL_TEXT_UPDATE",999);FireEvent("SPELL_DATA_LOAD_RESULT",999,true)
            assert(#Query(search,"needle")==1 and mock.calls.trees==builds)
            FireEvent("SPELL_DATA_LOAD_RESULT",102,false)
            assert(#Query(search,"needle")==1 and mock.spellRequests[102]==1 and mock.calls.trees==builds)
            mock.spellNames[102]="Needle Choice"
            C_Spell.GetSpellDescription=function() return "" end
            FireEvent("SPELL_DATA_LOAD_RESULT",102,true)
            local row=Query(search,"choice")[1]
            assert(row and row.description=="" and mock.spellRequests[102]==1)
            C_Spell.GetSpellDescription=function() return "Restores threaded healing" end
            FireEvent("SPELL_TEXT_UPDATE",102)
            assert(Query(search,"healing")[1].id=="7:11:22")
            assert(Talents==nil and lib._indexSources.talents.spellRequests.count==1)
            assert(#mock.errors==0)
        """)

    def test_talent_localized_state_terms_and_topics_are_consumer_owned(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            lib._sourceKeywordTerms={talents={learned="appris",unlearned="inconnu"}}
            local search=NewSearch("talents")
            assert(Query(search,"appris")[1].id=="7:11:21")
            assert(Query(search,"inconnu")[1].id=="7:11:22")
            assert(Query(search,"appris")[1].topic=="Needlecraft · Weaving · Rank 2/3 · appris")
            lib._sourceKeywordTerms={talents={unlearned="inconnu"}}
            lib:MarkDirty("talents")
            assert(#Query(search,"inconnu")==1 and #mock.errors==0)
        """)

    def test_talent_cold_empty_spell_data_is_pending_and_success_recovers(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            mock.definitions[31].overrideName=nil;mock.spellNames[102]=nil
            local search=NewSearch("talents")
            assert(#Query(search,"needle")==0 and lib:GetIndexSourceState("talents")=="pending")
            assert(mock.spellRequests[101]==1 and mock.spellRequests[102]==1)
            mock.spellNames[101]="Needle Focus"
            FireEvent("SPELL_DATA_LOAD_RESULT",101,true)
            assert(Query(search,"focus")[1] and lib:GetIndexSourceState("talents")=="ready")
            search:Disable()
            local calls=mock.calls.trees
            FireEvent("SPELL_DATA_LOAD_RESULT",102,true)
            assert(mock.calls.trees==calls and not lib._eventFrame.events.SPELL_DATA_LOAD_RESULT)
        """)

    def test_talent_failed_and_lost_pending_requests_retry_only_on_a_later_query(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            mock.now=0
            mock.definitions[31].overrideName=nil;mock.spellNames[102]=nil
            local search=NewSearch("talents")
            assert(#Query(search,"needle")==0 and lib:GetIndexSourceState("talents")=="pending")
            assert(mock.spellRequests[101]==1 and mock.spellRequests[102]==1)
            FireEvent("SPELL_DATA_LOAD_RESULT",101,false)
            local source=lib._indexSources.talents
            assert(source.nextRetry==30 and not source:IsExpired())
            mock.now=29
            for i=1,10 do Query(search,"needle") end
            assert(mock.calls.trees==1 and mock.spellRequests[101]==1 and mock.spellRequests[102]==1)
            mock.now=30
            for i=1,10 do assert(source:IsExpired()) end
            assert(mock.calls.trees==1 and mock.spellRequests[101]==1 and #mock.timers==0)
            Query(search,"needle")
            assert(mock.calls.trees==2 and mock.spellRequests[101]==2 and mock.spellRequests[102]==2)
            for i=1,10 do Query(search,"needle") end
            assert(mock.calls.trees==2 and source.nextRetry==60)
            mock.spellNames[101]="Needle Focus";mock.spellNames[102]="Needle Choice"
            FireEvent("SPELL_DATA_LOAD_RESULT",101,true)
            assert(#Query(search,"needle")==2 and source.nextRetry==nil)
            local builds=mock.calls.trees
            mock.now=120
            for i=1,10 do Query(search,"needle") end
            assert(mock.calls.trees==builds and mock.spellRequests[101]==2 and mock.spellRequests[102]==2)
            assert(not source:IsExpired() and #mock.errors==0)
        """)

    def test_talent_partial_description_retry_survives_disable_and_real_trait_events(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            mock.now=0
            C_Spell.GetSpellDescription=function() return "" end
            local search=NewSearch("talents")
            local row=Query(search,"choice")[1]
            assert(row and row.description=="" and lib:GetIndexSourceState("talents")=="ready")
            assert(mock.spellRequests[102]==1)
            FireEvent("SPELL_DATA_LOAD_RESULT",102,false)
            mock.now=10;FireEvent("TRAIT_NODE_CHANGED",11);Query(search,"choice")
            assert(mock.spellRequests[102]==1)
            search:Disable()
            assert(not lib._eventFrame.events.SPELL_DATA_LOAD_RESULT)
            mock.now=20;search:Enable();Query(search,"choice")
            assert(mock.spellRequests[102]==1)
            mock.now=30
            local builds=mock.calls.trees
            Query(search,"choice")
            assert(mock.calls.trees==builds+1 and mock.spellRequests[102]==2)
            for i=1,10 do Query(search,"choice") end
            assert(mock.calls.trees==builds+1 and mock.spellRequests[102]==2)
            search:Disable();mock.now=60;search:Enable();Query(search,"choice")
            assert(mock.spellRequests[102]==3)
            C_Spell.GetSpellDescription=function() return "Restores threaded healing" end
            FireEvent("SPELL_TEXT_UPDATE",102)
            assert(Query(search,"healing")[1].id=="7:11:22")
            assert(lib._indexSources.talents.nextRetry==nil)
            builds=mock.calls.trees;mock.now=120;Query(search,"healing")
            assert(mock.calls.trees==builds and mock.spellRequests[102]==3 and #mock.errors==0)
        """)

    def test_talent_sweep_delays_new_missing_fields_until_retry_and_ignores_absent_request_api(self):
        lua = runtime(TALENTS)
        lua.execute(r"""
            mock.now=0;mock.spellNames[102]=nil
            local search=NewSearch("talents")
            Query(search,"needle")
            local source=lib._indexSources.talents
            assert(source.nextRetry==30 and mock.spellRequests[102]==1)
            mock.now=10;mock.definitions[31].overrideDescription=nil
            C_Spell.GetSpellDescription=function() return "" end
            FireEvent("TRAIT_NODE_CHANGED",11);Query(search,"needle")
            assert(mock.spellRequests[101]==nil and source.nextRetry==30)
            mock.now=30;Query(search,"needle")
            assert(mock.spellRequests[101]==1 and mock.spellRequests[102]==2 and source.nextRetry==60)
            C_Spell.RequestLoadSpellData=nil
            FireEvent("TRAIT_NODE_CHANGED",11);Query(search,"needle")
            assert(source.nextRetry==nil)
            local builds=mock.calls.trees;mock.now=120;Query(search,"needle")
            assert(mock.calls.trees==builds and #mock.errors==0)
        """)

    def test_recipe_schematic_output_reagent_and_currency_terms(self):
        lua = runtime(RECIPES)
        lua.execute(r"""
            mock.itemNames[301]="Tempered Blade";mock.itemNames[302]="Copper Bar"
            C_CurrencyInfo={GetCurrencyInfo=function(id) assert(id==401);return {name="Artisan Mettle"} end}
            C_TradeSkillUI.GetRecipeSchematic=function(id,isRecraft)
                assert(not isRecraft)
                return {outputItemID=301,reagentSlotSchematics={
                    {reagents={{itemID=302},{currencyID=401}}}
                }}
            end
            local search=NewSearch("recipes")
            assert(#Query(search,"tempered")==2 and #Query(search,"copper")==2 and #Query(search,"mettle")==2)
            assert(next(mock.itemRequests)==nil and mock.calls.recipes==1)
            C_TradeSkillUI.GetRecipeSchematic=nil;FireEvent("TRADE_SKILL_LIST_UPDATE")
            assert(#Query(search,"needle")==2 and #Query(search,"copper")==0 and #mock.errors==0)
        """)

    def test_recipe_item_receipts_filter_completion_and_retire_on_disable(self):
        lua = runtime(RECIPES)
        lua.execute(r"""
            C_TradeSkillUI.GetRecipeSchematic=function()
                return {outputItemID=301,reagentSlotSchematics={{reagents={{itemID=302}}}}}
            end
            local search=NewSearch("recipes");search:SetOpen(true)
            assert(#Query(search,"needle")==2)
            assert(mock.itemRequests[301]==1 and mock.itemRequests[302]==1)
            FireEvent("GET_ITEM_INFO_RECEIVED",999,true);FlushTimers()
            assert(mock.calls.recipes==1)
            mock.itemNames[301]="Tempered Blade";mock.itemNames[302]="Copper Bar"
            FireEvent("GET_ITEM_INFO_RECEIVED",301,true);FlushTimers()
            assert(#Query(search,"copper")==2 and mock.calls.recipes==2)
            assert(not lib._sourceItemPending.recipes)
            mock.itemNames[302]=nil;FireEvent("TRADE_SKILL_LIST_UPDATE");FlushTimers()
            assert(lib._sourceItemPending.recipes)
            search:Disable()
            assert(not lib._sourceItemPending.recipes)
            local calls=mock.calls.recipes
            FireEvent("GET_ITEM_INFO_RECEIVED",302,true);FlushTimers()
            assert(mock.calls.recipes==calls and #mock.errors==0)
        """)

    def test_synchronous_recipe_item_receipt_rejects_incomplete_build(self):
        lua = runtime(RECIPES)
        lua.execute(r"""
            C_TradeSkillUI.GetRecipeSchematic=function()
                return {outputItemID=301,reagentSlotSchematics={}}
            end
            C_Item.RequestLoadItemDataByID=function(id)
                mock.itemNames[id]="Tempered Blade"
                FireEvent("GET_ITEM_INFO_RECEIVED",id,true)
            end
            local search=NewSearch("recipes")
            Query(search,"needle")
            assert(not lib._sourceItemPending.recipes)
            assert(#Query(search,"tempered")==2 and #mock.errors==0)
        """)


if __name__ == "__main__":
    unittest.main()
