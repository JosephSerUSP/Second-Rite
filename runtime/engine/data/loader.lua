local json = require("engine.data.json")
local semantic_resources = require("engine.data.semantic_resources")
local rtp_authored_defaults = require("engine.data.rtp_authored_defaults")

local loader = {}

local RUNTIME_DATA_ENV = "THESTRA_RUNTIME_DATA_ROOT"

local function runtimeDataRoot()
    local value = os.getenv and os.getenv(RUNTIME_DATA_ENV) or nil
    if value == nil or value == "" then return "data" end
    value = value:gsub("\\", "/")
    if value:sub(1, 1) == "/" or value:match("^%a:/") then
        error(RUNTIME_DATA_ENV .. " must be Project-relative")
    end
    for segment in value:gmatch("[^/]+") do
        if segment == ".." then
            error(RUNTIME_DATA_ENV .. " must not escape the Project root")
        end
    end
    return value
end

-- The runnable Project still has one semantic data root. Ordinary source
-- development reads data/. Same-root Test Play/Studio preview may point this at
-- an ignored, Project-relative compiled snapshot so engine/assets remain direct
-- while authored data matches the staged/exported player boundary.
loader.root = runtimeDataRoot()

-- Load JSON helper
local function load_json(path)
    local contents, size = love.filesystem.read(path)
    if not contents then
        error("Could not read JSON file: " .. path)
    end
    return json.decode(contents)
end

-- Some Project-authored scenes are intentionally maintained as complete
-- replacements while scene storage is fragmented. This file lives inside the
-- one Project data root; it is not an alternate content root or runtime
-- selection mechanism. Preserve it until its authored-storage migration is
-- handled separately, because the current file contains meaningful scene work.
local function applySceneOverrides()
    local path = loader.root .. "/scene_overrides.json"
    if not love.filesystem.getInfo(path) then return end

    local data = load_json(path)
    local replacements = data and data.sceneReplacements
    if type(replacements) ~= "table" then
        error("scene_overrides.json must contain a sceneReplacements array")
    end

    local indexById = {}
    for index, scene in ipairs(loader.scenes or {}) do
        indexById[scene.id] = index
    end

    for _, scene in ipairs(replacements) do
        if type(scene) ~= "table" or scene.id == nil then
            error("scene_overrides.json contains a replacement without an id")
        end
        local index = indexById[scene.id]
        if not index then
            error("scene_overrides.json cannot replace unknown scene '"
                .. tostring(scene.id) .. "'")
        end
        loader.scenes[index] = scene
    end
end

