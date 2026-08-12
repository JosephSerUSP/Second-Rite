package.path = package.path .. ";./?.lua;./engine/?.lua"

local function expectError(label, needle, fn)
    local ok, err = pcall(fn)
    if ok then error(label .. ": expected an error") end
    if needle and not tostring(err):find(needle, 1, true) then
        error(label .. ": expected error containing '" .. needle .. "', got: " .. tostring(err))
    end
end

do
    local originalLove = _G.love
    local originalJson = package.loaded["data.json"]
    local originalStorage = package.loaded["data.authored_storage"]

    local decoded = {}
    local files = {}
    local directories = {}

    local function reset()
        decoded = {}
        files = {}
        directories = {}
    end

    local function addFile(path, value)
        files[path] = true
        decoded[path] = value
    end

    local function addDirectory(path, names)
        directories[path] = names
    end

    local manifest = {
        version = 1,
        resources = {
            system = { kind = "document", representation = "monolith", bulkEditable = true },
            scenes = { kind = "ordered_collection", representation = "fragments", bulkEditable = true },
            maps = { kind = "ordered_collection", representation = "fragments", bulkEditable = true },
            widgets = { kind = "keyed_registry", representation = "fragments", bulkEditable = false },
            chapters = { kind = "ordered_collection", representation = "fragments", bulkEditable = false },
            flows = { kind = "semantic_config", representation = "fragments", modules = { "battle", "quest" }, bulkEditable = true },
        },
    }

    package.loaded["data.json"] = {
        decode = function(token)
            local value = decoded[token]
            if value == nil then error("missing decoded fixture for " .. tostring(token)) end
            return value
        end,
        encode = function() return "<encoded>" end,
    }
    _G.love = {
        filesystem = {
            read = function(path)
                if files[path] then return path end
                return nil
            end,
            getInfo = function(path)
                if files[path] then return { type = "file" } end
                if directories[path] then return { type = "directory" } end
                return nil
            end,
            getDirectoryItems = function(path)
                local source = directories[path] or {}
                local copy = {}
                for index, name in ipairs(source) do copy[index] = name end
                return copy
            end,
        },
    }
    package.loaded["data.authored_storage"] = nil

    local ok, err = pcall(function()
        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        local storage = require("data.authored_storage")

        assert(storage.resourceSpec("scenes").kind == "ordered_collection",
            "scene semantic kind did not come from shared manifest")
        assert(storage.resourceSpec("scenes").representation == "fragments",
            "scenes must use the activated fragmented representation")
        local bulk = storage.bulkEditableResources()
        assert(bulk[1] == "flows" and bulk[2] == "maps" and bulk[3] == "scenes" and bulk[4] == "system",
            "bulk-editable resource list was not manifest-derived and sorted")

        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        addDirectory("data/widgets", { "z-storage-name.json", "a-storage-name.json", "README.md" })
        addFile("data/widgets/z-storage-name.json", { id = "alpha", value = 1 })
        addFile("data/widgets/a-storage-name.json", { id = "omega", value = 2 })
        local registry, mode = storage.loadRegistry("data", "widgets")
        assert(mode == "fragments", "registry fragment mode not reported")
        assert(registry.alpha.value == 1 and registry.omega.value == 2,
            "registry did not derive keys from record.id")
        local registryFiles, registryFilesMode = storage.authoritativeFiles("data", "widgets")
        assert(registryFilesMode == "fragments", "registry provenance mode not reported")
        assert(registryFiles[1] == "data/widgets/a-storage-name.json"
            and registryFiles[2] == "data/widgets/z-storage-name.json",
            "registry provenance was not deterministic")

        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        addDirectory("data/scenes", { "index.json", "fragment.json" })
        addFile("data/scenes/index.json", { files = { "fragment.json" } })
        addFile("data/scenes/fragment.json", { id = "fragment", value = 4 })
        local scenes, sceneMode = storage.loadOrderedCollection("data", "scenes")
        assert(sceneMode == "fragments" and scenes[1].id == "fragment",
            "manifest representation did not activate scene fragments")
        addFile("data/scenes.json", { { id = "legacy", value = 3 } })
        expectError("scene dual source", "both fragment storage and legacy monolith", function()
            storage.loadOrderedCollection("data", "scenes")
        end)

        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        addDirectory("data/widgets", { "one.json", "two.json" })
        addFile("data/widgets/one.json", { id = "same" })
        addFile("data/widgets/two.json", { id = "same" })
        expectError("duplicate registry id", "duplicate id 'same'", function()
            storage.loadRegistry("data", "widgets")
        end)

        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        addDirectory("data/maps", { "index.json", "second.json", "first.json" })
        addFile("data/maps/index.json", { files = { "second.json", "first.json" } })
        addFile("data/maps/second.json", { id = 2 })
        addFile("data/maps/first.json", { id = 1 })
        local ordered, orderedMode = storage.loadOrderedCollection("data", "maps")
        assert(orderedMode == "fragments", "ordered fragment mode not reported")
        assert(ordered[1].id == 2 and ordered[2].id == 1,
            "ordered collection did not preserve manifest order")

        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        addDirectory("data/chapters", { "stale.json" })
        addFile("data/chapters/stale.json", { id = "stale" })
        local writes, removals = {}, {}
        local adapter = {
            writeJson = function(path, value) writes[path] = value end,
            remove = function(path) table.insert(removals, path) end,
        }
        local writeMode = storage.writeResource("data", "chapters", {
            { id = "opening", value = 1 },
            { id = "boss room", value = 2 },
        }, adapter)
        assert(writeMode == "fragments", "ordered write mode not reported")
        assert(writes["data/chapters/opening.json"].id == "opening",
            "ordered writer did not emit stable safe-id filename")
        assert(writes["data/chapters/boss-room--626f737320726f6f6d.json"].id == "boss room",
            "ordered writer did not emit deterministic encoded collision-safe filename")
        assert(writes["data/chapters/index.json"].files[1] == "opening.json"
            and writes["data/chapters/index.json"].files[2] == "boss-room--626f737320726f6f6d.json",
            "ordered writer index did not preserve collection order")
        assert(removals[1] == "data/chapters/stale.json", "ordered writer did not remove stale fragment")

        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        addDirectory("data/chapters", { "existing.json" })
        addFile("data/chapters/existing.json", { id = "existing" })
        local mutationCount = 0
        local invalidAdapter = {
            writeJson = function() mutationCount = mutationCount + 1 end,
            remove = function() mutationCount = mutationCount + 1 end,
        }
        expectError("invalid ordered write", "duplicate id 'same'", function()
            storage.writeResource("data", "chapters", { { id = "same" }, { id = "same" } }, invalidAdapter)
        end)
        assert(mutationCount == 0, "invalid payload mutated storage before full validation")

        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        addDirectory("data/maps", { "index.json", "one.json", "two.json" })
        addFile("data/maps/index.json", { files = { "one.json", "two.json" } })
        addFile("data/maps/one.json", { id = 1, value = "one" })
        addFile("data/maps/two.json", { id = 2, value = "two" })
        local snapshotValue = nil
        storage.snapshotResource("data", "maps", "versions/maps.json", {
            writeJson = function(path, value)
                assert(path == "versions/maps.json", "snapshot destination changed")
                snapshotValue = value
            end,
            remove = function() end,
        })
        assert(snapshotValue[1].id == 1 and snapshotValue[2].id == 2,
            "fragment-backed snapshot did not reassemble canonical collection")

        reset()
        addFile("data/authored_storage_manifest.json", manifest)
        addDirectory("data/flows", { "battle.json", "quest.json" })
        addFile("data/flows/battle.json", { round_start = {} })
        addFile("data/flows/quest.json", { offer = {} })
        local flows, flowMode = storage.loadSemanticConfig("data", "flows")
        assert(flowMode == "fragments" and flows.battle.round_start and flows.quest.offer,
            "semantic config did not reassemble named domains")
        local flowWrites = {}
        storage.writeResource("data", "flows", flows, {
            writeJson = function(path, value) flowWrites[path] = value end,
            remove = function() end,
        })
        assert(flowWrites["data/flows/battle.json"] and flowWrites["data/flows/quest.json"],
            "semantic config writer did not keep domain files separate")
    end)

    package.loaded["data.authored_storage"] = originalStorage
    package.loaded["data.json"] = originalJson
    _G.love = originalLove

    if not ok then error(err) end
    print("=== Authored storage manifest: 13 passed, 0 failed ===")
