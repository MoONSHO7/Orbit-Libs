local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = {}
local ITEM_REQUEST_CAPACITY = 256
local ITEM_REQUEST_TIMEOUT = 30
lib._NativeContract = Native
lib._sourceItemRequests = lib._sourceItemRequests or lib._BoundedCache.Create(ITEM_REQUEST_CAPACITY)

function Native.Require(namespace, ...)
    for index = 1, select("#", ...) do
        local name = select(index, ...)
        if not namespace or type(namespace[name]) ~= "function" then
            return "unsupported", "missing:" .. name
        end
    end
    return "ready"
end

function Native.IsEventValid(event)
    return C_EventUtils and C_EventUtils.IsEventValid and C_EventUtils.IsEventValid(event) == true
end

function Native.RequestItem(itemID)
    if C_Item and C_Item.RequestLoadItemDataByID then
        local requested = lib._sourceItemRequests:Get(itemID)
        if not requested or time() - requested >= ITEM_REQUEST_TIMEOUT then
            lib._sourceItemRequests:Set(itemID, time())
            C_Item.RequestLoadItemDataByID(itemID)
        end
    end
end

table.freeze(Native)
