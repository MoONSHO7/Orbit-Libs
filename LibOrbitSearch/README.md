# LibOrbitSearch

## Description
The independently versioned, UI-less search engine shared by Orbit addons: source registry, index builds, matching, provider merge and recents.

## Purpose
Keep one implementation of search ranking and one registry of search sources, so each addon keeps its own search box while any addon can contribute sources another addon's search includes.

## Implementation
`LibOrbitSearch-1.0/` is the authored runtime directory, loaded through `LibOrbitSearch-1.0.xml` after LibStub. Orbit embeds it through the `Orbit/Core/Libs/LibOrbitSearch-1.0` junction and Orbit-Compass through `Libs/LibOrbitSearch-1.0`; editing either path edits these files. Consumer fetch tooling materializes pinned runtime files for clean-checkout validation and packaging.

`.pkgmeta` defines the runtime package and excludes documentation and development metadata. A path-filtered workflow releases relevant changes pushed to Orbit-Libs `main` under `LibOrbitSearch-MAJOR.MINOR` tags, starting at 1.0. Its ZIP contains only the Lua, XML and license under `LibOrbitSearch-1.0/`, with a SHA256 sidecar.

`.scripts/tests/search_engine.py` runs the runtime through Lupa's Lua 5.1 (`python -m pip install lupa`): registry, rebuild notifications, matching, provider lifecycle, reentrancy, recents, typed ids and embedded upgrades. `client_contracts.py` covers missing native contracts, per-consumer event demand, source states/action retirement, all ten native sources and asynchronous lookup. Orbit's search bridge/host/presenter and row-validity suites cover consumer integration. Mocks do not certify Blizzard APIs, taint or rendering.

## Gotchas
- Consumers pin a full commit from a completed `LibOrbitSearch-*` [GitHub release](https://github.com/MoONSHO7/Orbit-Libs/releases) with `path: LibOrbitSearch/LibOrbitSearch-1.0`. Verify publication and runtime assets before updating consumers; release numbers are independent of `lib.API`.
- All Rights Reserved, like LibOrbitUI; both this project and its runtime directory carry the notice.
- The library owns no frames beyond event listeners, no saved variables and no localized strings; kind labels, item keyword synonyms and recents storage come from each consumer.

## References
[Runtime contract](LibOrbitSearch-1.0/README.md), [release workflow](../.github/workflows/README.md), [.pkgmeta](.pkgmeta), [license](LICENSE).
