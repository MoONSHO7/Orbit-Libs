-- [ MATCHER ]----------------------------------------------------------------------------------------------------------
local lib = LibStub("LibOrbitSearch-1.0")
if not lib.__building then
    return
end

local string_find = string.find
local string_len = string.len
local math_max = math.max
local math_min = math.min
local table_sort = table.sort
local table_insert = table.insert

-- [ CONSTANTS ]--------------------------------------------------------------------------------------------------------
local SCORE_ID_EXACT = 1200
local SCORE_ID_PREFIX = 600
local SCORE_EXACT = 1000
local SCORE_PREFIX = 500
local SCORE_WORD_START = 250
local SCORE_SUBSTRING = 125
local SCORE_CATEGORY = 100
-- Length bonuses plus the maximum 65-point boost must stay inside each match band.
local SCORE_LENGTH_BONUS = 50
local FUZZY_MAX_GAPS = 3
local FUZZY_GAP_WEIGHT = 4
local FUZZY_SCORE_BASE = 50
local SCORE_FAVORITE = 15
local SCORE_RECENT_BASE = 40
local SCORE_RECENT_STEP = 5
local TIER_ID_EXACT = 6
local TIER_EXACT = 5
local TIER_PREFIX = 4
local TIER_WORD_START = 3
local TIER_SUBSTRING = 2
local TIER_FUZZY = 1
local TIER_CATEGORY = TIER_WORD_START
local CATEGORY_MIN_PREFIX = 3
local CATEGORY_DIVERGENT_TAIL = 1
local DEFAULT_MAX_RESULTS = 25

local Matcher = {}
lib._Matcher = Matcher

-- [ CATEGORY TOKENS ]--------------------------------------------------------------------------------------------------
local function EnsureCategoryTokens(search)
    if search._categoryTokens then
        return search._categoryTokens
    end
    local tokens, aliases, keywordOnly = {}, {}, {}
    for _, row in ipairs(search._rows) do
        if search:IsKindListed(row) then
            if not row.noToken then
                tokens[row.kind] = row.kind
                local label = search:GetKindLabel(row.kind)
                if label then
                    tokens[lib.Fold(label)] = row.kind
                end
            end
            for _, alias in ipairs(row.aliases or {}) do
                aliases[lib.Fold(alias)] = row.kind
            end
            if row.keywordOnly then
                keywordOnly[row.kind] = true
            end
        end
    end
    search._categoryTokens, search._aliasExact, search._keywordOnlyKinds = tokens, aliases, keywordOnly
    return tokens
end

