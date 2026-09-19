-- [ BOUNDED CACHE ]----------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local CacheMixin = {}
local CacheMeta = { __index = CacheMixin }

local function Detach(cache, entry)
    if entry.previous then
        entry.previous.next = entry.next
    else
        cache.first = entry.next
    end
    if entry.next then
        entry.next.previous = entry.previous
    else
        cache.last = entry.previous
    end
    entry.previous, entry.next = nil, nil
end

local function Touch(cache, entry)
    if cache.last == entry then
        return
    end
    Detach(cache, entry)
    entry.previous = cache.last
    if cache.last then
        cache.last.next = entry
    else
        cache.first = entry
    end
    cache.last = entry
end

function CacheMixin:Get(key)
    local entry = self.entries[key]
    if entry then
        Touch(self, entry)
        return entry.value
    end
end

function CacheMixin:Set(key, value)
    local entry = self.entries[key]
    if entry then
        entry.value = value
        Touch(self, entry)
        return
    end
    if self.count == self.capacity then
        entry = self.first
        self.entries[entry.key] = nil
        Detach(self, entry)
    else
        entry = {}
        self.count = self.count + 1
    end
    entry.key, entry.value, entry.previous = key, value, self.last
    if self.last then
        self.last.next = entry
    else
        self.first = entry
    end
    self.last = entry
    self.entries[key] = entry
end

function CacheMixin:Remove(key)
    local entry = self.entries[key]
    if not entry then
        return
    end
    Detach(self, entry)
    self.entries[key] = nil
    self.count = self.count - 1
end

table.freeze(CacheMixin)

lib._BoundedCache = {
    Create = function(capacity)
        return setmetatable({ entries = {}, count = 0, capacity = capacity }, CacheMeta)
    end,
}
