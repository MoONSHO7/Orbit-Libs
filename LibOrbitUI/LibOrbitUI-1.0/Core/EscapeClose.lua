local _, addon = ...
local UI = addon.LibOrbitUI

local ESC_RESTORE_DELAY = 0.05
local attachedFrames = setmetatable({}, { __mode = "k" })

UI.EscapeClose = {}

local function HideFrame(frame)
    frame:Hide()
end

local function HandleKeyDown(frame, key)
    if key ~= "ESCAPE" or InCombatLockdown() then
        return
    end

    frame:SetPropagateKeyboardInput(false)
    C_Timer.After(ESC_RESTORE_DELAY, function()
        if not InCombatLockdown() then
            frame:SetPropagateKeyboardInput(true)
        end
    end)
    attachedFrames[frame](frame)
end

function UI.EscapeClose:Attach(frame, closeCallback)
    assert(frame and type(frame.HookScript) == "function", "LibOrbitUI EscapeClose needs a frame")
    assert(closeCallback == nil or type(closeCallback) == "function", "LibOrbitUI EscapeClose needs a close callback")
    local callback = closeCallback or HideFrame
    local existing = attachedFrames[frame]
    if existing then
        assert(existing == callback, "LibOrbitUI EscapeClose frame already has a different callback")
        return frame
    end

    attachedFrames[frame] = callback
    frame:EnableKeyboard(true)
    frame:SetPropagateKeyboardInput(true)
    frame:HookScript("OnKeyDown", HandleKeyDown)
    return frame
end
