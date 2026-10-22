"""Stress native request ownership with call counts and Lua-only weak-reference collection."""

import re
import unittest

import search_engine as engine
import search_talents_recipes as sources


AUDIT = r"""
function Count(t)
    local count=0
    for _ in pairs(t) do count=count+1 end
    return count
end
weak=setmetatable({}, {__mode="v"})
mock.reads={}
function CollectAudit()
    collectgarbage("collect")
    collectgarbage("collect")
end
function NativeSource(kind, ids)
    local source={kind=kind,ids=ids,events={{event="GET_ITEM_INFO_RECEIVED",items=true},
        {event="ITEM_DATA_LOAD_RESULT",items=true},"AUDIT_CHANGED"}}
    function source:Build()
        self.builds=(self.builds or 0)+1
        local rows={}
        for _,id in ipairs(self.ids) do
            mock.reads[kind]=(mock.reads[kind] or 0)+1
            local name=C_Item.GetItemNameByID(id)
            if name then
                rows[#rows+1]={kind=kind,id=id,name=name,lowerName=lib.Fold(name)}
            else
                lib._NativeContract.RequestItem(self,id)
            end
        end
        return rows
    end
    lib:RegisterIndexSource(kind,source)
    return source
end
function AuditSearch(kinds, open)
    local rows={}
    for _,kind in ipairs(kinds) do rows[#rows+1]={kind=kind,label=kind} end
    local search=lib:NewSearch({kinds=rows,onIndexUpdated=function()
        mock.updates=(mock.updates or 0)+1
    end})
    search:Enable();search:SetOpen(open==true)
    return search
end
function Sequence(first,last)
    local out={}
    for id=first,last do out[#out+1]=id end
    return out
end
function CheckCache(cache)
    assert(Count(cache.entries)==cache.count and cache.count<=cache.capacity)
    local count,previous=0,nil
    local node=cache.first
    while node do
        assert(node.previous==previous and cache.entries[node.key]==node)
        previous=node;node=node.next;count=count+1
        assert(count<=cache.capacity)
    end
    assert(count==cache.count and previous==cache.last)
    if cache.first then assert(cache.first.previous==nil and cache.last.next==nil) end
end
"""


def runtime(setup=""):
    lua = sources.runtime(setup)
    lua.execute(AUDIT)
    return lua


def upgrade(lua, revision):
    for path in engine.manifest_files():
        text = path.read_text(encoding="utf-8")
        if path.name == "LibOrbitSearch-1.0.lua":
            text = re.sub(
                r'local MAJOR, MINOR = "LibOrbitSearch-1.0", \d+',
                f'local MAJOR, MINOR = "LibOrbitSearch-1.0", {revision}',
                text,
            )
        lua.eval("LoadSource")(text, path.name)


