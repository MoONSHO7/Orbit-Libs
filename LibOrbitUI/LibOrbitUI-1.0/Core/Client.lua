local _, addon = ...
local UI = addon.LibOrbitUI
local RETAIL_MAJOR = 12
local FOREVER_MAJOR, FOREVER_MINOR = 1, 60
local LEGACY_ADDON = "Blizzard_LegacySystem"

local version, build, _, interface = GetBuildInfo()
local major, minor = version:match("^(%d+)%.(%d+)%.")
major, minor = tonumber(major), tonumber(minor)
local legacyExists = C_AddOns and C_AddOns.DoesAddOnExist and C_AddOns.DoesAddOnExist(LEGACY_ADDON)
local family, reason = "unknown", "unrecognized-version"
if major == RETAIL_MAJOR then
    if legacyExists == true then
        reason = "conflicting-client-signals"
    else
        family, reason = "retail", "version-signature"
    end
elseif major == FOREVER_MAJOR and minor == FOREVER_MINOR then
    family, reason = "forever", legacyExists and "version-and-addon" or "version-signature"
end

UI.Client = table.freeze({
    family = family,
    reason = reason,
    version = version,
    build = build,
    interface = interface,
    legacyAddonExists = legacyExists,
})
