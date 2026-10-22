local _, addon = ...
local UI = addon.LibOrbitUI

local ESC_RESTORE_DELAY = 0.05
local INPUT_TEMPLATE = "InsecureKeyboardInputPropagatorTemplate"
local INPUT_LEVEL_OFFSET = 1
local attachedFrames = setmetatable({}, { __mode = "k" })

UI.EscapeClose = {}

local function HideFrame(frame)
    frame:Hide()
end

local function SyncInputDepth(record)
    if InCombatLockdown() then
        record.input:Hide()
        return
    end
    record.input:SetFrameStrata(record.frame:GetFrameStrata())
    record.input:SetFrameLevel(record.frame:GetFrameLevel() + INPUT_LEVEL_OFFSET)
end

local function RefreshInput(record)
    local frame, input = record.frame, record.input
    if InCombatLockdown() or not frame:IsVisible() then
        input:Hide()
        return
    end

    input:SetPropagateKeyboardInput(true)
    if not record.armed then
        input:EnableKeyboard(true)
        record.armed = true
    end
    SyncInputDepth(record)
    input:Show()
end

local function HandleKeyDown(record, key)
    if InCombatLockdown() or not record.frame:IsVisible() then
        record.input:Hide()
        return
    end
    if key ~= "ESCAPE" then
        record.input:SetPropagateKeyboardInput(true)
        return
    end

    record.input:SetPropagateKeyboardInput(false)
    if not record.restorePending then
        record.restorePending = true
        C_Timer.After(ESC_RESTORE_DELAY, function()
            record.restorePending = false
            RefreshInput(record)
        end)
    end
    record.callback(record.frame)
end

function UI.EscapeClose:Attach(frame, closeCallback)
    assert(frame and type(frame.HookScript) == "function", "LibOrbitUI EscapeClose needs a frame")
    assert(closeCallback == nil or type(closeCallback) == "function", "LibOrbitUI EscapeClose needs a close callback")
    local callback = closeCallback or HideFrame
    local existing = attachedFrames[frame]
    if existing then
        assert(existing.callback == callback, "LibOrbitUI EscapeClose frame already has a different callback")
        return frame
    end

    -- Keep input outside the window's protected ancestry so combat can always hide a consumed Escape.
    local input = CreateFrame("Frame", nil, UIParent, INPUT_TEMPLATE)
    input:Hide()
    local record = { frame = frame, input = input, callback = callback }
    attachedFrames[frame] = record
    input:SetScript("OnKeyDown", function(_, key)
        HandleKeyDown(record, key)
    end)
    input:RegisterEvent("PLAYER_REGEN_DISABLED")
    input:RegisterEvent("PLAYER_REGEN_ENABLED")
    input:SetScript("OnEvent", function(_, event)
        if event == "PLAYER_REGEN_DISABLED" then
            input:Hide()
        else
            RefreshInput(record)
        end
    end)
    frame:HookScript("OnShow", function()
        RefreshInput(record)
    end)
    frame:HookScript("OnHide", function()
        input:Hide()
    end)
    local syncDepth = UI.Callbacks:Wrap(function()
        SyncInputDepth(record)
    end, "EscapeClose.SyncInputDepth")
    hooksecurefunc(frame, "Raise", syncDepth)
    hooksecurefunc(frame, "Lower", syncDepth)
    hooksecurefunc(frame, "SetFrameLevel", syncDepth)
    hooksecurefunc(frame, "SetFrameStrata", syncDepth)
    RefreshInput(record)
    return frame
end
