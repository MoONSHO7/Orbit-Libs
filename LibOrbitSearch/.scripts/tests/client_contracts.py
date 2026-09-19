"""Execute native-boundary and client isolation cases against the shipped Lua 5.1 library."""
import unittest

from lupa.lua51 import LuaRuntime
import search_engine as engine


def runtime(builtins=False):
    lua = LuaRuntime()
    lua.execute(engine.HARNESS)
    if builtins:
        lua.execute(engine.SOURCE_SETUP)
    for path in engine.manifest_files():
        if not builtins and path.parent.name == "Sources":
            continue
        lua.eval("LoadSource")(path.read_text(encoding="utf-8"), path.name)
    lua.execute('''
        lib = LibStub("LibOrbitSearch-1.0")
        options = {maxResults = 100, fuzzy = false, hidePassives = false}
        function Search(kind, config)
            config = config or {}
            config.kinds = {{kind = kind, label = kind, idSearch = true}}
            local search = lib:NewSearch(config)
            search:Enable()
            return search
        end
        function Entry(kind, id) return {kind=kind, id=id, name="needle", lowerName="needle"} end
    ''')
    return lua


class ClientContracts(unittest.TestCase):
    def test_declarations_and_unused_sources_need_no_optional_globals(self):
        lua = runtime(True)
        lua.execute('''
            Enum, Constants, C_Container, C_Spell, C_Item = nil, nil, nil, nil, nil
            GetItemInfo, GetInventoryItemLink, GetProfessions, GetNumMacros = nil, nil, nil, nil
            for kind, source in pairs(lib._indexSources) do
                local search = Search(kind)
                assert(#search:Query("needle", options) == 0, kind)
                assert(lib:GetIndexSourceState(kind) == "unsupported", kind)
                search:Disable()
            end
            for _, frame in ipairs(mock.frames) do assert(next(frame.events) == nil) end
            assert(#mock.errors == 0)
        ''')

    def test_missing_enums_at_actual_file_load(self):
        lua = LuaRuntime()
        lua.execute(engine.HARNESS)
        for path in engine.manifest_files():
            lua.eval("LoadSource")(path.read_text(encoding="utf-8"), path.name)
        lua.execute('assert(LibStub("LibOrbitSearch-1.0").INDEX_CONTRACT == 1 and #mock.errors == 0)')

    def test_event_union_tracks_selection_and_ignores_invalid_events(self):
        lua = runtime()
        lua.execute('''
            local selected = false
            lib:RegisterIndexSource("a", {events={"EVENT_A", "INVALID_EVENT"}, Build=function() return {} end})
            lib:RegisterIndexSource("b", {events={"EVENT_B"}, Build=function() return {} end})
            local first = Search("a", {IsKindEnabled=function() return selected end})
            assert(next(lib._eventFrame.events) == nil)
            local second = Search("b")
            assert(lib._eventFrame.events.EVENT_B and not lib._eventFrame.events.EVENT_A)
            selected = true; first:NotifySettingsChanged()
            assert(lib._eventFrame.events.EVENT_A and not lib._eventFrame.events.INVALID_EVENT)
            first:Disable()
            assert(lib._eventFrame.events.EVENT_B and not lib._eventFrame.events.EVENT_A)
            second:Disable(); assert(next(lib._eventFrame.events) == nil)
        ''')

    def test_pending_ready_empty_unavailable_recovery_and_stale_entries(self):
        lua = runtime()
        lua.execute('''
            local phase, data, builds = "pending", {Entry("a", 1)}, 0
            lib:RegisterIndexSource("a", {events={"EVENT_A"}, GetAvailability=function() return phase end,
                Build=function() builds=builds+1; return data end})
            local first, second = Search("a"), Search("a")
            assert(#first:Query("needle", options) == 0 and builds == 0)
            assert(lib:GetIndexSourceState("a") == "pending")
            phase="ready"; lib:NotifyIndexSourceChanged("a")
            local old = first:Query("needle", options)[1]
            assert(old and second:Query("needle", options)[1] == old and builds == 1)
            assert(first:IsEntryCurrent(old))
            data={}; FireEvent("EVENT_A")
            assert(not first:IsEntryCurrent(old))
            assert(#first:Query("needle", options) == 0 and lib:GetIndexSourceState("a") == "ready")
            phase="unsupported"; lib:NotifyIndexSourceChanged("a")
            assert(not lib._eventFrame.events.EVENT_A and lib._eventFrame.events.ADDON_LOADED)
            assert(#first:Query("needle", options) == 0 and lib:GetIndexSourceState("a") == "unsupported")
            phase="ready"; data={Entry("a",2)}; FireEvent("ADDON_LOADED")
            assert(first:Query("needle",options)[1].id == 2 and not first:IsEntryCurrent(old))
        ''')

    def test_build_pending_failure_and_explicit_recovery(self):
        lua = runtime()
        lua.execute('''
            local phase="pending"
            lib:RegisterIndexSource("a", {events={"EVENT_A"}, Build=function()
                if phase=="pending" then return nil, "pending", "loading" end
                if phase=="fail" then error("bad native data") end
                return {Entry("a",1)}
            end})
            local search=Search("a")
            assert(#search:Query("needle",options)==0)
            assert(lib:GetIndexSourceState("a")=="pending")
            phase="ready"; FireEvent("EVENT_A")
            local old=search:Query("needle",options)[1]
            phase="fail"; FireEvent("EVENT_A")
            assert(#search:Query("needle",options)==0 and not search:IsEntryCurrent(old))
            search:Query("needle",options); assert(#mock.errors==1)
            phase="ready"; lib:NotifyIndexSourceChanged("a")
            assert(#search:Query("needle",options)==1 and not lib:GetBuildErrors().a)
        ''')

    def test_source_replacement_during_build_cannot_publish_old_rows(self):
        lua = runtime()
        lua.execute('''
            lib:RegisterIndexSource("a", {Build=function()
                lib:RegisterIndexSource("a", {Build=function() return {Entry("a",2)} end})
                return {Entry("a",1)}
            end})
            local search=Search("a")
            assert(#search:Query("needle",options)==0)
            assert(search:Query("needle",options)[1].id==2)
        ''')

    def test_id_types_late_results_disable_and_lost_request_retry(self):
        lua = runtime()
        lua.execute('''
            C_Spell=nil
            local count=0
            C_Item.RequestLoadItemDataByID=function() count=count+1 end
            local enabled=true
            local search=Search("ids", {IsIDTypeEnabled=function() return enabled end})
            search:SetOpen(true)
            assert(not lib._idFrame.events.SPELL_DATA_LOAD_RESULT and lib._idFrame.events.GET_ITEM_INFO_RECEIVED)
            assert(#search:Query("123",options)==0 and count==1)
            search:Query("123",options); assert(count==1)
            mock.now=mock.now+31; search:Query("123",options); assert(count==2)
            search:Disable(); mock.itemNames[123]="needle"; FireEvent("GET_ITEM_INFO_RECEIVED",123,true)
            assert(next(lib._idFrame.events)==nil and lib._idCaches.itemPending.count==0)
            search:Enable(); assert(search:Query("123",options)[1].idType=="item")
            enabled=false; search:NotifySettingsChanged()
            assert(#search:Query("123",options)==0 and next(lib._idFrame.events)==nil)
        ''')

    def test_invalidation_and_reentrant_query_during_build(self):
        lua = runtime()
        lua.execute('''
            local search, builds = nil, 0
            lib:RegisterIndexSource("a", {Build=function()
                builds=builds+1
                if builds==1 then
                    assert(#search:Query("needle",options)==0)
                    lib:MarkDirty("a")
                end
                return {Entry("a",builds)}
            end})
            search=Search("a")
            assert(#search:Query("needle",options)==0 and builds==1)
            assert(search:Query("needle",options)[1].id==2 and builds==2)
        ''')

    def test_id_only_search_recovers_after_native_namespace_arrives(self):
        lua = runtime()
        lua.execute('''
            local items=C_Item
            C_Item,C_Spell=nil,nil
            local search=Search("ids", {IsIDTypeEnabled=function(idType) return idType=="item" end})
            search:SetOpen(true)
            assert(lib._idFrame.events.ADDON_LOADED and not lib._idFrame.events.GET_ITEM_INFO_RECEIVED)
            assert(#search:Query("123",options)==0)
            C_Item=items; FireEvent("ADDON_LOADED","Blizzard_Test")
            assert(lib._idFrame.events.GET_ITEM_INFO_RECEIVED and not lib._idFrame.events.SPELL_DATA_LOAD_RESULT)
            assert(#search:Query("123",options)==0 and mock.requestedItem==123)
            mock.itemNames[123]="needle"; FireEvent("GET_ITEM_INFO_RECEIVED",123,true)
            assert(search:Query("123",options)[1].idType=="item")
            search:Disable(); assert(next(lib._idFrame.events)==nil)
        ''')

    def test_keyring_quest_nil_and_native_bag_range(self):
        lua = runtime(True)
        lua.execute('''
            NUM_TOTAL_EQUIPPED_BAG_SLOTS=4
            C_ActionBar={ShouldShowKeyring=function() return true end}
            C_Container.GetContainerNumSlots=function(bag) assert(bag~=5); return bag==-1 and 1 or 0 end
            C_Container.GetContainerItemInfo=function() return {itemID=11,hyperlink="item:11",iconFileID=1} end
            C_Container.GetContainerItemQuestInfo=function() return nil end
            mock.items["item:11"]={name="needle key"}
            local search=Search("bags")
            local entry=search:Query("needle",options)[1]
            assert(entry.id==11 and entry.secure.item=="item:11")
            C_ActionBar.ShouldShowKeyring=function() return false end; lib:InvalidateAll()
            assert(#search:Query("needle",options)==0 and #mock.errors==0)
        ''')

    def test_equipped_ammo_ranged_and_deferred_item_names(self):
        lua = runtime(True)
        lua.execute('''
            INVSLOT_AMMO=0
            GetInventoryItemLink=function(_,slot) if slot==0 or slot==18 then return "item:"..slot end end
            GetInventoryItemID=function(_,slot) return slot+100 end
            GetInventoryItemTexture=function() return 1 end
            mock.items["item:18"]={name="needle bow"}
            local search=Search("equipped")
            assert(#search:Query("needle",options)==1 and mock.requestedItem==100)
            mock.items["item:0"]={name="needle arrow"}; FireEvent("GET_ITEM_INFO_RECEIVED",100,true)
            assert(#search:Query("needle",options)==2)
        ''')

    def test_currency_ids_nested_duplicate_headers_and_error_restore(self):
        lua = runtime(True)
        lua.execute('''
            local child={name="same",isHeader=true,isHeaderExpanded=false, children={{name="needle",currencyID=300}}}
            local parent={name="same",isHeader=true,isHeaderExpanded=false,children={child}}
            local sibling={name="same",isHeader=true,isHeaderExpanded=false,children={{name="needle two",currencyID=400}}}
            local function rows()
                local out={}
                local function add(row)
                    out[#out+1]=row
                    if row.isHeaderExpanded then for _,nextRow in ipairs(row.children) do add(nextRow) end end
                end
                add(parent); add(sibling); return out
            end
            local fail=false
            C_CurrencyInfo={GetCurrencyListSize=function() return #rows() end,
                GetCurrencyListInfo=function(i) return rows()[i] end,
                ExpandCurrencyList=function(i,expanded) rows()[i].isHeaderExpanded=expanded end,
                GetCurrencyListLink=function(i) if fail then error("link failed") end return "currency:"..rows()[i].currencyID end}
            local search=Search("currencies")
            local result=search:Query("needle",options)
            assert(#result==2 and result[1].id==300 and result[2].id==400)
            assert(not parent.isHeaderExpanded and not child.isHeaderExpanded and not sibling.isHeaderExpanded)
            fail=true; lib:InvalidateAll(); assert(#search:Query("needle",options)==0)
            assert(not parent.isHeaderExpanded and not child.isHeaderExpanded and not sibling.isHeaderExpanded)
        ''')

    def test_profession_holes_secondary_actions_and_spell_identity(self):
        lua = runtime(True)
        lua.execute('''
            GetProfessions=function() return nil,2,3,nil,5 end
            GetProfessionInfo=function(i) return "needle profession "..i,1,1,100,2,i*10,200+i end
            C_SpellBook={GetSpellBookItemInfo=function(slot,bank) assert(bank==0); return {name="needle action",spellID=1000+slot} end}
            local result=Search("professions"):Query("needle",options)
            assert(#result==6)
            for _,entry in ipairs(result) do assert(entry.spellID>1000 and entry.secure.spell==entry.spellID) end
        ''')

    def test_spellbook_zero_bank_optional_flyouts_pet_ranks(self):
        lua = runtime(True)
        lua.execute('''
            Enum.SpellBookItemType={Spell=1,Flyout=2}
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return {itemIndexOffset=0,numSpellBookItems=2} end,
                GetSpellBookItemInfo=function(slot,bank)
                    if bank==1 then return {itemType=1,name="needle pet",spellID=99} end
                    return slot==1 and {itemType=1,name="needle rank",spellID=42} or {itemType=2,name="fly",actionID=8}
                end, HasPetSpells=function() return 1 end}
            GetFlyoutInfo,GetFlyoutSlotInfo=nil,nil
            local result=Search("spellbook"):Query("needle",options)
            local ids={}; for _,entry in ipairs(result) do ids[entry.secure.spell]=true end
            assert(#result==2 and ids[42] and ids[99])
        ''')

    def test_companion_summon_does_not_require_battle_metadata(self):
        lua = runtime(True)
        lua.execute('''
            BATTLE_PET_NAME_1="battle-family"
            C_PetJournal={GetOwnedPetIDs=function() return {"Pet-1"} end,
                GetPetInfoByPetID=function() return 123,nil,1,0,0,0,false,"needle companion",1,1,nil,nil,nil,false,false end,
                SummonPetByGUID=function() end, PetIsSummonable=function() return true end}
            local search=Search("pets")
            local entry=search:Query("needle",options)[1]
            assert(entry.secure and not entry.lowerName:find("battle%-family"))
            C_PetJournal.SummonPetByGUID=nil; lib:InvalidateAll()
            entry=search:Query("needle",options)[1]; assert(entry.passive and not entry.secure)
        ''')

    def test_mounts_unknown_type_favorites_and_skyriding_are_independent(self):
        lua = runtime(True)
        lua.execute('''
            local unlocked=false
            C_MountJournal={GetMountIDs=function() return {123} end,
                GetMountInfoByID=function() return "needle mount",5,1,false,true,1,true,false,nil,false,true,123,false end,
                GetMountInfoExtraByID=function() return 1,"","",false,99999 end,
                SummonByID=function() end, IsDragonridingUnlocked=function() return unlocked end,
                GetCollectedDragonridingMounts=function() assert(unlocked); return {123} end}
            local search=Search("mounts")
            local entry=search:Query("needle",options)[1]
            assert(entry.favorite and entry.secure and not entry.lowerName:find("flying"))
            assert(not entry.lowerName:find("skyriding"))
            unlocked=true; lib:InvalidateAll()
            assert(search:Query("skyriding",options)[1].id==123)
        ''')

    def test_toys_heirlooms_and_macro_limits(self):
        lua = runtime(True)
        lua.execute('''
            PlayerHasToy=function() return true end
            C_ToyBox={GetNumFilteredToys=function() return 1 end,GetToyFromIndex=function() return 77 end,
                GetToyInfo=function() return 77,"needle toy",1 end}
            assert(Search("toys"):Query("needle",options)[1].secure.macrotext=="/use item:77")
            GetItemCount=function() return 0 end
            C_Heirloom={GetHeirloomItemIDs=function() return {88} end, PlayerHasHeirloom=function() return true end,
                GetHeirloomInfo=function() return "needle heirloom",1 end}
            local heirloom=Search("heirlooms"):Query("needle",options)[1]
            assert(heirloom.passive and not heirloom.secure)
            Constants={MacroConsts={MAX_ACCOUNT_MACROS=120}}
            GetNumMacros=function() return 1,1 end
            GetMacroInfo=function(i) assert(i==1 or i==121); return "needle macro",1 end
            local macros=Search("macros"):Query("needle",options)
            assert(#macros==2 and macros[2].secure.macro==121)
        ''')


if __name__ == "__main__":
    unittest.main()
