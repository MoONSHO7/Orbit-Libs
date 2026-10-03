local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local Native = {}
local ITEM_REQUEST_CAPACITY = 256
local ITEM_REQUEST_TIMEOUT = 30
lib._NativeContract = Native
lib._sourceItemRequests = lib._sourceItemRequests or lib._BoundedCache.Create(ITEM_REQUEST_CAPACITY)
lib._sourceItemPending = lib._sourceItemPending or {}
lib._sourceItemBuilders = {}

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

function Native.ClearItems(kind)
    lib._sourceItemPending[kind] = nil
end

function Native.BeginBuild(kind, source)
    Native.ClearItems(kind)
    local build = { kind = kind, source = source, revision = lib._kindRevisions[kind] or 0 }
    lib._sourceItemBuilders[kind] = build
    return build
end

function Native.EndBuild(build, published)
    local kind = build.kind
    if lib._sourceItemBuilders[kind] == build then
        lib._sourceItemBuilders[kind] = nil
    end
    if lib._sourceItemPending[kind] == build then
        if published then
            build.revision = lib._kindRevisions[kind] or 0
        else
            Native.ClearItems(kind)
        end
    end
end

function Native.RequestItem(source, itemID)
    local build = lib._sourceItemBuilders[source.kind]
    if
        not build
        or build.source ~= source
        or lib._indexSources[source.kind] ~= source
        or build.revision ~= (lib._kindRevisions[source.kind] or 0)
        or not C_Item
        or not C_Item.RequestLoadItemDataByID
    then
        return
    end
    local now = time()
    local requested = lib._sourceItemRequests:Get(itemID)
    local request = not requested or now - requested >= ITEM_REQUEST_TIMEOUT
    requested = request and now or requested
    build.items = build.items or lib._BoundedCache.Create(ITEM_REQUEST_CAPACITY)
    build.items:Set(itemID, requested)
    build.retryAt = math.min(build.retryAt or math.huge, requested + ITEM_REQUEST_TIMEOUT)
    lib._sourceItemPending[source.kind] = build
    if request then
        -- Publish the receipt first: native item completion can invalidate this build synchronously.
        lib._sourceItemRequests:Set(itemID, requested)
        C_Item.RequestLoadItemDataByID(itemID)
    end
end

function Native.ItemDataReceived(kind, itemID, success)
    local pending = lib._sourceItemPending[kind]
    if
        not pending
        or pending.source ~= lib._indexSources[kind]
        or pending.revision ~= (lib._kindRevisions[kind] or 0)
        or not pending.items:Get(itemID)
        or not success
    then
        return false
    end
    pending.items:Remove(itemID)
    return true
end

function Native.ItemsExpired(kind)
    local pending = lib._sourceItemPending[kind]
    return pending ~= nil and pending.retryAt <= time()
end

table.freeze(Native)