class AsyncLifecycleAudit(unittest.TestCase):
    def test_bounded_cache_eviction_and_removal_release_values_and_preserve_links(self):
        lua = runtime()
        lua.execute(r"""
            auditCache=lib._BoundedCache.Create(256)
            for id=1,10000 do
                local value={id=id}
                weak[id]=value
                auditCache:Set(id,value)
                if id%3==0 then auditCache:Get(id-1) end
                if id%31==0 then CheckCache(auditCache) end
            end
            CheckCache(auditCache)
        """)
        lua.execute(r"""
            CollectAudit()
            assert(Count(weak)==256 and auditCache.count==256)
            for id in pairs(auditCache.entries) do auditCache:Remove(id) end
            CheckCache(auditCache);CollectAudit()
            assert(Count(weak)==0 and not auditCache.first and not auditCache.last)
        """)

    def test_item_receipt_and_source_cycles_collect_after_last_demand_and_unregister(self):
        lua = runtime()
        lua.execute(r"""
            local source=NativeSource("audititems",{1,2,3})
            auditSearch=AuditSearch({"audititems"})
            Query(auditSearch,"needle")
            weak.source=source
            weak.receipt=lib._sourceItemPending.audititems
            weak.items=weak.receipt.items
            assert(next(lib._sourceItemBuilders)==nil)
            auditSearch:Disable();lib:UnregisterIndexSource("audititems")
            weak.search=auditSearch;auditSearch=nil
        """)
        lua.execute(r"""
            CollectAudit()
            assert(not weak.source and not weak.receipt and not weak.items and not weak.search)
            assert(next(lib._sourceItemPending)==nil and next(lib._sourceItemBuilders)==nil)
            assert(lib._sourceItemRequests.count==3)
            for _,entry in pairs(lib._sourceItemRequests.entries) do assert(type(entry.value)=="number") end
            FireEvent("GET_ITEM_INFO_RECEIVED",1,true);FlushTimers()
            assert(not mock.updates and #mock.errors==0)
        """)

    def test_replacement_releases_old_receipts_and_late_unrelated_completion_does_no_work(self):
        lua = runtime()
        lua.execute(r"""
            NativeSource("audititems",{1})
            auditSearch=AuditSearch({"audititems"})
            Query(auditSearch,"needle")
            weak.source=lib._indexSources.audititems
            weak.receipt=lib._sourceItemPending.audititems
            NativeSource("audititems",{2})
            Query(auditSearch,"needle")
        """)
        lua.execute(r"""
            CollectAudit()
            assert(not weak.source and not weak.receipt)
            for i=1,1000 do FireEvent("GET_ITEM_INFO_RECEIVED",1,true) end
            assert(not lib._dirty.audititems and lib._indexSources.audititems.builds==1)
            assert(mock.itemRequests[1]==1 and mock.itemRequests[2]==1)
            mock.itemNames[2]="needle recovered"
            FireEvent("GET_ITEM_INFO_RECEIVED",2,true)
            assert(Query(auditSearch,"needle")[1].id==2 and #mock.errors==0)
        """)

    def test_shared_receipts_dedupe_requests_and_coalesce_completion_bursts(self):
        lua = runtime()
        lua.execute(r"""
            NativeSource("audita",Sequence(1,128));NativeSource("auditb",Sequence(1,128))
            auditSearch=AuditSearch({"audita","auditb"},true)
            Query(auditSearch,"needle")
            assert(Count(mock.itemRequests)==128)
            for id=1,128 do assert(mock.itemRequests[id]==1);mock.itemNames[id]="needle "..id end
            for id=1,128 do FireEvent("GET_ITEM_INFO_RECEIVED",id,true) end
            assert(lib._indexSources.audita.builds==1 and lib._indexSources.auditb.builds==1)
            local activeTimers=0
            for _,timer in ipairs(mock.timers) do if not timer.cancelled then activeTimers=activeTimers+1 end end
            assert(activeTimers==1)
            FlushTimers()
            assert(lib._indexSources.audita.builds==2 and lib._indexSources.auditb.builds==2)
            assert(mock.updates==1 and next(lib._sourceItemPending)==nil)
            for i=1,100 do Query(auditSearch,"needle") end
            assert(mock.reads.audita==256 and mock.reads.auditb==256 and #mock.errors==0)
        """)

    def test_item_receipts_and_requests_stay_bounded_under_overflow(self):
        lua = runtime()
        lua.execute(r"""
            NativeSource("audititems",Sequence(1,1024))
            auditSearch=AuditSearch({"audititems"})
            Query(auditSearch,"needle")
            assert(lib._sourceItemRequests.count==256)
            assert(lib._sourceItemPending.audititems.items.count==256)
            CheckCache(lib._sourceItemRequests);CheckCache(lib._sourceItemPending.audititems.items)
            for i=1,100 do Query(auditSearch,"needle") end
            assert(mock.reads.audititems==1024)
            assert(Count(mock.itemRequests)==1024)
            auditSearch:Disable()
            assert(next(lib._sourceItemPending)==nil and next(lib._sourceItemBuilders)==nil)
        """)

    def test_large_item_catalogue_rebuilds_cannot_repeat_a_request_sweep_inside_thirty_seconds(self):
        lua = runtime()
        lua.execute(r"""
            mock.now=0
            NativeSource("audititems",Sequence(1,1024))
            auditSearch=AuditSearch({"audititems"})
            Query(auditSearch,"needle")
            for i=1,10 do FireEvent("AUDIT_CHANGED");Query(auditSearch,"needle") end
            for id=1,1024 do assert(mock.itemRequests[id]==1) end
            mock.now=10
            lib._indexSources.audititems.ids[1025]=1025
            FireEvent("AUDIT_CHANGED");Query(auditSearch,"needle")
            assert(not mock.itemRequests[1025] and lib._sourceItemPending.audititems.retryAt==30)
            auditSearch:Disable();auditSearch:Enable();Query(auditSearch,"needle")
            assert(not mock.itemRequests[1025])
            mock.now=30;Query(auditSearch,"needle")
            for id=1,1024 do assert(mock.itemRequests[id]==2) end
            assert(mock.itemRequests[1025]==1 and lib._sourceItemPending.audititems.retryAt==60)
            for id=1,1025 do mock.itemNames[id]="needle "..id end
            FireEvent("GET_ITEM_INFO_RECEIVED",1025,true);Query(auditSearch,"needle")
            assert(not lib._sourceItemPending.audititems)
            local reads=mock.reads.audititems;mock.now=120
            for i=1,100 do Query(auditSearch,"needle") end
            assert(mock.reads.audititems==reads and #mock.errors==0)
        """)

    def test_large_talent_catalogue_rebuilds_cannot_repeat_a_request_sweep_inside_thirty_seconds(self):
        lua = runtime(sources.TALENTS)
        lua.execute(r"""
            mock.now=0
            mock.nodes={[11]={ID=11,isVisible=true,entryIDs={}}}
            mock.entries={};mock.definitions={};mock.spellNames={}
            for id=1,1024 do
                mock.nodes[11].entryIDs[id]=id
                mock.entries[id]={definitionID=id,maxRanks=1}
                mock.definitions[id]={spellID=id}
            end
            auditSearch=AuditSearch({"talents"})
            Query(auditSearch,"needle")
            for i=1,10 do FireEvent("TRAIT_NODE_CHANGED",11);Query(auditSearch,"needle") end
            for id=1,1024 do assert(mock.spellRequests[id]==1) end
            assert(lib._indexSources.talents.spellRequests.count==256)
            auditSearch:Disable();mock.now=29;auditSearch:Enable();Query(auditSearch,"needle")
            for id=1,1024 do assert(mock.spellRequests[id]==1) end
            mock.now=30;Query(auditSearch,"needle")
            for id=1,1024 do assert(mock.spellRequests[id]==2) end
            for id=1,1024 do mock.spellNames[id]="needle "..id end
            FireEvent("SPELL_DATA_LOAD_RESULT",1024,true);Query(auditSearch,"needle")
            assert(lib._indexSources.talents.nextRetry==nil)
            local builds=mock.calls.trees;mock.now=120;Query(auditSearch,"needle")
            assert(mock.calls.trees==builds and #mock.errors==0)
        """)

    def test_synchronous_talent_demand_loss_stops_remaining_requests_and_reenable_recovers(self):
        lua = runtime(sources.TALENTS)
        lua.execute(r"""
            mock.now=0
            mock.definitions[31].overrideName=nil;mock.spellNames[102]=nil
            auditSearch=AuditSearch({"talents"})
            C_Spell.RequestLoadSpellData=function(id)
                mock.spellRequests[id]=(mock.spellRequests[id] or 0)+1
                if not mock.disabledOnce then mock.disabledOnce=true;auditSearch:Disable() end
            end
            Query(auditSearch,"needle")
            assert(mock.spellRequests[101]==1 and not mock.spellRequests[102])
            assert(not lib._eventFrame.events.SPELL_DATA_LOAD_RESULT and #lib._entries.talents==0)
            auditSearch:Enable();Query(auditSearch,"needle")
            assert(mock.spellRequests[101]==1 and not mock.spellRequests[102])
            mock.now=30;Query(auditSearch,"needle")
            assert(mock.spellRequests[101]==2 and mock.spellRequests[102]==1)
            mock.spellNames[101]="Needle focus";mock.spellNames[102]="Needle choice"
            FireEvent("SPELL_DATA_LOAD_RESULT",102,true)
            assert(#Query(auditSearch,"needle")==2 and lib._indexSources.talents.nextRetry==nil)
            assert(#mock.errors==0)
        """)

    def test_synchronous_talent_replacement_stops_old_requests_and_rejects_old_rows(self):
        lua = runtime(sources.TALENTS)
        lua.execute(r"""
            mock.definitions[31].overrideName=nil;mock.spellNames[102]=nil
            auditSearch=AuditSearch({"talents"})
            C_Spell.RequestLoadSpellData=function(id)
                mock.spellRequests[id]=(mock.spellRequests[id] or 0)+1
                lib:RegisterIndexSource("talents",{Build=function()
                    return {{kind="talents",id="replacement",name="Needle replacement",lowerName="needle replacement"}}
                end})
            end
            Query(auditSearch,"needle")
            assert(mock.spellRequests[101]==1 and not mock.spellRequests[102])
            local rows=Query(auditSearch,"needle")
            assert(#rows==1 and rows[1].id=="replacement")
            FireEvent("SPELL_DATA_LOAD_RESULT",101,true)
            assert(not lib._dirty.talents and #mock.errors==0)
        """)

    def test_unavailable_talent_description_api_omits_enrichment_without_requesting_it(self):
        lua = runtime(sources.TALENTS)
        lua.execute(r"""
            C_Spell.GetSpellDescription=nil
            auditSearch=AuditSearch({"talents"})
            assert(#Query(auditSearch,"needle")==2 and next(mock.spellRequests)==nil)
            assert(lib._indexSources.talents.nextRetry==nil)
            mock.now=mock.now+60;Query(auditSearch,"needle")
            assert(mock.calls.trees==1 and next(mock.spellRequests)==nil)
            mock.spellNames[102]=nil;FireEvent("TRAIT_NODE_CHANGED",11);Query(auditSearch,"needle")
            assert(mock.spellRequests[102]==1)
            mock.spellNames[102]="Needle choice";FireEvent("SPELL_DATA_LOAD_RESULT",102,true)
            assert(#Query(auditSearch,"needle")==2 and lib._indexSources.talents.nextRetry==nil)
            assert(#mock.errors==0)
        """)

    def test_native_item_load_result_alone_recovers_recipes_and_ids_and_duplicate_info_is_ignored(self):
        lua = runtime(sources.RECIPES)
        lua.execute(r"""
            C_TradeSkillUI.GetRecipeSchematic=function()
                return {outputItemID=1,reagentSlotSchematics={}}
            end
            auditSearch=AuditSearch({"recipes","ids"},true)
            Query(auditSearch,"needle");Query(auditSearch,"123")
            assert(lib._eventFrame.events.ITEM_DATA_LOAD_RESULT and lib._idFrame.events.ITEM_DATA_LOAD_RESULT)
            mock.itemNames[1]="Tempered blade";mock.itemNames[123]="Needle numeric"
            FireEvent("ITEM_DATA_LOAD_RESULT",1,true);FireEvent("ITEM_DATA_LOAD_RESULT",123,true)
            FlushTimers()
            assert(#Query(auditSearch,"tempered")==2 and Query(auditSearch,"123")[1].id==123)
            local updates=mock.updates
            for i=1,100 do
                FireEvent("GET_ITEM_INFO_RECEIVED",1,true);FireEvent("GET_ITEM_INFO_RECEIVED",123,true)
            end
            FlushTimers()
            assert(mock.updates==updates and mock.calls.recipes==2 and #mock.errors==0)
            auditSearch:Disable()
            assert(not lib._eventFrame.events.ITEM_DATA_LOAD_RESULT and not lib._idFrame.events.ITEM_DATA_LOAD_RESULT)
        """)

    def test_id_item_observation_accepts_either_valid_native_completion_event(self):
        for event in ("ITEM_DATA_LOAD_RESULT", "GET_ITEM_INFO_RECEIVED"):
            with self.subTest(event=event):
                lua = runtime()
                lua.globals().validItemEvent = event
                lua.execute(r"""
                    C_EventUtils.IsEventValid=function(event)
                        return event~="ITEM_DATA_LOAD_RESULT" and event~="GET_ITEM_INFO_RECEIVED"
                            or event==validItemEvent
                    end
                    auditSearch=AuditSearch({"ids"},true)
                    Query(auditSearch,"123")
                    assert(lib._idFrame.events[validItemEvent])
                    assert(not lib._idFrame.events[validItemEvent=="ITEM_DATA_LOAD_RESULT"
                        and "GET_ITEM_INFO_RECEIVED" or "ITEM_DATA_LOAD_RESULT"])
                    mock.itemNames[123]="Needle numeric";FireEvent(validItemEvent,123,true)
                    assert(Query(auditSearch,"123")[1].idType=="item" and #mock.errors==0)
                """)

    def test_synchronous_native_item_load_result_retires_build_and_recovers_without_repeat_request(self):
        lua = runtime(sources.RECIPES)
        lua.execute(r"""
            C_TradeSkillUI.GetRecipeSchematic=function()
                return {outputItemID=1,reagentSlotSchematics={}}
            end
            C_Item.RequestLoadItemDataByID=function(id)
                mock.itemRequests[id]=(mock.itemRequests[id] or 0)+1
                mock.itemNames[id]="Tempered blade";FireEvent("ITEM_DATA_LOAD_RESULT",id,true)
            end
            auditSearch=AuditSearch({"recipes"})
            Query(auditSearch,"needle")
            assert(lib._dirty.recipes and not lib._sourceItemPending.recipes)
            assert(#Query(auditSearch,"tempered")==2 and mock.itemRequests[1]==1)
            assert(next(lib._sourceItemBuilders)==nil and #mock.errors==0)
        """)

    def test_aborted_synchronous_item_sweeps_do_not_delay_never_requested_ids(self):
        lua = runtime()
        lua.execute(r"""
            mock.now=0
            NativeSource("audititems",{1,2,3})
            C_Item.RequestLoadItemDataByID=function(id)
                mock.itemRequests[id]=(mock.itemRequests[id] or 0)+1
                mock.itemNames[id]="needle "..id
                FireEvent("ITEM_DATA_LOAD_RESULT",id,true)
            end
            auditSearch=AuditSearch({"audititems"})
            for id=1,3 do
                Query(auditSearch,"needle")
                assert(mock.itemRequests[id]==1 and not mock.itemRequests[id+1])
                assert(lib._dirty.audititems and not lib._sourceItemPending.audititems)
                assert(lib._indexSources.audititems._itemRequestSweepAt==nil)
                assert(next(lib._sourceItemBuilders)==nil)
            end
            assert(#Query(auditSearch,"needle")==3 and mock.now==0)
            for id=1,3 do assert(mock.itemRequests[id]==1) end
            assert(not lib._dirty.audititems and #mock.errors==0)
        """)

    def test_id_pending_and_positive_caches_are_bounded_and_drop_late_callbacks(self):
        lua = runtime()
        lua.execute(r"""
            auditSearch=AuditSearch({"ids"},true)
            for id=1,1024 do Query(auditSearch,tostring(id)) end
            for _,kind in ipairs({"spellPending","itemPending"}) do
                assert(lib._idCaches[kind].count==256);CheckCache(lib._idCaches[kind])
                weak[kind]=lib._idCaches[kind]
            end
            auditSearch:Disable()
            for id=1,1024 do
                FireEvent("SPELL_DATA_LOAD_RESULT",id,true)
                FireEvent("GET_ITEM_INFO_RECEIVED",id,true)
            end
            assert(not mock.updates)
        """)
        lua.execute(r"""
            CollectAudit()
            assert(not weak.spellPending and not weak.itemPending)
            auditSearch:Enable()
            for id=1,1024 do
                mock.itemNames[id]="needle item "..id
                mock.spellNames[id]="needle spell "..id
                Query(auditSearch,tostring(id))
            end
            assert(lib._idCaches.spell.count==256 and lib._idCaches.item.count==256)
            CheckCache(lib._idCaches.spell);CheckCache(lib._idCaches.item)
            assert(#mock.errors==0)
        """)

    def test_lost_numeric_id_load_retries_once_after_deadline_and_sync_receipt_recovers(self):
        lua = runtime()
        lua.execute(r"""
            auditSearch=AuditSearch({"ids"},true)
            Query(auditSearch,"123")
            for i=1,100 do Query(auditSearch,"123") end
            assert(mock.itemRequests[123]==1 and mock.spellRequests[123]==1)
            mock.now=mock.now+30
            C_Item.RequestLoadItemDataByID=function(id)
                mock.itemRequests[id]=mock.itemRequests[id]+1
                mock.itemNames[id]="needle recovered"
                FireEvent("GET_ITEM_INFO_RECEIVED",id,true)
            end
            Query(auditSearch,"123")
            assert(mock.itemRequests[123]==2 and mock.spellRequests[123]==2)
            assert(mock.updates==1)
            local rows=Query(auditSearch,"123")
            assert(#rows==1 and rows[1].idType=="item")
            assert(lib._idCaches.itemPending.count==0 and #mock.errors==0)
        """)

    def test_recipe_warm_queries_do_not_repeat_schematic_or_reagent_collection(self):
        lua = runtime(sources.RECIPES)
        lua.execute(r"""
            mock.schematics=0;mock.itemReads=0
            C_TradeSkillUI.GetRecipeSchematic=function()
                mock.schematics=mock.schematics+1
                return {outputItemID=1,reagentSlotSchematics={{reagents={{itemID=2},{itemID=2}}}}}
            end
            local getName=C_Item.GetItemNameByID
            C_Item.GetItemNameByID=function(id) mock.itemReads=mock.itemReads+1;return getName(id) end
            auditSearch=AuditSearch({"recipes"},true)
            Query(auditSearch,"needle")
            assert(mock.schematics==2 and mock.itemReads==2)
            for i=1,1000 do Query(auditSearch,"needle") end
            assert(mock.schematics==2 and mock.itemReads==2)
            for i=1,1000 do FireEvent("GET_ITEM_INFO_RECEIVED",999,true) end
            FlushTimers()
            assert(mock.schematics==2 and mock.itemReads==2 and not mock.updates)
            assert(mock.itemRequests[1]==1 and mock.itemRequests[2]==1 and #mock.errors==0)
        """)

    def test_recipe_build_does_not_retain_native_schematic_or_category_tables(self):
        lua = runtime(sources.RECIPES)
        lua.execute(r"""
            mock.itemNames[1]="Tempered blade";mock.itemNames[2]="Copper bar"
            C_TradeSkillUI.GetRecipeSchematic=function(id)
                local reagent={itemID=2}
                local slot={reagents={reagent}}
                local schematic={outputItemID=1,reagentSlotSchematics={slot}}
                weak["reagent"..id]=reagent;weak["slot"..id]=slot;weak["schematic"..id]=schematic
                return schematic
            end
            C_TradeSkillUI.GetCategoryInfo=function()
                local category={name="Armaments"}
                weak.category=category
                return category
            end
            auditSearch=AuditSearch({"recipes"})
            assert(#Query(auditSearch,"copper")==2)
        """)
        lua.execute(r"""
            CollectAudit()
            assert(Count(weak)==0 and #lib._entries.recipes==2 and #mock.errors==0)
        """)

    def test_talent_build_copies_fields_without_retaining_native_snapshot_tables(self):
        lua = runtime(sources.TALENTS)
        lua.execute(r"""
            mock.snapshots=0
            local function Snapshot(value)
                if type(value)~="table" then return value end
                local copy={}
                mock.snapshots=mock.snapshots+1;weak[mock.snapshots]=copy
                for key,child in pairs(value) do copy[key]=Snapshot(child) end
                return copy
            end
            for _,name in ipairs({"GetConfigInfo","GetTreeNodes","GetNodeInfo","GetEntryInfo",
                "GetDefinitionInfo","GetTreeInfo","GetGroupDisplayInfoByTreeID"}) do
                local native=C_Traits[name]
                C_Traits[name]=function(...) return Snapshot(native(...)) end
            end
            auditSearch=AuditSearch({"talents"})
            assert(#Query(auditSearch,"needle")==2 and mock.snapshots>10)
        """)
        lua.execute(r"""
            CollectAudit()
            assert(Count(weak)==0 and #lib._entries.talents==2 and #mock.errors==0)
        """)

    def test_embedded_upgrade_releases_previous_source_and_boundary_objects(self):
        lua = runtime(sources.TALENTS + sources.RECIPES)
        lua.execute(r"""
            mock.spellNames[102]=nil
            C_TradeSkillUI.GetRecipeSchematic=function()
                return {outputItemID=1,reagentSlotSchematics={}}
            end
            auditSearch=AuditSearch({"talents","recipes","ids"},true)
            Query(auditSearch,"needle");Query(auditSearch,"123")
            weak.native=lib._NativeContract;weak.lookup=lib._IDLookup
            weak.talents=lib._indexSources.talents;weak.recipes=lib._indexSources.recipes
            weak.receipt=lib._sourceItemPending.recipes
            itemRequestCache=lib._sourceItemRequests;idCaches=lib._idCaches
            oldIDFrame=lib._idFrame;oldEventFrame=lib._eventFrame
        """)
        upgrade(lua, 100)
        lua.execute(r"""
            CollectAudit()
            assert(not weak.native and not weak.lookup and not weak.talents and not weak.recipes and not weak.receipt)
            assert(lib._sourceItemRequests==itemRequestCache and lib._idCaches==idCaches)
            assert(lib._idFrame==oldIDFrame and lib._eventFrame==oldEventFrame and #mock.frames==2)
            assert(next(lib._sourceItemBuilders)==nil)
            mock.itemNames[123]="needle ID"
            FireEvent("GET_ITEM_INFO_RECEIVED",123,true)
            assert(Query(auditSearch,"123")[1].id==123)
            assert(#mock.errors==0)
        """)

    def test_unregistered_cached_source_does_not_survive_through_weak_key_owner_values(self):
        lua = runtime()
        lua.execute(r"""
            local source={entries={{kind="auditcached",id=1,name="needle",lowerName="needle"}}}
            function source:Build() return self.entries end
            lib:RegisterIndexSource("auditcached",source)
            auditSearch=AuditSearch({"auditcached"})
            Query(auditSearch,"needle")
            weak.source=source;weak.entry=source.entries[1]
            auditSearch:Disable();lib:UnregisterIndexSource("auditcached");auditSearch=nil
        """)
        lua.execute(r"""
            CollectAudit()
            assert(not weak.source and not weak.entry)
            assert(Count(lib._entryOwners)==0 and #mock.errors==0)
        """)


if __name__ == "__main__":
    unittest.main()