local function LongestCommonPrefix(a, b)
    local n = math_min(#a, #b)
    for i = 1, n do
        if a:byte(i) ~= b:byte(i) then
            return i - 1
        end
    end
    return n
end

local function MatchToken(search, word, requireMultiWordToken)
    local tokens = EnsureCategoryTokens(search)
    if tokens[word] then
        return tokens[word], false
    end
    if search._aliasExact[word] then
        return search._aliasExact[word], false
    end
    if #word < CATEGORY_MIN_PREFIX then
        return nil
    end
    local winner, bestLCP, ambiguous = nil, 0, false
    for token, kind in pairs(tokens) do
        if not requireMultiWordToken or token:find(" ", 1, true) then
            local lcp = LongestCommonPrefix(word, token)
            if lcp >= CATEGORY_MIN_PREFIX and #word <= lcp + CATEGORY_DIVERGENT_TAIL then
                if lcp > bestLCP then
                    winner, bestLCP, ambiguous = kind, lcp, false
                elseif lcp == bestLCP and winner ~= kind then
                    ambiguous = true
                end
            end
        end
    end
    if ambiguous then
        return nil
    end
    return winner, winner ~= nil
end

local function SplitWords(query)
    local words = {}
    for word in query:gmatch("%S+") do
        words[#words + 1] = word
    end
    return words
end

local function Consume(words, first, last, kind, partial)
    local rest, consumed = {}, {}
    for j = 1, #words do
        if j >= first and j <= last then
            consumed[j] = true
        else
            rest[#rest + 1] = words[j]
        end
    end
    return kind, table.concat(rest, " "), partial, consumed
end

local function ExtractCategoryPrefix(search, words)
    for i = 1, #words - 1 do
        local kind, partial = MatchToken(search, words[i] .. " " .. words[i + 1], true)
        if kind then
            return Consume(words, i, i + 1, kind, partial)
        end
    end
    for i = 1, #words do
        local kind, partial = MatchToken(search, words[i])
        if kind then
            return Consume(words, i, i, kind, partial)
        end
    end
    return nil
end

-- [ PARSE ]------------------------------------------------------------------------------------------------------------
function Matcher.Parse(search, query, ignoreCategory)
    local words = SplitWords(query)
    local parsed = { query = query, words = words, consumed = {}, nameQuery = query }
    if not ignoreCategory then
        local kind, rest, partial, consumed = ExtractCategoryPrefix(search, words)
        if kind then
            parsed.kindFilter, parsed.nameQuery, parsed.partial, parsed.consumed = kind, rest, partial, consumed
        end
    end
    local nameWords = SplitWords(parsed.nameQuery ~= "" and parsed.nameQuery or query)
    parsed.digits = #nameWords == 1 and nameWords[1]:match("^%d+$") or nil
    return parsed
end

-- [ SCORING ]----------------------------------------------------------------------------------------------------------
-- Memoized outside the entry tables so sources that persist their entries never write the cache out.
local idStrings = {}

local function ScoreEntryID(search, digits, entry)
    local id = search:EntryID(entry)
    if not id then
        return 0
    end
    local text = idStrings[id]
    if not text then
        text = tostring(id)
        idStrings[id] = text
    end
    if text == digits then
        return SCORE_ID_EXACT, TIER_ID_EXACT
    end
    if string_find(text, digits, 1, true) == 1 then
        return SCORE_ID_PREFIX + math_max(0, SCORE_LENGTH_BONUS - string_len(text)), TIER_PREFIX
    end
    return 0
end

local function ScoreFuzzy(query, qlen, name)
    local gaps = 0
    local cursor = 1
    local nlen = string_len(name)
    for i = 1, qlen do
        local ch = string.byte(query, i)
        local found
        for j = cursor, nlen do
            if string.byte(name, j) == ch then
                if j > cursor then
                    gaps = gaps + (j - cursor)
                end
                cursor = j + 1
                found = true
                break
            end
        end
        if not found or gaps > FUZZY_MAX_GAPS * FUZZY_GAP_WEIGHT then
            return 0
        end
    end
    return FUZZY_SCORE_BASE - gaps, TIER_FUZZY
end

local function ScoreEntry(query, qlen, entry, fuzzy)
    local name = entry.lowerName
    if not name or name == "" then
        return 0
    end
    if name == query then
        return SCORE_EXACT, TIER_EXACT
    end
    local ps = string_find(name, query, 1, true)
    if ps == 1 then
        return SCORE_PREFIX + math_max(0, SCORE_LENGTH_BONUS - string_len(name)), TIER_PREFIX
    end
    if ps then
        local prev = string.sub(name, ps - 1, ps - 1)
        if prev == " " or prev == "-" or prev == "'" then
            return SCORE_WORD_START + math_max(0, SCORE_LENGTH_BONUS - string_len(name)), TIER_WORD_START
        end
        return SCORE_SUBSTRING + math_max(0, SCORE_LENGTH_BONUS - string_len(name)), TIER_SUBSTRING
    end
    if fuzzy and qlen > 1 then
        return ScoreFuzzy(query, qlen, name)
    end
    return 0
end

local function ApplyBoosts(score, entry, recentBoost)
    score = score + (entry.sourcePriority or 0)
    if entry.favorite then
        score = score + SCORE_FAVORITE
    end
    local position = recentBoost[entry.kind .. ":" .. tostring(entry.id)]
    if position then
        score = score + SCORE_RECENT_BASE - (position - 1) * SCORE_RECENT_STEP
    end
    return score
end

local function KindPasses(search, entryKind, kindFilter, enabledKinds)
    if not enabledKinds[entryKind] then
        return false
    end
    if kindFilter then
        return entryKind == kindFilter
    end
    return not search._keywordOnlyKinds[entryKind]
end

-- [ QUERY ]------------------------------------------------------------------------------------------------------------
function Matcher.Query(search, entries, parsed, enabledKinds, options, recentBoost)
    local out, tiers = {}, {}
    if parsed.query == "" then
        return out, tiers
    end
    EnsureCategoryTokens(search)

    local kindFilter, nameQuery = parsed.kindFilter, parsed.nameQuery
    local hidePassives = options.hidePassives
    local results = {}
    if kindFilter and nameQuery == "" then
        for i = 1, #entries do
            local entry = entries[i]
            if entry.kind == kindFilter and enabledKinds[entry.kind] and not (hidePassives and entry.passive) then
                table_insert(results, {
                    entry = entry,
                    score = ApplyBoosts(SCORE_CATEGORY, entry, recentBoost),
                    tier = TIER_CATEGORY,
                })
            end
        end
    else
        local queryWords = SplitWords(nameQuery ~= "" and nameQuery or parsed.query)
        if #queryWords == 0 then
            return out, tiers
        end
        local digits = parsed.digits
        for i = 1, #entries do
            local entry = entries[i]
            if
                KindPasses(search, entry.kind, kindFilter, enabledKinds)
                and not (hidePassives and entry.passive and not digits)
            then
                local score, tier = 0, nil
                if digits then
                    score, tier = ScoreEntryID(search, digits, entry)
                end
                if score == 0 then
                    for _, word in ipairs(queryWords) do
                        local wordScore, wordTier = ScoreEntry(word, #word, entry, options.fuzzy)
                        if wordScore == 0 then
                            score = 0
                            break
                        end
                        score = score + wordScore
                        tier = tier and math_min(tier, wordTier) or wordTier
                    end
                end
                if score > 0 then
                    table_insert(
                        results,
                        { entry = entry, score = ApplyBoosts(score, entry, recentBoost), tier = tier }
                    )
                end
            end
        end
    end

    local priority = search._priority
    table_sort(results, function(a, b)
        if a.score ~= b.score then
            return a.score > b.score
        end
        local pa = priority[a.entry.kind] or 0
        local pb = priority[b.entry.kind] or 0
        if pa ~= pb then
            return pa > pb
        end
        return a.entry.lowerName < b.entry.lowerName
    end)

    local limit = math_min(options.maxResults or DEFAULT_MAX_RESULTS, #results)
    for i = 1, limit do
        out[i] = results[i].entry
        tiers[i] = results[i].tier
    end
    return out, tiers
end
