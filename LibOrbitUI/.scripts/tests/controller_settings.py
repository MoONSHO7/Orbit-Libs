"""Exercise always-on controller setting ownership with Lua 5.1."""

from pathlib import Path

from lupa.lua51 import LuaRuntime

RUNTIME = Path(__file__).resolve().parents[2] / "LibOrbitUI-1.0"


def load(lua, relative, addon):
    lua.execute((RUNTIME / relative).read_text(encoding="utf-8"), "LibOrbitUI", addon)


def main():
    lua = LuaRuntime()
    lua.execute(r"""
        table.freeze = function(value) return value end
        function issecretvalue() return false end
        function Mixin(target, mixin)
            for key, value in pairs(mixin) do target[key] = value end
            return target
        end
        addon = { LibOrbitUI = {} }
    """)
    addon = lua.globals().addon
    load(lua, "Core/SettingsStore.lua", addon)
    load(lua, "Core/Controller.lua", addon)
    lua.execute(r"""
        local UI = addon.LibOrbitUI
        local defaults = { Enabled = false, Scale = 100 }
        local store = UI.SettingsStore:Create(defaults)
        local controller = UI.Controller:Create({
            name = "AlwaysOn",
            defaults = defaults,
            context = {},
            events = {},
            store = store,
            alwaysEnabled = true,
        })
        assert(defaults.Enabled == nil)
        assert(controller:IsEnabled())
        assert(store:Initialize({ version = 1, settings = {}, collections = {} }))
        local ok, err = store:Set(1, "Enabled", true)
        assert(ok == nil and err == "Invalid or undeclared LibOrbitUI setting")

        local ordinaryDefaults = { Scale = 100 }
        local ordinaryStore = UI.SettingsStore:Create(ordinaryDefaults)
        local ordinary = UI.Controller:Create({
            name = "Ordinary",
            defaults = ordinaryDefaults,
            context = {},
            events = {},
            store = ordinaryStore,
        })
        assert(ordinaryDefaults.Enabled == true)
        assert(ordinaryStore:Initialize({ version = 1, settings = {}, collections = {} }))
        assert(ordinary:IsEnabled())
    """)
    print("Controller settings: always-on ownership passed; Lua 5.1 simulated APIs.")


if __name__ == "__main__":
    main()
