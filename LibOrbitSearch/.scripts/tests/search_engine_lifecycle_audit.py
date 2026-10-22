"""Exercise query rebuild cost and retention against the shipped Lua 5.1 engine."""
import unittest

from client_contracts import runtime


class EngineLifecycleAudit(unittest.TestCase):
    def setUp(self):
        self.lua = runtime()

    def test_registered_source_probe_optionally_checks_owner_identity(self):
        self.lua.execute("""
            local first,second={Build=function() return {} end},{Build=function() return {} end}
            assert(not lib:IsIndexSourceRegistered("a"))
            assert(not lib:IsIndexSourceRegistered("a",first))
            lib:RegisterIndexSource("a",first)
            assert(lib:IsIndexSourceRegistered("a") and lib:IsIndexSourceRegistered("a",first))
            assert(not lib:IsIndexSourceRegistered("a",second))
            lib:RegisterIndexSource("a",second)
            assert(lib:IsIndexSourceRegistered("a") and lib:IsIndexSourceRegistered("a",second))
            assert(not lib:IsIndexSourceRegistered("a",first))
            lib:UnregisterIndexSource("a")
            assert(not lib:IsIndexSourceRegistered("a") and not lib:IsIndexSourceRegistered("a",second))
        """)

    def test_invalidated_warm_rebuild_cannot_publish_a_stale_snapshot(self):
        self.lua.execute("""
            local value,invalidate=1,false
            lib:RegisterIndexSource("a",{events={"EVENT_A"},Build=function()
                local captured=value
                if invalidate then invalidate=false;value=3;FireEvent("EVENT_A") end
                return {Entry("a",captured)}
            end})
            local search=Search("a")
            local first=search:Query("needle",options)[1]
            value=2;invalidate=true;FireEvent("EVENT_A")
            assert(#search:Query("needle",options)==0, "warm invalidation published stale data")
            local current=search:Query("needle",options)[1]
            assert(current.id==3 and search:IsEntryCurrent(current))
            assert(not search:IsEntryCurrent(first))
        """)

    def test_retirement_releases_entries_from_closed_and_disabled_search_masters(self):
        self.lua.execute("""
            lib:RegisterIndexSource("a",{events={"EVENT_A"},Build=function() return {Entry("a",1)} end})
            local first,second=Search("a"),Search("a")
            local weak=setmetatable({}, {__mode="v"})
            weak[1]=first:Query("needle",options)[1]
            second:Query("needle",options)
            FireEvent("EVENT_A")
            collectgarbage("collect");collectgarbage("collect")
            assert(weak[1]==nil, "closed searches retained retired entries")
            weak[1]=first:Query("needle",options)[1]
            second:Query("needle",options)
            first:Disable();second:Disable()
            collectgarbage("collect");collectgarbage("collect")
            assert(weak[1]==nil and first._master==nil and second._master==nil)
            assert(next(lib._enabledSearches)==nil and next(lib._openSearches)==nil)
        """)

    def test_dirty_event_burst_uses_one_timer_and_one_rebuild(self):
        self.lua.execute("""
            local builds,updates=0,0
            lib:RegisterIndexSource("a",{events={"EVENT_A"},Build=function()
                builds=builds+1;return {Entry("a",builds)}
            end})
            local search=Search("a",{onIndexUpdated=function() updates=updates+1 end})
            search:SetOpen(true);search:Query("needle",options)
            for i=1,1000 do FireEvent("EVENT_A") end
            assert(#mock.timers==1, "dirty burst created "..#mock.timers.." timers")
            FlushTimers()
            assert(builds==2 and updates==1 and not lib._rebuildTimer)
            assert(next(lib._pendingRebuildKinds)==nil)
            search:Disable();FlushTimers()
            assert(builds==2 and next(lib._eventFrame.events)==nil)
        """)

    def test_transient_source_names_release_metadata_and_do_not_revive_old_entries(self):
        self.lua.execute("""
            local source={Build=function() return {Entry("a",1)} end}
            lib:RegisterIndexSource("a",source)
            local search=Search("a")
            local old=search:Query("needle",options)[1]
            lib:UnregisterIndexSource("a");lib:RegisterIndexSource("a",source)
            local current=search:Query("needle",options)[1]
            assert(current and search:IsEntryCurrent(current) and not search:IsEntryCurrent(old))
            lib:UnregisterIndexSource("a")
            for i=1,1000 do
                local kind="temporary"..i
                lib:SetSourceKeywordTerms(kind,{term="localized"})
                lib:RegisterIndexSource(kind,{Build=function() return {} end})
                lib:UnregisterIndexSource(kind)
            end
            for _,tableName in ipairs({"_kindRevisions","_entries","_sourceStates","_buildCounts",
                "_dirty","_built","_indexSources","_sourceKeywordTerms","_pendingRebuildKinds"}) do
                assert(next(lib[tableName])==nil, tableName.." retains unregistered sources")
            end
        """)

    def test_thousand_rebuilds_keep_only_current_entries_and_one_warm_index(self):
        self.lua.execute("""
            local builds=0
            lib:RegisterIndexSource("a",{events={"EVENT_A"},Build=function()
                builds=builds+1
                local entries={}
                for i=1,100 do entries[i]=Entry("a",i) end
                return entries
            end})
            local search=Search("a")
            for i=1,1000 do
                search:Query("needle",options)
                FireEvent("EVENT_A")
            end
            collectgarbage("collect");collectgarbage("collect")
            assert(next(lib._entryOwners)==nil)
            assert(#lib._entries.a==0 and builds==1000)
            search:Query("needle",options)
            for i=1,1000 do search:Query("needle",options) end
            assert(builds==1001)
            local owners=0
            for _ in pairs(lib._entryOwners) do owners=owners+1 end
            assert(owners==100)
        """)


if __name__ == "__main__":
    unittest.main()
