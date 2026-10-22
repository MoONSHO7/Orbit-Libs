"""Verify source-owned synchronous event filtering without hiding external invalidation."""
import unittest

import client_contracts


class SourceEventFilters(unittest.TestCase):
    def setUp(self):
        self.lua = client_contracts.runtime()

    def test_temporary_native_enumeration_does_not_retire_its_own_build(self):
        self.lua.execute("""
            local source={events={"SKILL_LINES_CHANGED"},builds=0}
            function source:ShouldInvalidate(event)
                return not (self.enumerating and event=="SKILL_LINES_CHANGED")
            end
            function source:Build()
                self.builds=self.builds+1
                self.enumerating=true;FireEvent("SKILL_LINES_CHANGED");self.enumerating=false
                return {Entry("skills",1)}
            end
            lib:RegisterIndexSource("skills",source)
            local search=Search("skills")
            local first=search:Query("needle",options)[1]
            assert(first and search:IsEntryCurrent(first) and source.builds==1)
            assert(search:Query("needle",options)[1]==first and source.builds==1)
            FireEvent("SKILL_LINES_CHANGED")
            assert(not search:IsEntryCurrent(first))
            local second=search:Query("needle",options)[1]
            assert(second~=first and source.builds==2)
        """)

    def test_filter_is_local_to_its_source(self):
        self.lua.execute("""
            lib:RegisterIndexSource("skills",{events={"SKILL_LINES_CHANGED"},
                ShouldInvalidate=function() return false end,Build=function() return {Entry("skills",1)} end})
            lib:RegisterIndexSource("professions",{events={"SKILL_LINES_CHANGED"},
                Build=function() return {Entry("professions",2)} end})
            local skills,professions=Search("skills"),Search("professions")
            local a=skills:Query("needle",options)[1]
            local b=professions:Query("needle",options)[1]
            FireEvent("SKILL_LINES_CHANGED")
            assert(skills:IsEntryCurrent(a) and not professions:IsEntryCurrent(b))
        """)

    def test_throwing_external_filter_reports_and_invalidates(self):
        self.lua.execute("""
            lib:RegisterIndexSource("skills",{events={"SKILL_LINES_CHANGED"},
                ShouldInvalidate=function() error("filter failure") end,
                Build=function() return {Entry("skills",1)} end})
            local search=Search("skills")
            local first=search:Query("needle",options)[1]
            FireEvent("SKILL_LINES_CHANGED")
            assert(not search:IsEntryCurrent(first) and #mock.errors==1)
            assert(mock.errors[1]:find("ShouldInvalidate",1,true))
        """)

    def test_removed_event_sources_do_not_dispatch_or_throw(self):
        self.lua.execute("""
            for _,kind in ipairs({"a","b"}) do
                lib:RegisterIndexSource(kind,{events={"SKILL_LINES_CHANGED"},
                    ShouldInvalidate=function()
                        lib:UnregisterIndexSource(kind=="a" and "b" or "a")
                        return false
                    end,
                    Build=function() return {Entry(kind,1)} end})
                Search(kind):Query("needle",options)
            end
            FireEvent("SKILL_LINES_CHANGED")
            assert(#mock.errors==0)
            assert(lib:IsIndexSourceRegistered("a")~=lib:IsIndexSourceRegistered("b"))
        """)

    def test_replacement_built_in_filter_is_not_dirtied_by_old_callback(self):
        self.lua.execute("""
            local search=Search("skills")
            lib:RegisterIndexSource("skills",{events={"SKILL_LINES_CHANGED"},
                ShouldInvalidate=function()
                    lib:RegisterIndexSource("skills",{Build=function() return {Entry("skills",2)} end})
                    search:Query("needle",options)
                    return true
                end,Build=function() return {Entry("skills",1)} end})
            search:Query("needle",options)
            FireEvent("SKILL_LINES_CHANGED")
            assert(lib._entries.skills[1].id==2 and not lib._dirty.skills)
        """)

    def test_localized_terms_invalidate_only_the_named_source_and_copy_inputs(self):
        self.lua.execute("""
            lib:RegisterIndexSource("talents",{Build=function()
                local entry=Entry("talents",1)
                entry.lowerName=lib._sourceKeywordTerms.talents.learned
                return {entry}
            end})
            local terms={learned="learned"}
            lib:SetSourceKeywordTerms("talents",terms)
            terms.learned="changed"
            local search=Search("talents")
            local first=search:Query("learned",options)[1]
            assert(first)
            lib:SetSourceKeywordTerms("talents",{learned="appris"})
            assert(not search:IsEntryCurrent(first))
            assert(search:Query("appris",options)[1])
        """)

    def test_expiry_probe_retries_pending_only_after_its_deadline(self):
        self.lua.execute("""
            local now,ready=0,false
            local source={builds=0}
            function source:IsExpired() return self.deadline and now>=self.deadline end
            function source:Build()
                self.builds=self.builds+1
                if not ready then self.deadline=now+30;return nil,"pending","data" end
                self.deadline=nil
                return {Entry("talents",1)}
            end
            lib:RegisterIndexSource("talents",source)
            local search=Search("talents")
            assert(#search:Query("needle",options)==0 and source.builds==1)
            now=29;search:Query("needle",options);assert(source.builds==1)
            now=30;ready=true
            assert(search:Query("needle",options)[1] and source.builds==2)
            now=100;search:Query("needle",options);assert(source.builds==2)
        """)

    def test_expiry_probe_removal_does_not_build_a_missing_source(self):
        self.lua.execute("""
            lib:RegisterIndexSource("talents",{
                IsExpired=function() lib:UnregisterIndexSource("talents");return true end,
                Build=function() return {Entry("talents",1)} end})
            local search=Search("talents")
            assert(search:Query("needle",options)[1])
            assert(#search:Query("needle",options)==0 and #mock.errors==0)
        """)

    def test_unavailable_source_does_not_repeat_expired_work(self):
        self.lua.execute("""
            local available,probes=true,0
            lib:RegisterIndexSource("talents",{
                GetAvailability=function() return available and "ready" or "pending","config" end,
                IsExpired=function() probes=probes+1;return true end,
                Build=function() return {Entry("talents",1)} end})
            local search=Search("talents")
            assert(search:Query("needle",options)[1])
            available=false
            search:Query("needle",options)
            local revision=lib._kindRevisions.talents
            search:Query("needle",options)
            assert(probes==0 and lib._kindRevisions.talents==revision)
            available=true
            assert(search:Query("needle",options)[1])
        """)


if __name__ == "__main__":
    unittest.main()