-- Since #700 the checkout is the Thestra INSTALLATION, not a game: it owns no
-- `data/`, and the runnable Project lives at `projects/<name>/`. A bare
-- `lovec .` therefore cannot work, and used to fail several frames later deep
-- inside the storage layer with
--   `Could not find ordered collection 'units' at data/units/index.json`
-- which names a file nobody asked for and says nothing about the actual
-- mistake. AGENTS.md and README.md both document the rule, but a document is
-- not a diagnostic: agents, CI shims and people all kept re-deriving it from a
-- traceback. Say it once, here, where the wrong root is first observable.
local function assertRunnableProject(root)
    if love.filesystem.getInfo(root) then return end
    if not love.filesystem.getInfo("projects") then return end
    local names = {}
    for _, entry in ipairs(love.filesystem.getDirectoryItems("projects")) do
        if love.filesystem.getInfo("projects/" .. entry .. "/data") then
            names[#names + 1] = entry
        end
    end
    if #names == 0 then return end
    error(([[

this is a Thestra installation root, not a runnable Project.

  no %q here, but these Projects have one: %s

A Project is only runnable once STAGED -- engine code, the Project's data/ and
assets/, and the Effekseer shim united in one directory:

  node tools/ci/stage-project-gates.js --output <stageDir>
  lovec <stageDir> <mode>

Or play the default Project directly:

  run.bat

See AGENTS.md "The repository root is not a game".]]):format(root, table.concat(names, ", ")), 0)
end

function loader.init()
    -- Re-read the process boundary on every reload. No gameplay/runtime state
    -- can redirect this root: only the host-created Project-relative snapshot
    -- environment variable may select compiled data for this subprocess.
    loader.root = runtimeDataRoot()
    assertRunnableProject(loader.root)
    local function J(name) return load_json(loader.root .. "/" .. name) end

    -- Authored combat-capable definitions are Units, stored in the Unit
    -- catalog. Actor is reserved for persistent player-owned identity.
    loader.units = semantic_resources.load(loader.root, "units")

    loader.elements = J("elements.json")
    loader.items = J("items.json")
    loader.maps = semantic_resources.load(loader.root, "maps")
    loader.mapsById = {}
    for index, map in ipairs(loader.maps) do
        local key = tostring(map.id)
        if loader.mapsById[key] then
            error("duplicate authored map id: " .. key)
        end
        loader.mapsById[key] = index
    end
    loader.lore = J("lore.json")
    loader.quests = J("quests.json")
    loader.shops = J("shops.json")
    loader.sounds = J("sounds.json")
    loader.terms = J("terms.json")
    loader.actionSequences = J("actionSequences.json")
    loader.system = J("system.json")
    loader.commonEvents = J("commonEvents.json")
    loader.skills = J("skills.json")
    loader.passives = J("passives.json")
    loader.states = J("states.json")
    loader.roles = J("roles.json")
    -- #390: source development composes the exact pinned RTP semantic registry
    -- with disjoint Project policy. Compiled snapshots/staged Projects contain
    -- the materialized effective engine.json and authored-resolution provenance.
    loader.engine, loader.engineResolution = rtp_authored_defaults.loadEngine(loader.root, loader.system)

    -- Skill use occasion is required authored data. The vocabulary is owned by
    -- engine.json's existing itemScopes registry so runtime, editor surfaces and
    -- authored tooling share one set of words. Reject at the load boundary: a
    -- missing field must never fall back to deriving occasion from charges or
    -- effect shape.
    local validSkillScopes = {}
    local skillScopeNames = {}
    for _, entry in ipairs((loader.engine and loader.engine.itemScopes) or {}) do
        if entry.scope then
            validSkillScopes[entry.scope] = true
            table.insert(skillScopeNames, entry.scope)
        end
    end
    table.sort(skillScopeNames)
    if #skillScopeNames == 0 then
        error("engine.json itemScopes declares no skill use-scope vocabulary")
    end
    local skillScopeList = table.concat(skillScopeNames, ", ")
    for id, skill in pairs(loader.skills or {}) do
        if skill.scope == nil then
            error("skill '" .. tostring(id) .. "' is missing required scope")
        end
        if not validSkillScopes[skill.scope] then
            error("skill '" .. tostring(id) .. "' has unknown scope '"
                .. tostring(skill.scope) .. "' (" .. skillScopeList .. ")")
        end
    end

    -- Phase flows (SPEC S4): scene phase -> command list, run in immediate mode.
    -- Source/Test Play and compiled players both expose the same semantic Flow
    -- object; source-only `_test` projection belongs to the provider/compiler.
    loader.flows = semantic_resources.load(loader.root, "flows")
    -- Troops: what a battle is made of (member slots, rigid or pooled) and its
    -- battle events. `base` is inherited by all of them.
    loader.troops = J("troops.json")
    -- Scenes configuration. Optional same-Project replacements are applied
    -- before the lookup registry is built, so every consumer sees one
    -- canonical resolved scene.
    loader.scenes = semantic_resources.load(loader.root, "scenes")
    applySceneOverrides()

    -- overhaul-7 A1: animations data loaded from JSON
    loader.animations = J("animations.json")
    local animation_player = require("presentation.animation_player")
    animation_player.load(loader.animations)

    -- #591: reusable Event presentation controllers are separate from concrete
    -- battle/VFX animation tracks. Older external Projects remain valid when
    -- the resource is absent: no authored controller means the pre-#591 static
    -- Event presentation path stays exactly as it was.
    local controllerPath = loader.root .. "/animationControllers.json"
    if love.filesystem.getInfo(controllerPath) then
        loader.animationControllers = J("animationControllers.json")
    else
        loader.animationControllers = {}
    end
    require("engine.animation_controller").validateRegistry(loader.animationControllers)

    -- Tilesets are semantic ids here. Source registry layout and compiled
    -- monolith layout are provider concerns, not player/database state.
    loader.tilesets = semantic_resources.load(loader.root, "tilesets")

    -- Icon palettes and key profiles
    loader.iconPalettes = J("iconPalettes.json")
    loader.iconKeyProfiles = J("iconKeyProfiles.json")

    -- Canonical Unit lookup. Unit identity is symbolic-only: numeric IDs were
    -- removed atomically in issue #147 and are not a compatibility surface.
    loader.unitsById = {}
    for index, unit in ipairs(loader.units) do
        if type(unit.id) ~= "string" or unit.id == "" then
            error("authored unit at units collection[" .. tostring(index)
                .. "] must have a non-empty symbolic string id")
        end
        if loader.unitsById[unit.id] then
            error("duplicate authored unit id: " .. tostring(unit.id))
        end
        loader.unitsById[unit.id] = unit
    end
    loader.itemsById = {}
    for _, item in ipairs(loader.items) do
        loader.itemsById[item.id] = item
    end

    loader.scenesById = {}
    for _, scene in ipairs(loader.scenes or {}) do
        loader.scenesById[scene.id] = scene
    end
end

function loader.getTileset(id)
    if not loader.tilesets then return nil end
    local key = (id and tostring(id) ~= "") and tostring(id) or "dungeon_default"
    return loader.tilesets[key] or loader.tilesets["dungeon_default"]
end

function loader.getMapIndex(id)
    if not loader.mapsById then return nil end
    return loader.mapsById[tostring(id)]
end

-- Authored combat-capable definitions are Units. Allegiance is deliberately
-- absent from this lookup.
function loader.getUnit(id)
    return loader.unitsById and loader.unitsById[id]
end

function loader.getUnitByRole(role)
    for _, unit in ipairs(loader.units or {}) do
        if unit.role == role then return unit end
    end
    return nil
end

function loader.getItem(id)
    if not id then return nil end
    local item = loader.itemsById[id]
    if not item and tonumber(id) then
        item = loader.itemsById[tonumber(id)]
    end
    return item
end

function loader.getSkill(id)
    return loader.skills[id]
end

function loader.getPassive(id)
    return loader.passives[id]
end

function loader.getState(id)
    return loader.states[id]
end

function loader.getElement(id)
    return loader.elements and loader.elements[id]
end

function loader.getScene(id)
    return loader.scenesById[id]
end

function loader.getRole(id)
    return loader.roles and loader.roles[id]
end

-- Quests are keyed by string id (JSON object keys); tostring so numeric or
-- string ids both resolve — same convention as the shops/commonEvents
-- lookups in main.lua.
function loader.getQuest(id)
    return loader.quests and loader.quests[tostring(id)]
end

function loader.getLore(id)
    return loader.lore and loader.lore[tostring(id)]
end

-- Looks up a UI/battle string from data/terms.json by dotted path
-- (e.g. "battle.flee_success"); falls back to the engine default when the
-- key is missing so incomplete terms files never crash the game.
function loader.getTerm(path, fallback)
    local node = loader.terms
    for part in path:gmatch("[^%.]+") do
        if type(node) ~= "table" then return fallback end
        node = node[part]
    end
    if type(node) == "string" then return node end
    return fallback
end

-- Like getTerm but for list-valued terms (e.g. menu command label arrays).
function loader.getTermList(path, fallback)
    local node = loader.terms
    for part in path:gmatch("[^%.]+") do
        if type(node) ~= "table" then return fallback end
        node = node[part]
    end
    if type(node) == "table" and #node > 0 then return node end
    return fallback
end

-- getTerm + positional substitution: replaces {0}, {1}, ... with the extra
-- arguments (the same placeholder style terms.json already uses).
function loader.formatTerm(path, fallback, ...)
    local str = loader.getTerm(path, fallback)
    local args = { ... }
    return (str:gsub("{(%d+)}", function(idx)
        local v = args[tonumber(idx) + 1]
        return v ~= nil and tostring(v) or ("{" .. idx .. "}")
    end))
end

return loader