local _, addon = ...
local Provider = {}
addon.LibOrbitUI.MediaMenu = Provider
local SEARCH_HEIGHT = 26
local MAX_VISIBLE_ROWS = 10
local PAD, SEARCH_GAP, SCROLL_GAP = 5, 5, 10
local CHOICE_INSET, CHECK_SIZE = 20, 16
local CHECK_INSET, ROW_INSET = 8, 2
local CONTENT_INSET, ROW_TEXT_RIGHT_INSET = 48, 10
local DIVIDER_HEIGHT, OVERSCAN = 8, 1
local POPUP_LEVEL = 1000
local BACKGROUND = { 0.06, 0.06, 0.06, 0.98 }
local BORDER = { 0.3, 0.3, 0.3, 1 }
local SELECTED_COLOR = { 1, 0.82, 0, 0.11 }
local HOVER_COLOR = { 1, 1, 1, 0.07 }
local DIVIDER, KEEP_OPEN = {}, {}

function Provider:CreateProvider(context, Layout, Constants, isPreferredName)
    local Pixel = context.pixel
    local MediaMenu = { DIVIDER = DIVIDER, KEEP_OPEN = KEEP_OPEN, ROW_TEXT_RIGHT_INSET = ROW_TEXT_RIGHT_INSET }

    function MediaMenu:Create(owner, opts)
        -- A control-parented popup inherits the settings scroll area's clipping, even on a higher strata.
        local popup = CreateFrame("Frame", nil, UIParent, "BackdropTemplate")
        popup:SetIgnoreParentScale(true)
        popup:SetScale(owner:GetEffectiveScale())
        Pixel:Enforce(popup)
        popup:SetFrameStrata(Constants.Strata.FullscreenDialog)
        popup:SetFrameLevel(POPUP_LEVEL) -- strata-ok: picker chrome above the owning settings dialog
        popup:SetClampedToScreen(true)
        popup:EnableMouse(true)
        popup:Hide()
        popup.allItems, popup.filtered, popup.rows = {}, {}, {}
        popup.generation = 0
        local hasSearch = opts.search ~= false
        local TextOf = opts.itemText or tostring
        popup:SetBackdrop({
            bgFile = Constants.Texture.White,
            edgeFile = Constants.Texture.White,
            edgeSize = Pixel:Multiple(1, popup:GetEffectiveScale()),
        })
        popup:SetBackdropColor(unpack(BACKGROUND))
        popup:SetBackdropBorderColor(unpack(BORDER))
        local searchStrip = CreateFrame("Frame", nil, popup, "BackdropTemplate")
        Pixel:Enforce(searchStrip)
        searchStrip:SetHeight(SEARCH_HEIGHT)
        Pixel:Point(searchStrip, "TOPLEFT", PAD, -PAD)
        Pixel:Point(searchStrip, "TOPRIGHT", -PAD, -PAD)
        searchStrip:SetBackdrop(Layout.ORBIT_INPUT_BACKDROP)
        searchStrip:SetBackdropColor(0, 0, 0, 0.6)
        searchStrip:SetBackdropBorderColor(0.5, 0.5, 0.5, 1)
        local search = CreateFrame("EditBox", nil, searchStrip, "SearchBoxTemplate")
        search:SetAutoFocus(false)
        search:SetFontObject(ChatFontNormal)
        Pixel:Point(search, "TOPLEFT", 8, -1)
        Pixel:Point(search, "BOTTOMRIGHT", -6, 1)
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
        local viewport = CreateFrame("ScrollFrame", nil, popup)
        Pixel:Enforce(viewport)
        viewport:SetClipsChildren(true)
        local content = CreateFrame("Frame", nil, viewport)
        Pixel:Enforce(content)
        content:SetSize(1, 1) -- px-ok: initial scroll-child extent before content layout
        viewport:SetScrollChild(content)
        local scrollBar = Layout.scrollBar:Attach(viewport, { rightOffsetPixels = SCROLL_GAP })
        popup.ScrollFrame, popup.ScrollBar = viewport, scrollBar
        local measure = popup:CreateFontString(nil, "OVERLAY", Constants.UI.LabelFont)
        measure:Hide()
        local tops, bottoms = {}, {}

        local rowPool = CreateObjectPool(function()
            local slot = CreateFrame("Button", nil, content)
            Pixel:Enforce(slot)
            slot.Content = opts.createRow(slot)
            Pixel:Enforce(slot.Content)
            slot.Check = CreateFrame("CheckButton", nil, slot, "UIRadialButtonTemplate")
            slot.Check:EnableMouse(false)
            slot.Check:SetSize(CHECK_SIZE, CHECK_SIZE)
            Pixel:Point(slot.Check, "LEFT", CHECK_INSET, 0)
            slot.Selected = slot:CreateTexture(nil, "BACKGROUND")
            Pixel:Point(slot.Selected, "TOPLEFT", ROW_INSET, -1)
            Pixel:Point(slot.Selected, "BOTTOMRIGHT", -ROW_INSET, 1)
            slot.Selected:SetColorTexture(unpack(SELECTED_COLOR))
            slot.Highlight = slot:CreateTexture(nil, "HIGHLIGHT")
            Pixel:Point(slot.Highlight, "TOPLEFT", ROW_INSET, -1)
            Pixel:Point(slot.Highlight, "BOTTOMRIGHT", -ROW_INSET, 1)
            slot.Highlight:SetColorTexture(unpack(HOVER_COLOR))
            slot.Divider = slot:CreateTexture(nil, "ARTWORK")
            slot.Divider:SetHeight(Pixel:Multiple(1, slot:GetEffectiveScale()))
            slot.Divider:SetPoint("LEFT")
            slot.Divider:SetPoint("RIGHT")
            slot.Divider:SetColorTexture(0.35, 0.35, 0.35, 1)
            slot:SetScript("OnEnter", function()
                local enter = slot.Content:GetScript("OnEnter")
                if enter then
                    enter(slot.Content)
                end
            end)
            slot:SetScript("OnLeave", Layout.configOptions.tooltipHide)
            return slot
        end, function(_, slot)
            slot:Hide()
            slot.Content:Hide()
            slot:ClearAllPoints()
            slot:SetScript("OnClick", nil)
            slot.item = nil
        end)

        local function IsSelected(item)
            if type(popup.selected) == "function" then
                return popup.selected(item)
            end
            return item == popup.selected
        end

        local function ApplyFilter()
            local query = hasSearch and string.lower(search:GetText() or "") or ""
            local function Matches(item)
                return query == "" or string.find(string.lower(TextOf(item)), query, 1, true)
            end
            local filtered = {}
            if opts.pinnedItem then
                filtered[#filtered + 1] = opts.pinnedItem
            end
            if opts.sorted == false then
                for _, item in ipairs(popup.allItems) do
                    if item == DIVIDER then
                        if #filtered > 0 and filtered[#filtered] ~= DIVIDER then
                            filtered[#filtered + 1] = DIVIDER
                        end
                    elseif item ~= opts.pinnedItem and Matches(item) then
                        filtered[#filtered + 1] = item
                    end
                end
                if filtered[#filtered] == DIVIDER then
                    filtered[#filtered] = nil
                end
            else
                if opts.firstItem and opts.firstItem ~= opts.pinnedItem and Matches(opts.firstItem) then
                    filtered[#filtered + 1] = opts.firstItem
                end
                local preferred, other = {}, {}
                for _, item in ipairs(popup.allItems) do
                    if item ~= DIVIDER and item ~= opts.pinnedItem and item ~= opts.firstItem and Matches(item) then
                        local list = isPreferredName and isPreferredName(TextOf(item)) and preferred or other
                        list[#list + 1] = item
                    end
                end
                local function Sort(a, b)
                    return string.lower(TextOf(a)) < string.lower(TextOf(b))
                end
                table.sort(preferred, Sort)
                table.sort(other, Sort)
                for _, item in ipairs(preferred) do
                    filtered[#filtered + 1] = item
                end
                if #preferred > 0 and #other > 0 then
                    filtered[#filtered + 1] = DIVIDER
                end
                for _, item in ipairs(other) do
                    filtered[#filtered + 1] = item
                end
            end
            popup.filtered = filtered
        end

        local function ReleaseRows()
            for index, slot in pairs(popup.rows) do
                popup.rows[index] = nil
                rowPool:Release(slot)
            end
        end

        local function Paint(slot, item)
            local divider = item == DIVIDER
            local title = not divider and type(item) == "table" and item.title ~= nil
            local action = not divider and type(item) == "table" and item.action ~= nil
            local selectable = not divider and not title
            local choice = selectable and not action
            local check = choice and type(popup.selected) == "function"
            slot.Divider:SetShown(divider)
            slot.Check:SetShown(check)
            slot.Check:SetChecked(check and IsSelected(item))
            slot.Selected:SetShown(choice and IsSelected(item))
            slot:EnableMouse(selectable)
            if divider then
                slot.Content:Hide()
            else
                slot.Content:ClearAllPoints()
                Pixel:Point(slot.Content, "TOPLEFT", check and CHOICE_INSET or 0, 0)
                slot.Content:SetPoint("BOTTOMRIGHT")
                opts.renderRow(slot.Content, item, IsSelected(item))
                slot.Content:EnableMouse(false)
                slot.Content:Show()
            end
            slot.selected = IsSelected(item)
        end

        local function RenderVisible()
            if popup.layingOut or not popup:IsShown() then
                return
            end
            local y = viewport:GetVerticalScroll()
            local low, high = 1, #popup.filtered
            while low <= high do
                local middle = math.floor((low + high) / 2)
                if bottoms[middle] <= y then
                    low = middle + 1
                else
                    high = middle - 1
                end
            end
            local first = math.max(1, low - OVERSCAN)
            local last = low - 1
            while last < #popup.filtered and tops[last + 1] < y + viewport:GetHeight() do
                last = last + 1
            end
            last = math.min(#popup.filtered, last + OVERSCAN)
            for index, slot in pairs(popup.rows) do
                if index < first or index > last then
                    popup.rows[index] = nil
                    rowPool:Release(slot)
                end
            end
            for index = first, last do
                if not popup.rows[index] then
                    local slot = rowPool:Acquire()
                    local item, generation = popup.filtered[index], popup.generation
                    popup.rows[index], slot.item = slot, item
                    slot:SetPoint("TOPLEFT", content, "TOPLEFT", 0, -tops[index])
                    slot:SetPoint("TOPRIGHT", content, "TOPRIGHT", 0, -tops[index])
                    slot:SetHeight(bottoms[index] - tops[index])
                    Paint(slot, item)
                    slot:SetScript("OnClick", function()
                        if not popup:IsShown() or popup.generation ~= generation or slot.item ~= item then
                            return
                        end
                        local response = opts.onSelect(item)
                        if popup.generation == generation and response ~= KEEP_OPEN then
                            popup:Hide()
                        end
                    end)
                    slot:Show()
                end
            end
        end

        local function Position()
            popup:ClearAllPoints()
            local bottom = owner:GetBottom()
            local above = bottom and bottom * owner:GetEffectiveScale() < popup:GetHeight() * popup:GetEffectiveScale()
            if above then
                Pixel:Point(popup, "BOTTOMLEFT", owner, "TOPLEFT", 0, 2)
            else
                Pixel:Point(popup, "TOPLEFT", owner, "BOTTOMLEFT", 0, -2)
            end
        end

        local function LayoutItems(revealSelected)
            popup.layingOut = true
            popup:SetScale(owner:GetEffectiveScale())
            popup.generation = popup.generation + 1
            ReleaseRows()
            ApplyFilter()
            local scale = popup:GetEffectiveScale()
            local pad = Pixel:Multiple(PAD, scale)
            local gap = Pixel:Multiple(SCROLL_GAP, scale)
            local searchSpace = hasSearch and Pixel:Snap(SEARCH_HEIGHT, scale) + Pixel:Multiple(SEARCH_GAP, scale) or 0
            local rowHeight = Pixel:Snap(opts.rowHeight, scale)
            local height, width, selectedY = 0, owner:GetWidth(), nil
            tops, bottoms = {}, {}
            for index, item in ipairs(popup.filtered) do
                tops[index] = height
                height = height + (item == DIVIDER and Pixel:Multiple(DIVIDER_HEIGHT, scale) or rowHeight)
                bottoms[index] = height
                if selectedY == nil and IsSelected(item) then
                    selectedY = tops[index]
                end
                if item ~= DIVIDER then
                    measure:SetText((type(item) == "table" and item.title) or TextOf(item))
                    local left = opts.itemTextLeftInset and opts.itemTextLeftInset(item, popup)
                        or Pixel:Multiple(CONTENT_INSET, scale)
                    width = math.max(
                        width,
                        measure:GetUnboundedStringWidth()
                            + left
                            + Pixel:Multiple(
                                (type(popup.selected) == "function" and CHOICE_INSET or 0) + ROW_TEXT_RIGHT_INSET,
                                scale
                            )
                            + pad * 2
                            + gap
                    )
                end
            end
            local viewportHeight = math.max(
                rowHeight,
                math.min(height, rowHeight * MAX_VISIBLE_ROWS, opts.maxHeight - searchSpace - pad * 2)
            )
            popup:SetSize(width, viewportHeight + searchSpace + pad * 2)
            searchStrip:SetShown(hasSearch)
            viewport:ClearAllPoints()
            viewport:SetPoint("TOPLEFT", popup, "TOPLEFT", pad, -(pad + searchSpace))
            viewport:SetSize(width - pad * 2 - gap, viewportHeight)
            content:SetSize(viewport:GetWidth(), math.max(height, viewportHeight))
            viewport:UpdateScrollChildRect()
            scrollBar:SetScrollPosition(
                revealSelected and math.max(0, (selectedY or 0) - viewportHeight / 2 + rowHeight / 2)
                    or viewport:GetVerticalScroll()
            )
            Position()
            popup.layingOut = nil
            RenderVisible()
        end

        function popup:SetSearchEnabled(enabled)
            hasSearch = enabled == true
        end

        function popup:Populate(items, selected)
            if MediaMenu.active and MediaMenu.active ~= self then
                MediaMenu.active:Hide()
            end
            MediaMenu.active = self
            self.allItems, self.selected = items, selected
            self.populating = true
            search:SetText("")
            self.populating = nil
            LayoutItems(true)
            self:Show()
            RenderVisible()
            if hasSearch then
                search:SetFocus()
            end
        end

        function popup:RefreshItems(items)
            self.allItems = items
            LayoutItems(false)
        end

        function popup:SetSelected(selected)
            self.selected = selected
            for _, slot in pairs(self.rows) do
                if slot.selected ~= IsSelected(slot.item) then
                    Paint(slot, slot.item)
                end
            end
        end

        viewport:SetScript("OnVerticalScroll", RenderVisible)
        search:SetScript("OnTextChanged", function(self)
            SearchBoxTemplate_OnTextChanged(self)
            if not popup.populating then
                scrollBar:SetScrollPosition(0)
                LayoutItems(false)
            end
        end)
        search:SetScript("OnEscapePressed", function()
            popup:Hide()
        end)
        popup:SetScript("OnKeyDown", function(self, key)
            if not InCombatLockdown() then
                self:SetPropagateKeyboardInput(key ~= "ESCAPE")
            end
            if key == "ESCAPE" then
                self:Hide()
            end
        end)
        popup:SetScript("OnEvent", function()
            if not popup:IsMouseOver() and not owner:IsMouseOver() then
                popup:Hide()
            end
        end)
        popup:SetScript("OnShow", function(self)
            self:RegisterEvent("GLOBAL_MOUSE_DOWN")
            if not InCombatLockdown() then
                self:SetPropagateKeyboardInput(true)
            end
        end)
        popup:SetScript("OnHide", function(self)
            self.generation = self.generation + 1
            self:UnregisterEvent("GLOBAL_MOUSE_DOWN")
            scrollBar:StopScrolling()
            ReleaseRows()
            search:ClearFocus()
            Layout.configOptions.tooltipHide()
            if MediaMenu.active == self then
                MediaMenu.active = nil
            end
        end)
        return popup
    end
    return MediaMenu
end

table.freeze(Provider)