end

-- ENGINE-STATE consumes semantic resources from the initialized loader rather
-- than guessing their physical files. This fixture deliberately gives the
-- filesystem no authored JSON at all: fragmented Flow/Scene/Map values and
-- monolithic Common Event/Troop values exist only as canonical loader data.
do
    local originalLove = _G.love
    local originalEngineState = package.loaded["engine.engine_state"]
    local reads = {}

    _G.love = {
        filesystem = {
            getDirectoryItems = function() return {} end,
            getInfo = function() return nil end,
            read = function(path)
                reads[#reads + 1] = path
                return nil
            end,
        },
    }
    package.loaded["engine.engine_state"] = nil

    local ok, err = pcall(function()
        local engine_state = require("engine.engine_state")
        local traitCodes = {
            "FLEE_CHANCE_BONUS", "GOLD_DIGGER", "MOVE_HEAL", "PARASITE",
            "POST_BATTLE_HEAL", "SYMBIOSIS",
            "FLOW_ONLY", "SCENE_ONLY", "COMMON_ONLY", "MAP_ONLY", "TROOP_ONLY",
            "ASSIGNED_ONLY", "UNIT_ASSIGNED_ONLY",
        }
        local registryTraits = {}
        for _, code in ipairs(traitCodes) do registryTraits[#registryTraits + 1] = { code = code } end

        local assignedTraits = {}
        for _, code in ipairs(traitCodes) do
            if code ~= "UNIT_ASSIGNED_ONLY" then assignedTraits[#assignedTraits + 1] = code end
        end

        local loader = {
            root = "data",
            engine = { commands = {}, effectTypes = {}, traitCodes = registryTraits, metaKeys = {} },
            flows = {
                battle = {
                    round_end = {
                        {
                            condition = "party.trait.FLEE_CHANCE_BONUS + party.trait.GOLD_DIGGER + ally.trait.SYMBIOSIS + ally.trait.PARASITE + ally.trait.FLOW_ONLY > 0",
                            trait = "POST_BATTLE_HEAL",
                        },
                    },
                },
                exploration = { step = { { trait = "MOVE_HEAL" } } },
            },
            scenes = {
                { id = "fixture", kind = "menu", draw = "windows", hooks = { open = { { trait = "SCENE_ONLY" } } } },
            },
            commonEvents = { fixture = { commands = { { trait = "COMMON_ONLY" } } } },
            maps = { { id = "fixture-map", events = { { commands = { { trait = "MAP_ONLY" } } } } } },
            troops = { base = { events = { { commands = { { trait = "TROOP_ONLY" } } } } } },
            passives = { fixture = { traits = assignedTraits } },
            items = {},
            units = { { id = "fragmented-unit", traits = { "UNIT_ASSIGNED_ONLY" } } },
            states = {},
            skills = {},
            roles = {},
            elements = {},
            shops = {},
            quests = {},
            lore = {},
            animations = {},
            tilesets = {},
        }

        local report = engine_state.build(loader)
        local assignedLine = report:match("%- trait codes %(assigned%):[^\n]+")
        assert(assignedLine == "- trait codes (assigned): `ASSIGNED_ONLY`, `UNIT_ASSIGNED_ONLY`",
            "assignment/consumption census drifted: " .. tostring(assignedLine))

        for _, code in ipairs({
            "FLEE_CHANCE_BONUS", "GOLD_DIGGER", "MOVE_HEAL", "PARASITE",
            "POST_BATTLE_HEAL", "SYMBIOSIS", "FLOW_ONLY", "SCENE_ONLY",
            "COMMON_ONLY", "MAP_ONLY", "TROOP_ONLY",
        }) do
            assert(not assignedLine:find(code, 1, true),
                code .. " was consumed by behavior but still classified assigned-only")
        end

        for _, path in ipairs(reads) do
            assert(not path:match("%.json$"),
                "ENGINE-STATE census bypassed semantic loader data and read physical JSON: " .. path)
        end
    end)

    package.loaded["engine.engine_state"] = originalEngineState
    _G.love = originalLove

    if not ok then error(err) end
    print("=== ENGINE-STATE semantic registry census: 1 passed, 0 failed ===")
end
