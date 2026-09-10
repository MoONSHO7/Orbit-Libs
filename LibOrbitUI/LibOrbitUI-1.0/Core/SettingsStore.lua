local _, addon = ...
local UI = addon.LibOrbitUI
local STORE_VERSION = 1
local MAX_DEPTH = 32
local MAX_VALUES = 100000

UI.SettingsStore = {}
local StoreMixin = {}
local CollectionMixin = {}

local function Validate(value, visiting, depth, budget)
    if issecretvalue(value) then
        return false
    end
    local kind = type(value)
    if kind == "number" then
        return value == value and value > -math.huge and value < math.huge
    end
    if kind ~= "table" then
        return kind == "nil" or kind == "boolean" or kind == "string"
    end
    if depth >= MAX_DEPTH or visiting[value] or getmetatable(value) ~= nil then
        return false
    end
    visiting[value] = true
    for key, child in pairs(value) do
        budget.count = budget.count + 1
        if budget.count > MAX_VALUES or issecretvalue(key) then
            return false
        end
        local keyType = type(key)
        if (keyType ~= "string" and keyType ~= "number") or not Validate(key, visiting, depth + 1, budget) then
            return false
        end
        if not Validate(child, visiting, depth + 1, budget) then
            return false
        end
    end
    visiting[value] = nil
    return true
end

local function ValidData(value)
    return Validate(value, {}, 0, { count = 0 })
end

local function Copy(value)
    if type(value) ~= "table" then
        return value
    end
    local copy = {}
    for key, child in pairs(value) do
        copy[key] = Copy(child)
    end
    return copy
end

local function Index(index)
    if issecretvalue(index) then
        return nil
    end
    if type(index) ~= "number" then
        return 1
    end
    if index >= 1 and index < math.huge and index % 1 == 0 then
        return index
    end
end

local function Default(self, index, key)
    local indexed = self.indexDefaults[index]
    if indexed and indexed[key] ~= nil then
        return indexed[key]
    end
    return self.defaults[key]
end

local function ValidSetting(self, index, key, value)
    if type(key) ~= "string" or issecretvalue(key) then
        return false
    end
    local default = Default(self, index, key)
    if default == nil or not ValidData(value) then
        return false
    end
    if value == nil then
        return true
    end
    local valueType = self.valueTypes[key]
    if valueType then
        return value == false or type(value) == valueType
    end
    if key == "Position" and (default == false or type(default) == "table") then
        return value == false or type(value) == "table"
    end
    return type(value) == type(default)
end

function StoreMixin:Initialize(data)
    if issecretvalue(data) then
        return nil, "Malformed LibOrbitUI settings root"
    end
    if data == nil then
        data = { version = STORE_VERSION, settings = {}, collections = {} }
    end
    if not ValidData(data) or type(data) ~= "table" then
        return nil, "Malformed LibOrbitUI settings root"
    end
    if data.version ~= STORE_VERSION then
        return nil, "Unsupported LibOrbitUI settings version"
    end
    if type(data.settings) ~= "table" or type(data.collections) ~= "table" then
        return nil, "Malformed LibOrbitUI settings root"
    end
    for key in pairs(data) do
        if key ~= "version" and key ~= "settings" and key ~= "collections" then
            return nil, "Unknown LibOrbitUI settings root field"
        end
    end
    for index, settings in pairs(data.settings) do
        if type(index) ~= "number" or not Index(index) or type(settings) ~= "table" then
            return nil, "Malformed LibOrbitUI settings entry"
        end
        for key, value in pairs(settings) do
            if not ValidSetting(self, index, key, value) then
                return nil, "Invalid or undeclared LibOrbitUI setting"
            end
        end
    end
    for name, collection in pairs(data.collections) do
        if
            type(name) ~= "string"
            or name == ""
            or type(collection) ~= "table"
            or type(collection.records) ~= "table"
        then
            return nil, "Malformed LibOrbitUI settings collection"
        end
        for id, record in pairs(collection.records) do
            if type(record) ~= "table" or record.id ~= id then
                return nil, "Malformed LibOrbitUI collection record"
            end
        end
    end
    self.data = data
    return data
end

function StoreMixin:Get(index, key)
    index = Index(index)
    assert(index, "LibOrbitUI setting index must be a positive integer")
    assert(self.data, "LibOrbitUI settings store is not initialized")
    local settings = self.data.settings[index]
    local value = settings and settings[key]
    if value == nil then
        value = Default(self, index, key)
    end
    return Copy(value)
end

function StoreMixin:Set(index, key, value)
    index = Index(index)
    if not index or not ValidSetting(self, index, key, value) then
        return nil, "Invalid or undeclared LibOrbitUI setting"
    end
    assert(self.data, "LibOrbitUI settings store is not initialized")
    local settings = self.data.settings[index]
    if not settings then
        settings = {}
        self.data.settings[index] = settings
    end
    settings[key] = Copy(value)
    return true
end

function CollectionMixin:Records()
    assert(self.owner.data, "LibOrbitUI settings store is not initialized")
    local collection = self.owner.data.collections[self.name]
    return collection and collection.records or {}
end

function CollectionMixin:Get(id)
    return self:Records()[id]
end

function CollectionMixin:Insert(record)
    if not ValidData(record) or type(record) ~= "table" or record.id == nil then
        return nil, "Invalid LibOrbitUI collection record"
    end
    local idType = type(record.id)
    if idType ~= "string" and idType ~= "number" then
        return nil, "Invalid LibOrbitUI collection record ID"
    end
    assert(self.owner.data, "LibOrbitUI settings store is not initialized")
    local collection = self.owner.data.collections[self.name]
    if not collection then
        collection = { records = {} }
        self.owner.data.collections[self.name] = collection
    end
    collection.records[record.id] = record
    return record
end

function CollectionMixin:Remove(id)
    self:Records()[id] = nil
end

function StoreMixin:Collection(name)
    assert(type(name) == "string" and name ~= "", "LibOrbitUI collection name is required")
    if not self.collections[name] then
        self.collections[name] = Mixin({ owner = self, name = name }, CollectionMixin)
    end
    return self.collections[name]
end

table.freeze(CollectionMixin)
table.freeze(StoreMixin)

function UI.SettingsStore:Create(defaults, indexDefaults, valueTypes)
    return Mixin({
        defaults = defaults or {},
        indexDefaults = indexDefaults or {},
        valueTypes = valueTypes or {},
        collections = {},
    }, StoreMixin)
end
