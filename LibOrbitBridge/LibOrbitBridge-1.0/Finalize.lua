-- [ FINALIZE ]---------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitBridge-1.0")
if not lib.__building then
    return
end

lib.__building = false
lib:_DemandChanged()
