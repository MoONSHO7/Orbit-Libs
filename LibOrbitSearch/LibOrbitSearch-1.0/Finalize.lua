-- [ FINALIZE ]---------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

for search in pairs(lib._searches) do
    lib._ProviderSessions.Adopt(search)
end
lib.__building = false
lib:_RefreshEventRegistration()
lib:_NotifySourcesChanged()
