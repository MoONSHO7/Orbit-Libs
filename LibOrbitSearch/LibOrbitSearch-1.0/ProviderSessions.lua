-- [ PROVIDER SESSIONS ]------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local EMPTY = {}
table.freeze(EMPTY)

local Sessions = {}
lib._ProviderSessions = Sessions

local function InvalidateSession(session)
    if not session.open or not session.ready then
        return
    end
    local ok, err = pcall(session.onInvalidate)
    if not ok then
        lib:_Report(err)
    end
end

local function CloseSession(session)
    if not session.open then
        return
    end
    session.open = false
    lib:_CallProviderOwner(session.providerOwner, session.providerKey, "EndSession", session)
end

local function BeginSession(search, kind, provider, key)
    local session = {
        kind = kind,
        providerOwner = provider,
        providerKey = key,
        generation = search._sessionGeneration,
        open = true,
        ready = false,
        onInvalidate = search._sessionCallback,
        Invalidate = InvalidateSession,
    }
    search._sessions[kind] = session
    session.ready = lib:_CallProviderOwner(provider, key, "BeginSession", session)
    if not session.ready then
        -- Keep the failed attempt until the next session or availability change, avoiding retries on every keystroke.
        CloseSession(session)
    end
end

function Sessions.Reconcile(search)
    if search._reconcilingSessions then
        search._sessionsNeedReconcile = true
        return
    end
    search._reconcilingSessions = true
    repeat
        search._sessionsNeedReconcile = nil
        local enabled = search._sessionCallback and search:GetEnabledKinds() or EMPTY
        for kind, session in pairs(search._sessions) do
            local provider = lib:GetProvider(kind)
            if
                not enabled[kind]
                or provider ~= session.providerOwner
                or session.generation ~= search._sessionGeneration
            then
                search._sessions[kind] = nil
                CloseSession(session)
            end
        end
        for _, row in ipairs(search._rows) do
            if not search._sessionCallback then
                break
            end
            if row.provider and enabled[row.kind] and not search._sessions[row.kind] then
                local provider, key = lib:GetProvider(row.kind)
                if provider then
                    BeginSession(search, row.kind, provider, key)
                end
            end
        end
    until not search._sessionsNeedReconcile
    search._reconcilingSessions = nil
end

function Sessions.Begin(search, onInvalidate)
    search._sessionGeneration = (search._sessionGeneration or 0) + 1
    Sessions.End(search)
    search._sessionCallback = onInvalidate
    Sessions.Reconcile(search)
end

function Sessions.End(search)
    search._sessionCallback = nil
    -- A provider may close the search inside BeginSession; let it finish acquiring before releasing its resources.
    Sessions.Reconcile(search)
end

function Sessions.Adopt(search)
    -- Revision 1 sessions resolved their provider by kind; capture that owner before reconciling the installed copy.
    for kind, session in pairs(search._sessions) do
        if not session.providerOwner then
            session.providerOwner, session.providerKey = lib:GetProvider(kind)
            session.ready = session.open
            session.generation = search._sessionGeneration
            search._sessionCallback = session.onInvalidate
        end
        session.Invalidate = InvalidateSession
        if not session.providerOwner then
            session.open = false
            search._sessions[kind] = nil
        end
    end
    if lib._openSearches[search] and not search._sessionCallback then
        search._sessionCallback = search._config.onIndexUpdated
    end
end
