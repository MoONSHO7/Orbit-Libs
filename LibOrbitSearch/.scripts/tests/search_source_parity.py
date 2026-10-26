"""Exercise native source completeness against the shipped Lua 5.1 search engine."""
import unittest

from client_contracts import runtime


class SearchSourceParityTests(unittest.TestCase):
    def test_all_profession_returns_survive_nil_holes(self):
        lua = runtime(True)
        lua.execute("""
            GetProfessions = function() return 1, nil, 3, nil, nil, nil, 7 end
            GetProfessionInfo = function(index)
                return "Craft "..index, 1, 1, 100, 1, index * 10, 200 + index
            end
            C_SpellBook = { GetSpellBookItemInfo = function(slot, bank)
                assert(bank == Enum.SpellBookSpellBank.Player)
                return {name = "Open action "..slot, spellID = 1000 + slot}
            end }
            local search = Search("professions")
            local entries = search:Query("craft", options)
            assert(#entries == 3)
            local entry = search:Query("craft 7", options)[1]
            assert(entry and entry.id == "207:1071" and entry.spellID == 1071)
            assert(entry.secure.type == "spell" and entry.secure.spell == 1071)
            GetProfessions = function() return nil, nil, nil, nil, nil, nil, nil, nil, 9 end
            FireEvent("SKILL_LINES_CHANGED")
            assert(not search:IsEntryCurrent(entry))
            entries = search:Query("craft", options)
            assert(#entries == 1 and entries[1].spellID == 1091)
        """)

    def test_player_and_pet_spell_ranks_keep_distinct_native_ids(self):
        lua = runtime(True)
        lua.execute("""
            Enum.SpellBookItemType = {Spell = 1, Flyout = 2, PetAction = 3}
            C_SpellBook = {
                GetNumSpellBookSkillLines = function() return 1 end,
                GetSpellBookSkillLineInfo = function()
                    return {itemIndexOffset = 0, numSpellBookItems = 2}
                end,
                HasPetSpells = function() return 1 end,
                GetSpellBookItemInfo = function(slot, bank)
                    if bank == Enum.SpellBookSpellBank.Pet then
                        return {itemType = 1, name = "Bite", subName = "Rank 3", spellID = 203}
                    end
                    return {itemType = 1, name = "Heal", subName = "Rank "..slot, spellID = 100 + slot}
                end,
            }
            local search = Search("spellbook")
            assert(#search:Query("heal", options) == 2)
            local first = search:Query("heal rank 1", options)[1]
            local second = search:Query("heal rank 2", options)[1]
            assert(first.id == 101 and first.spellID == 101 and first.secure.spell == 101)
            assert(first.name == "Heal (Rank 1)" and first.subName == "Rank 1")
            assert(second.id == 102 and second.secure.spell == 102)
            assert(search:Query("bite rank 3", options)[1].secure.spell == 203)
            assert(search:Query("101", options)[1].id == 101)
        """)

    def test_delayed_native_rank_text_retires_old_results_and_recovers(self):
        lua = runtime(True)
        lua.execute("""
            Enum.SpellBookItemType = {Spell = 1, Flyout = 2}
            local subName = ""
            C_SpellBook = {
                GetNumSpellBookSkillLines = function() return 1 end,
                GetSpellBookSkillLineInfo = function()
                    return {itemIndexOffset = 0, numSpellBookItems = 1}
                end,
                GetSpellBookItemInfo = function()
                    return {itemType = Enum.SpellBookItemType.Spell, name = "Heal",
                        subName = subName, spellID = 101}
                end,
            }
            local search = Search("spellbook")
            local entry = search:Query("heal", options)[1]
            assert(entry.name == "Heal" and #search:Query("rank 1", options) == 0)
            subName = "Rank 1"
            FireEvent("SPELL_TEXT_UPDATE", 101)
            assert(not search:IsEntryCurrent(entry))
            entry = search:Query("heal rank 1", options)[1]
            assert(entry and entry.id == 101 and entry.name == "Heal (Rank 1)")
            search:Disable()
            subName = "Rank 2"
            FireEvent("SPELL_TEXT_UPDATE", 101)
            search:Enable()
            assert(search:Query("heal rank 2", options)[1].id == 101)
        """)

    def test_flyout_rank_enrichment_is_optional(self):
        lua = runtime(True)
        lua.execute("""
            Enum.SpellBookItemType = {Spell = 1, Flyout = 2}
            C_SpellBook = {
                GetNumSpellBookSkillLines = function() return 1 end,
                GetSpellBookSkillLineInfo = function()
                    return {itemIndexOffset = 0, numSpellBookItems = 1}
                end,
                GetSpellBookItemInfo = function()
                    return {itemType = 2, name = "Portals", actionID = 5}
                end,
            }
            GetFlyoutInfo = function() return "Portals", "", 1, true end
            GetFlyoutSlotInfo = function() return 101, nil, true, "Portal" end
            C_Spell.GetSpellSubtext = function(id) assert(id == 101); return "Rank 2" end
            local search = Search("spellbook")
            assert(search:Query("portal rank 2", options)[1].secure.spell == 101)
            C_Spell.GetSpellSubtext = nil
            lib:MarkDirty("spellbook")
            assert(search:Query("portal", options)[1].name == "Portal")
        """)

    def test_species_and_all_nicknames_resolve_to_a_stable_summonable_pet(self):
        lua = runtime(True)
        lua.execute("""
            local ids = {"Pet-Dead", "Pet-Z", "Pet-A", "Pet-B"}
            local pets = {
                ["Pet-Dead"] = {name = "Fluffy", favorite = true, summonable = false},
                ["Pet-Z"] = {name = "Snowball", favorite = true, summonable = true},
                ["Pet-A"] = {name = "Cotton", favorite = true, summonable = true},
                ["Pet-B"] = {name = "Cloud", favorite = false, summonable = true},
            }
            BATTLE_PET_NAME_1 = "battle-family"
            C_PetJournal = {
                GetOwnedPetIDs = function() return ids end,
                GetPetInfoByPetID = function(id)
                    local pet = pets[id]
                    return 123, pet.name, 1, 0, 0, 0, pet.favorite, "Snowshoe Rabbit",
                        1, 1, nil, nil, nil, false, false
                end,
                PetIsSummonable = function(id) return pets[id].summonable end,
                SummonPetByGUID = function(id) mock.summoned = id end,
            }
            local search = Search("pets")
            local entry = search:Query("snowshoe rabbit", options)[1]
            assert(entry.id == 123 and entry.petGUID == "Pet-A" and entry.name == "Cotton")
            assert(entry.favorite and not entry.passive)
            assert(entry.secure.macrotext == '/run C_PetJournal.SummonPetByGUID("Pet-A")')
            assert(#search:Query("rabbit", options) == 1)
            assert(#search:Query("battle-family", options) == 0)
            for _, alias in ipairs({"fluffy", "snowball", "cotton", "cloud"}) do
                assert(search:Query(alias, options)[1] == entry)
            end
            ids = {"Pet-B", "Pet-A", "Pet-Z", "Pet-Dead"}
            FireEvent("PET_JOURNAL_LIST_UPDATE")
            assert(not search:IsEntryCurrent(entry))
            assert(search:Query("snowshoe rabbit", options)[1].petGUID == "Pet-A")
            pets["Pet-A"].summonable = false
            FireEvent("PET_JOURNAL_LIST_UPDATE")
            assert(search:Query("cotton", options)[1].petGUID == "Pet-Z")
        """)

    def test_unsummonable_companions_keep_names_without_inventing_actions(self):
        lua = runtime(True)
        lua.execute("""
            C_PetJournal = {
                GetOwnedPetIDs = function() return {"Pet-B", "Pet-A"} end,
                GetPetInfoByPetID = function(id)
                    return 123, id == "Pet-A" and "" or "Fluffy", 1, 0, 0, 0,
                        false, "Snowshoe Rabbit", 1, 1, nil, nil, nil, false, false
                end,
            }
            local search = Search("pets")
            local entry = search:Query("fluffy", options)[1]
            assert(entry and entry.id == 123 and entry.petGUID == "Pet-A")
            assert(entry.name == "Snowshoe Rabbit" and entry.passive and not entry.secure)
            assert(search:Query("snowshoe rabbit", options)[1] == entry)
        """)

    def test_favorite_describes_the_selected_summonable_pet(self):
        lua = runtime(True)
        lua.execute("""
            C_PetJournal = {
                GetOwnedPetIDs = function() return {"Pet-Favorite", "Pet-Summonable"} end,
                GetPetInfoByPetID = function(id)
                    return 123, id == "Pet-Favorite" and "Fluffy" or "Cotton", 1, 0, 0, 0,
                        id == "Pet-Favorite", "Snowshoe Rabbit", 1, 1, nil, nil, nil, false, false
                end,
                PetIsSummonable = function(id) return id == "Pet-Summonable" end,
                SummonPetByGUID = function() end,
            }
            local entry = Search("pets"):Query("fluffy", options)[1]
            assert(entry and entry.petGUID == "Pet-Summonable" and entry.name == "Cotton")
            assert(entry.favorite == false and not entry.passive)
            assert(entry.secure.macrotext == '/run C_PetJournal.SummonPetByGUID("Pet-Summonable")')
        """)

    def test_pet_commands_map_native_identity_to_each_clients_actual_bar_slot(self):
        for family in ("retail", "forever"):
            with self.subTest(family=family):
                lua = runtime(True)
                lua.globals().family = family
                lua.execute("""
                    Enum.SpellBookItemType = {Spell = 1, PetAction = 3}
                    Enum.ActionBarSet = family == "forever" and {Mkb = 0, Gamepad = 1} or nil
                    local actionSlot = 4
                    C_ActionBar = {GetPetActionPetBarIndices = function(...)
                        local id, barSet = ...
                        assert(id == 77)
                        if family == "forever" then
                            assert(select("#", ...) == 2 and barSet == Enum.ActionBarSet.Mkb)
                        else
                            assert(select("#", ...) == 1)
                        end
                        return {actionSlot}
                    end}
                    CastPetAction = function() end
                    C_SpellBook = {
                        GetNumSpellBookSkillLines = function() return 0 end,
                        GetSpellBookSkillLineInfo = function() error("no player lines") end,
                        HasPetSpells = function() return 1 end,
                        GetSpellBookItemInfo = function(slot, bank)
                            assert(slot == 1 and bank == Enum.SpellBookSpellBank.Pet)
                            return {itemType = 3, name = "Attack", actionID = 77, iconID = 55}
                        end,
                    }
                    local search = Search("spellbook")
                    local entry = search:Query("attack", options)[1]
                    assert(entry and entry.id == "petaction:77" and entry.petActionID == 77)
                    assert(not entry.spellID and search:EntryID(entry) == nil)
                    assert(entry.spellBookSlot == 1 and entry.spellBookBank == Enum.SpellBookSpellBank.Pet)
                    assert(entry.secure.type == "pet" and entry.secure.action == 4)
                    assert(not entry.secure.spell and not entry.onClick)
                    actionSlot = 7
                    FireEvent("PET_BAR_UPDATE")
                    assert(not search:IsEntryCurrent(entry))
                    assert(search:Query("attack", options)[1].secure.action == 7)
                """)

    def test_off_bar_pet_commands_press_each_clients_native_spellbook_opener(self):
        for family in ("retail", "forever"):
            with self.subTest(family=family):
                lua = runtime(True)
                lua.globals().family = family
                lua.execute("""
                    Enum.SpellBookItemType = {Spell = 1, PetAction = 3}
                    CastPetAction = function() error("no pet bar action") end
                    C_ActionBar = {GetPetActionPetBarIndices = function() return nil end}
                    C_SpellBook = {
                        GetNumSpellBookSkillLines = function() return 0 end,
                        GetSpellBookSkillLineInfo = function() error("no player lines") end,
                        HasPetSpells = function() return 1 end,
                        GetSpellBookItemInfo = function()
                            return {itemType = 3, name = "Stay", actionID = 79, iconID = 56}
                        end,
                        CastSpellBookItem = function() error("must not cast from Lua") end,
                    }
                    PlayerSpellsUtil = setmetatable({}, {__index = function(_, key)
                        error("addon Lua reached PlayerSpellsUtil." .. key)
                    end})
                    PlayerSpellsMicroButton = {name = "PlayerSpellsMicroButton"}
                    SpellbookMicroButton = family == "forever" and {name = "SpellbookMicroButton"} or nil
                    local search = Search("spellbook")
                    local entry = search:Query("stay", options)[1]
                    assert(entry and not entry.passive and not entry.onClick)
                    assert(entry.secure.type == "click" and not entry.secure.action)
                    assert(entry.secure.clickbutton == (SpellbookMicroButton or PlayerSpellsMicroButton))
                    PlayerSpellsMicroButton, SpellbookMicroButton = nil, nil
                    FireEvent("PET_UI_UPDATE")
                    entry = search:Query("stay", options)[1]
                    assert(entry and not entry.secure and not entry.onClick)
                    assert(#mock.errors == 0)
                """)

    def test_toy_search_preserves_native_filters(self):
        lua = runtime(True)
        lua.execute("""
            PlayerHasToy = function(id) return id == 77 end
            C_ToyBox = {
                GetNumFilteredToys = function() return 1 end,
                GetToyFromIndex = function(index) assert(index == 1); return 77 end,
                GetToyInfo = function() return 77, "Visible Toy", 1 end,
                SetFilterString = function() error("must preserve journal search") end,
                SetCollectedShown = function() error("must preserve journal ownership filter") end,
                SetAllSourceTypeFilters = function() error("must preserve journal source filters") end,
                SetAllExpansionTypeFilters = function() error("must preserve journal expansion filters") end,
            }
            C_ToyBoxInfo = {SetDefaultFilters = function() error("must preserve journal filters") end}
            local search = Search("toys")
            assert(search:Query("visible toy", options)[1].id == 77)
            assert(#mock.errors == 0)
        """)


if __name__ == "__main__":
    unittest.main()
