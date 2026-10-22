"""Stress native index identities, event payloads and rebuild costs in shipped Lua 5.1."""

import unittest

from client_contracts import runtime
import search_talents_recipes as talents


PETS = r"""
mock.petIDs={"Pet-A","Pet-B"}
mock.petReads=0
mock.petLists=0
mock.pets={
    ["Pet-A"]={species=1,nickname="Fluffy",name="Rabbit",favorite=true,summonable=true},
    ["Pet-B"]={species=1,nickname="Cotton",name="Rabbit",favorite=false,summonable=true},
}
C_PetJournal={
    GetOwnedPetIDs=function() mock.petLists=mock.petLists+1;return mock.petIDs end,
    GetPetInfoByPetID=function(id)
        mock.petReads=mock.petReads+1
        local pet=mock.pets[id]
        return pet.species,pet.nickname,nil,nil,nil,nil,pet.favorite,pet.name,123,8,
            nil,nil,nil,nil,false
    end,
    PetIsSummonable=function(id) return mock.pets[id].summonable end,
    SummonPetByGUID=function() end,
}
"""


class NativeSourceAudit(unittest.TestCase):
    def test_flat_skill_and_reputation_indexes_enumerate_linearly_and_stay_warm(self):
        for kind in ("skills", "reputation"):
            with self.subTest(kind=kind):
                lua = runtime(True)
                lua.globals().auditKind = kind
                lua.execute(r"""
                    local count=500
                    local reads=0
                    local function Count() return count end
                    local function Read(index)
                        reads=reads+1
                        return {skillID=index,factionID=index,name="Needle "..index,description="",
                            rank=50,maxRank=100,modifier=0,parentSkillLineID=0,skillLineCategoryID=6}
                    end
                    local function UnexpectedMutation() error("flat lists cannot require header mutations") end
                    local function Selected() return 1 end
                    if auditKind=="skills" then
                        C_SkillInfo={GetNumSkillLines=Count,GetSkillLineInfo=Read,
                            ExpandSkillHeader=UnexpectedMutation,CollapseSkillHeader=UnexpectedMutation,
                            GetSelectedSkill=Selected,SetSelectedSkill=UnexpectedMutation}
                    else
                        C_Reputation={GetNumFactions=Count,GetFactionDataByIndex=Read,
                            ExpandFactionHeader=UnexpectedMutation,CollapseFactionHeader=UnexpectedMutation,
                            GetSelectedFaction=Selected,SetSelectedFaction=UnexpectedMutation}
                    end
                    local search=Search(auditKind)
                    local first=search:Query("needle",options)[1]
                    assert(first and #lib._entries[auditKind]==count and reads==count*2)
                    for i=1,20 do search:Query("needle",options) end
                    assert(reads==count*2 and search:IsEntryCurrent(first))
                    count=1000
                    FireEvent(auditKind=="skills" and "SKILL_LINES_CHANGED" or "UPDATE_FACTION")
                    assert(not search:IsEntryCurrent(first))
                    search:Query("needle",options)
                    assert(#lib._entries[auditKind]==count and reads==3000)
                    assert(#mock.errors==0)
                """)

    def test_recipe_enrichment_deduplicates_shared_item_and_category_reads(self):
        lua = talents.runtime(talents.RECIPES)
        lua.execute(r"""
            mock.recipeIDs={};mock.recipeInfo={}
            for i=1,1000 do
                mock.recipeIDs[i]=i
                mock.recipeInfo[i]={recipeID=i,name="Needle "..i,categoryID=8,learned=true}
            end
            local itemReads,schematicReads=0,0
            C_Item.GetItemNameByID=function(id)
                itemReads=itemReads+1
                assert(id==301 or id==302)
                return id==301 and "Output" or "Copper Bar"
            end
            C_TradeSkillUI.GetRecipeSchematic=function()
                schematicReads=schematicReads+1
                return {outputItemID=301,reagentSlotSchematics={{reagents={{itemID=302},{itemID=302}}}}}
            end
            local search=NewSearch("recipes")
            assert(#Query(search,"copper")==100 and #lib._entries.recipes==1000)
            assert(itemReads==2 and schematicReads==1000 and mock.calls.categories==1)
            for i=1,20 do Query(search,"copper") end
            assert(itemReads==2 and schematicReads==1000 and mock.calls.categories==1)
            assert(#mock.errors==0)
        """)

    def test_explicit_empty_talent_description_is_complete_native_metadata(self):
        lua = talents.runtime(talents.TALENTS)
        lua.execute(r"""
            mock.now=0
            mock.definitions[32].overrideDescription=""
            local search=NewSearch("talents")
            local row=Query(search,"choice")[1]
            assert(row and row.description=="")
            assert(next(mock.spellRequests)==nil and lib._indexSources.talents.nextRetry==nil)
            local builds=mock.calls.trees
            for i=1,5 do
                mock.now=i*30
                assert(Query(search,"choice")[1]==row)
            end
            assert(mock.calls.trees==builds and next(mock.spellRequests)==nil)
            assert(#mock.errors==0)
        """)

    def test_tiered_talents_distribute_purchased_ranks_without_changing_choice_semantics(self):
        lua = talents.runtime(talents.TALENTS)
        lua.execute(r"""
            Enum={TraitNodeType={Tiered=1,Selection=2}}
            mock.nodes[11].type=Enum.TraitNodeType.Tiered
            mock.nodes[11].ranksPurchased=4
            mock.nodes[11].activeEntry={entryID=22,rank=1}
            lib:SetSourceKeywordTerms("talents",{learned="learned",unlearned="unlearned"})
            local search=NewSearch("talents")
            local first=Query(search,"precision")[1]
            local second=Query(search,"choice")[1]
            assert(first.rank==3 and first.learned and second.rank==1 and second.learned)
            assert(first.id=="7:11:21" and second.id=="7:11:22")
            assert(first.topic:find("Rank 3/3",1,true) and not first.secure)
            assert(mock.calls.entries==3, "entry metadata must be read once per entry")
            mock.nodes[11].ranksPurchased=2;FireEvent("TRAIT_NODE_CHANGED",11)
            assert(not search:IsEntryCurrent(first))
            first=Query(search,"precision")[1];second=Query(search,"choice")[1]
            assert(first.rank==2 and first.learned and second.rank==0 and not second.learned)
            mock.nodes[11].type=Enum.TraitNodeType.Selection
            FireEvent("TRAIT_NODE_CHANGED",11)
            first=Query(search,"precision")[1];second=Query(search,"choice")[1]
            assert(first.rank==0 and not first.learned and second.rank==1 and second.learned)
            assert(#mock.errors==0)
        """)

    def test_missing_tier_metadata_waits_before_assigning_ranks_to_later_tiers(self):
        lua = talents.runtime(talents.TALENTS)
        lua.execute(r"""
            Enum={TraitNodeType={Tiered=1}}
            mock.nodes[11].type=Enum.TraitNodeType.Tiered
            mock.nodes[11].ranksPurchased=4
            local info=mock.entries[21];mock.entries[21]=nil
            local search=NewSearch("talents")
            assert(#Query(search,"needle")==0)
            assert(lib:GetIndexSourceState("talents")=="pending")
            mock.entries[21]=info;FireEvent("TRAIT_NODE_ENTRY_UPDATED",21)
            assert(Query(search,"precision")[1].rank==3 and Query(search,"choice")[1].rank==1)
            assert(#mock.errors==0)
        """)

    def test_deleted_pet_retires_guid_and_nickname_before_another_journal_event(self):
        lua = runtime(True)
        lua.execute(PETS + r"""
            local search=Search("pets")
            local first=search:Query("fluffy",options)[1]
            assert(first and first.petGUID=="Pet-A" and first.favorite)
            mock.petIDs={"Pet-B"};mock.pets["Pet-A"]=nil
            FireEvent("PET_JOURNAL_PET_DELETED","Pet-A")
            assert(not search:IsEntryCurrent(first), "deleted pet action must retire immediately")
            assert(#search:Query("fluffy",options)==0, "deleted nickname must leave the index")
            local second=search:Query("cotton",options)[1]
            assert(second and second.petGUID=="Pet-B" and not second.favorite)
            assert(second.secure.macrotext:find("Pet-B",1,true))
            mock.petIDs={};mock.pets["Pet-B"]=nil
            FireEvent("PET_JOURNAL_PET_DELETED","Pet-B")
            assert(not search:IsEntryCurrent(second) and #search:Query("rabbit",options)==0)
            assert(#mock.errors==0)
        """)

    def test_mount_companion_events_do_not_rebuild_large_pet_collections(self):
        lua = runtime(True)
        lua.execute(PETS + r"""
            mock.petIDs={};mock.pets={}
            for i=1,1000 do
                local id="Pet-"..i
                mock.petIDs[i]=id
                mock.pets[id]={species=i,name="Rabbit "..i,summonable=true}
            end
            local search=Search("pets")
            local first=search:Query("rabbit",options)[1]
            assert(first and mock.petReads==1000 and mock.petLists==1)
            for i=1,20 do
                FireEvent("COMPANION_UPDATE","MOUNT")
                search:Query("rabbit",options)
            end
            assert(search:IsEntryCurrent(first), "mount updates cannot alter pet identities")
            assert(mock.petReads==1000 and mock.petLists==1, "unrelated events must not enumerate pets")
            mock.pets[first.petGUID].summonable=false
            FireEvent("COMPANION_UPDATE","CRITTER")
            assert(not search:IsEntryCurrent(first))
            search:Query("rabbit",options)
            assert(mock.petReads==2000 and mock.petLists==2)
            assert(#mock.errors==0)
        """)


if __name__ == "__main__":
    unittest.main()
