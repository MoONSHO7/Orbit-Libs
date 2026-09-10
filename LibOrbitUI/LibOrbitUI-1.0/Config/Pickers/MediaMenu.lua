local _, addon = ...
local Provider = {}
addon.LibOrbitUI.MediaMenu = Provider

local strfind, strlower = string.find, string.lower
local tinsert, tsort = table.insert, table.sort
local math_floor, math_max, math_min = math.floor, math.max, math.min

local POPUP_WIDTH = 230
local PAD = 5
local SEARCH_HEIGHT = 26
local AUTO_CLOSE_DELAY = 0.2
local MAX_VISIBLE_ROWS = 10
local ROW_INSET = 2
local ROW_TEXT_RIGHT_INSET = 10
local DIVIDER_ROW_HEIGHT = 8
local DIVIDER_EDGE_INSET = 3
local SELECTED_COLOR = { 1, 0.82, 0, 0.11 }
local HOVER_COLOR = { 1, 1, 1, 0.07 }
local DIVIDER = {}
local KEEP_OPEN = {}

function Provider:CreateProvider(context, Layout, Constants, isPreferredName)
    local Pixel = context.pixel
    local MediaMenu = {}
    MediaMenu.DIVIDER = DIVIDER
    MediaMenu.KEEP_OPEN = KEEP_OPEN
    MediaMenu.ROW_TEXT_RIGHT_INSET = ROW_TEXT_RIGHT_INSET

    local function IsPreferredName(name)
        return isPreferredName and isPreferredName(name) or false
    end

    local function SortNames(items, TextOf)
        tsort(items, function(a, b)
            return strlower(TextOf(a)) < strlower(TextOf(b))
        end)
    end

    -- [ FACTORY ]------------------------------------------------------------------------------------------------------
    local function DefaultItemText(item)
        return tostring(item)
    end

    local function SelectRow(row)
        if row._onSelect(row._item) ~= KEEP_OPEN then
            row._popup:Hide()
        end
    end

    function MediaMenu:Create(owner, opts)
        local rowHeight = opts.rowHeight
        local sorted = opts.sorted ~= false
        local hasSearch = opts.search ~= false
        local TextOf = opts.itemText or DefaultItemText

        local popup = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
        Pixel:Enforce(popup)
        popup:SetFrameStrata(Constants.Strata.FullscreenDialog)
        popup:SetFrameLevel(1000) -- strata-ok: dropdown popup above every dialog surface
        popup:SetWidth(POPUP_WIDTH)
        popup:SetClipsChildren(true)
        popup:EnableMouse(true)
        popup:Hide()
        popup:SetBackdrop({
            bgFile = Constants.Texture.White,
            edgeFile = Constants.Texture.White,
            edgeSize = Pixel:Multiple(1, popup:GetEffectiveScale()),
        })
        popup:SetBackdropColor(0.06, 0.06, 0.06, 0.98)
        popup:SetBackdropBorderColor(0.3, 0.3, 0.3, 1)

        local searchStrip = CreateFrame("Frame", nil, popup, "BackdropTemplate")
        Pixel:Enforce(searchStrip)
        searchStrip:SetHeight(SEARCH_HEIGHT)
        Pixel:Point(searchStrip, "TOPLEFT", PAD, -PAD)
        Pixel:Point(searchStrip, "TOPRIGHT", -PAD, -PAD)
        searchStrip:SetBackdrop(Layout.ORBIT_INPUT_BACKDROP)
        searchStrip:SetBackdropColor(0, 0, 0, 0.6)
        searchStrip:SetBackdropBorderColor(0.5, 0.5, 0.5, 1)

        local search = CreateFrame("EditBox", nil, searchStrip, "SearchBoxTemplate")
        Pixel:Point(search, "TOPLEFT", 8, -1)
        Pixel:Point(search, "BOTTOMRIGHT", -6, 1)
        search:SetFontObject(ChatFontNormal)
        search:SetAutoFocus(false)
        if search.Left then
            search.Left:Hide()
        end
        if search.Middle then
            search.Middle:Hide()
        end
        if search.Right then
            search.Right:Hide()
        end
        popup.Search = search
        searchStrip:SetShown(hasSearch)

        local popupScale = popup:GetEffectiveScale()
        local pad = Pixel:Multiple(PAD, popupScale)
        local searchSpace = hasSearch and (searchStrip:GetHeight() + pad) or 0
        local content = CreateFrame("Frame", nil, popup)
        Pixel:Enforce(content)
        content:SetPoint("TOPLEFT", popup, "TOPLEFT", pad, -(pad + searchSpace))
        content:SetPoint("TOPRIGHT", popup, "TOPRIGHT", -pad, -(pad + searchSpace))

        local scale = content:GetEffectiveScale()
        local resolvedRowHeight = Pixel:Snap(rowHeight, scale)
        local resolvedDividerHeight = Pixel:Multiple(DIVIDER_ROW_HEIGHT, scale)
        local maxHeight = Pixel:Snap(opts.maxHeight, popupScale)
        local fitByHeight = math_max(1, math_floor((maxHeight - searchSpace - pad * 2) / resolvedRowHeight))
        local visibleSlots = math_min(MAX_VISIBLE_ROWS, fitByHeight)

        popup.rows = {}
        popup.dividers = {}
        popup.filtered = {}
        popup.allItems = {}
        popup.scrollOffset = 0
        popup.selected = nil

        local function IsSelected(item)
            return type(popup.selected) == "function" and popup.selected(item) or item == popup.selected
        end

        local function RenderVisible()
            local items = popup.filtered
            local edgeInset = Pixel:Multiple(DIVIDER_EDGE_INSET, popupScale)
            local y = 0
            for slot = 1, visibleSlots do
                local row = popup.rows[slot]
                if not row then
                    row = opts.createRow(content)
                    Pixel:Enforce(row)
                    row:SetHeight(resolvedRowHeight)

                    row.SelectedBackground = row:CreateTexture(nil, "BACKGROUND", nil, 7)
                    Pixel:Point(row.SelectedBackground, "TOPLEFT", ROW_INSET, -1)
                    Pixel:Point(row.SelectedBackground, "BOTTOMRIGHT", -ROW_INSET, 1)
                    row.SelectedBackground:SetColorTexture(unpack(SELECTED_COLOR))

                    local hl = row:CreateTexture(nil, "HIGHLIGHT")
                    Pixel:Point(hl, "TOPLEFT", ROW_INSET, -1)
                    Pixel:Point(hl, "BOTTOMRIGHT", -ROW_INSET, 1)
                    hl:SetColorTexture(unpack(HOVER_COLOR))
                    row:SetScript("OnClick", SelectRow)
                    popup.rows[slot] = row
                end
                local divider = popup.dividers[slot]
                if not divider then
                    divider = content:CreateTexture(nil, "ARTWORK")
                    divider:SetHeight(Pixel:Multiple(1, scale))
                    divider:SetColorTexture(0.35, 0.35, 0.35, 1)
                    popup.dividers[slot] = divider
                end
                local item = items[popup.scrollOffset + slot]
                if item == DIVIDER then
                    local dy = Pixel:Snap(y - resolvedDividerHeight / 2, scale)
                    divider:ClearAllPoints()
                    divider:SetPoint("LEFT", popup, "TOPLEFT", edgeInset, -(pad + searchSpace) + dy)
                    divider:SetPoint("RIGHT", popup, "TOPRIGHT", -edgeInset, -(pad + searchSpace) + dy)
                    divider:Show()
                    row:Hide()
                elseif item then
                    row:ClearAllPoints()
                    local rowY = Pixel:Snap(y, scale)
                    row:SetPoint("TOPLEFT", content, "TOPLEFT", 0, rowY)
                    row:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, rowY)
                    local isSelected = IsSelected(item)
                    opts.renderRow(row, item, isSelected)
                    row._item, row._onSelect, row._popup = item, opts.onSelect, popup
                    row.SelectedBackground:SetShown(isSelected)
                    row:Show()
                    divider:Hide()
                else
                    row:Hide()
                    divider:Hide()
                end
                if item then
                    y = y - (item == DIVIDER and resolvedDividerHeight or resolvedRowHeight)
                end
            end
        end

        local function ResizeToContent()
            local height = 0
            for slot = 1, math_min(#popup.filtered - popup.scrollOffset, visibleSlots) do
                height = height
                    + (
                        popup.filtered[popup.scrollOffset + slot] == DIVIDER and resolvedDividerHeight
                        or resolvedRowHeight
                    )
            end
            height = math_max(resolvedRowHeight, height)
            content:SetHeight(height)
            popup:SetHeight(searchSpace + height + pad * 2)
        end

        local measure
        local function RequiredWidth()
            local row = popup.rows[1]
            local text = row and row.Text
            if not text then
                return 0
            end
            local defaultLeftInset
            if not opts.itemTextLeftInset then
                local rowLeft, textLeft = row:GetLeft(), text:GetLeft()
                if not (rowLeft and textLeft) then
                    return 0
                end
                defaultLeftInset = textLeft - rowLeft
            end
            if not measure then
                measure = popup:CreateFontString(nil, "OVERLAY")
            end
            local fontObject = text:GetFontObject()
            if fontObject then
                measure:SetFontObject(fontObject)
            else
                local path, size, flags = text:GetFont()
                if not path then
                    return 0
                end
                measure:SetFont(path, size, flags)
            end
            local widest = 0
            for _, item in ipairs(popup.allItems) do
                if item ~= DIVIDER then
                    measure:SetText((type(item) == "table" and item.title) or TextOf(item))
                    local leftInset = (opts.itemTextLeftInset and opts.itemTextLeftInset(item, row)) or defaultLeftInset
                    widest = math_max(widest, leftInset + measure:GetStringWidth())
                end
            end
            return widest + Pixel:Multiple(ROW_TEXT_RIGHT_INSET, popupScale) + pad * 2
        end

        -- [ FILTER + SORT ]--------------------------------------------------------------------------------------------
        local function Matches(item, query)
            return query == "" or strfind(strlower(TextOf(item)), query, 1, true)
        end

        local function ApplyFilter()
            local query = hasSearch and strlower(search:GetText() or "") or ""
            local filtered = {}
            if opts.pinnedItem then
                tinsert(filtered, opts.pinnedItem)
            end
            if not sorted then
                for _, item in ipairs(popup.allItems) do
                    if item == DIVIDER then
                        if #filtered > 0 and filtered[#filtered] ~= DIVIDER then
                            tinsert(filtered, DIVIDER)
                        end
                    elseif item ~= opts.pinnedItem and Matches(item, query) then
                        tinsert(filtered, item)
                    end
                end
                if filtered[#filtered] == DIVIDER then
                    filtered[#filtered] = nil
                end
                popup.filtered = filtered
                popup.scrollOffset = 0
                ResizeToContent()
                RenderVisible()
                return
            end
            if opts.firstItem and opts.firstItem ~= opts.pinnedItem and Matches(opts.firstItem, query) then
                tinsert(filtered, opts.firstItem)
            end
            local orbit, other = {}, {}
            for _, name in ipairs(popup.allItems) do
                if name ~= opts.pinnedItem and Matches(name, query) then
                    tinsert(IsPreferredName(TextOf(name)) and orbit or other, name)
                end
            end
            SortNames(orbit, TextOf)
            SortNames(other, TextOf)
            for _, name in ipairs(orbit) do
                tinsert(filtered, name)
            end
            if #orbit > 0 and #other > 0 then
                tinsert(filtered, DIVIDER)
            end
            for _, name in ipairs(other) do
                tinsert(filtered, name)
            end
            popup.filtered = filtered
            popup.scrollOffset = 0
            ResizeToContent()
            RenderVisible()
        end

        local function RevealSelected()
            for index, item in ipairs(popup.filtered) do
                if IsSelected(item) then
                    local maxOffset = math_max(0, #popup.filtered - visibleSlots)
                    popup.scrollOffset = math_max(0, math_min(maxOffset, index - math_floor(visibleSlots / 2) - 1))
                    ResizeToContent()
                    RenderVisible()
                    return
                end
            end
        end

        search:SetScript("OnTextChanged", function(self)
            SearchBoxTemplate_OnTextChanged(self)
            ApplyFilter()
        end)
        search:SetScript("OnEscapePressed", function(self)
            self:ClearFocus()
            popup:Hide()
        end)

        popup:EnableMouseWheel(true)
        popup:SetScript("OnMouseWheel", function(_, delta)
            local maxOffset = math_max(0, #popup.filtered - visibleSlots)
            popup.scrollOffset = math_max(0, math_min(maxOffset, popup.scrollOffset - delta))
            ResizeToContent()
            RenderVisible()
        end)

        function popup:SetSearchEnabled(enabled)
            hasSearch = enabled and true or false
            searchStrip:SetShown(hasSearch)
            searchSpace = hasSearch and (searchStrip:GetHeight() + pad) or 0
            content:ClearAllPoints()
            content:SetPoint("TOPLEFT", self, "TOPLEFT", pad, -(pad + searchSpace))
            content:SetPoint("TOPRIGHT", self, "TOPRIGHT", -pad, -(pad + searchSpace))
            fitByHeight = math_max(1, math_floor((maxHeight - searchSpace - pad * 2) / resolvedRowHeight))
            visibleSlots = math_min(MAX_VISIBLE_ROWS, fitByHeight)
            for slot = visibleSlots + 1, #self.rows do
                self.rows[slot]:Hide()
                self.dividers[slot]:Hide()
            end
        end

        function popup:Populate(items, selected)
            self.allItems = items
            self.selected = selected
            self:ClearAllPoints()
            Pixel:Point(self, "TOPLEFT", owner, "BOTTOMLEFT", 0, -2)
            search:SetText("")
            ApplyFilter()
            RevealSelected()
            self:Show()
            self:SetWidth(math_max(owner:GetWidth() or POPUP_WIDTH, RequiredWidth()))
            if hasSearch then
                search:SetFocus()
            end
        end

        function popup:RefreshItems(items)
            self.allItems = items
            ApplyFilter()
            self:SetWidth(math_max(owner:GetWidth() or POPUP_WIDTH, RequiredWidth()))
        end

        function popup:SetSelected(selected)
            self.selected = selected
            RenderVisible()
        end

        -- [ CLOSE LIFECYCLE ]------------------------------------------------------------------------------------------
        popup:SetScript("OnKeyDown", function(self, key)
            if key == "ESCAPE" then
                if not InCombatLockdown() then
                    self:SetPropagateKeyboardInput(false)
                end
                self:Hide()
            elseif not InCombatLockdown() then
                self:SetPropagateKeyboardInput(true)
            end
        end)
        popup:SetScript("OnShow", function(self)
            if not InCombatLockdown() then
                self:SetPropagateKeyboardInput(true)
            end
            self.closeTimer = 0
            self:SetScript("OnUpdate", function(d, elapsed)
                if not owner:IsVisible() then
                    d:Hide()
                    return
                end
                local over = d:IsMouseOver() or owner:IsMouseOver()
                if not over and (IsMouseButtonDown("LeftButton") or IsMouseButtonDown("RightButton")) then
                    d:Hide()
                    return
                end
                if search:HasFocus() then
                    d.closeTimer = 0
                elseif not over then
                    d.closeTimer = d.closeTimer + elapsed
                    if d.closeTimer > AUTO_CLOSE_DELAY then
                        d:Hide()
                    end
                else
                    d.closeTimer = 0
                end
            end)
        end)
        popup:SetScript("OnHide", function(self)
            self:SetScript("OnUpdate", nil)
            search:ClearFocus()
        end)

        return popup
    end

    return MediaMenu
end

table.freeze(Provider)
