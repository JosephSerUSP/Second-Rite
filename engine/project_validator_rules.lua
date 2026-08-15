-- Project-generic validation for Thestra Projects that do not opt into the
-- installation's legacy/full game regression fixture.
--
-- The historical validator_rules.lua grew as Second Gate's G1 and therefore
-- mixes reusable authored-data checks with concrete game assertions (Pixie,
-- Summoner reserve waves, required battle/quest phases, dungeon policy, etc.).
-- A sparse Project must not acquire that ontology merely to be considered a
-- valid Thestra Project. Keep this pass deliberately small and semantic: it
-- validates the startup graph, literal authored references, and command
-- vocabulary without inventing RPG content.
local validator = {}

local function nonEmptyString(value)
    return type(value) == "string" and value ~= ""
end

local function nonEmptyPhase(loader, host, name)
    local flows = loader.flows
    local phases = flows and flows[host]
    local commands = phases and phases[name]
    return type(commands) == "table" and #commands > 0
end

function validator.run(loader)
    local problems = {}
    local function check(ok, message)
        if not ok then problems[#problems + 1] = message end
        return ok
    end

    check(type(loader.system) == "table", "system.json must contain an object")
    if type(loader.system) == "table" and loader.system.rtp ~= nil then
        check(type(loader.system.rtp) == "table"
                and nonEmptyString(loader.system.rtp.revision),
            "system.rtp.revision must be a non-empty pinned RTP revision")
    end

    local sceneIds = {}
    local hasMapScene = false
    for index, scene in ipairs(loader.scenes or {}) do
        local where = "scene[" .. index .. "]"
        if check(type(scene) == "table", where .. " must be an object") then
            check(nonEmptyString(scene.id), where .. " needs a non-empty id")
            if nonEmptyString(scene.id) then
                check(not sceneIds[scene.id], "duplicate scene id '" .. scene.id .. "'")
                sceneIds[scene.id] = true
            end
            check(nonEmptyString(scene.kind), where .. " needs a non-empty kind")
            if scene.kind == "map" then hasMapScene = true end
            -- presentation/scene_compositor.lua accepts exactly these two
            -- authored surfaces. Letting an absent/unknown mode through G1
            -- means a Project can validate and boot at title, then crash the
            -- first time the player enters that Scene (#520).
            local validDraw = scene.draw == "windows" or scene.draw == "world"
            check(validDraw,
                where .. " ('" .. tostring(scene.id or "?")
                .. "') draw must be 'windows' or 'world', got '"
                .. tostring(scene.draw) .. "'")
            -- A world Scene also names the world renderer it delegates to.
            -- Validation intentionally checks the structural contract rather
            -- than importing presentation.world_renderer into the engine;
            -- unknown named renderers remain a presentation-level hard error.
            if scene.draw == "world" then
                check(nonEmptyString(scene.world),
                    where .. " ('" .. tostring(scene.id or "?")
                    .. "') draw 'world' requires a non-empty world renderer id")
            end
        end
    end

    -- Normal runtime boot currently enters the authored `title` Scene
    -- unconditionally (main.lua). This is a Thestra runtime contract rather
    -- than Second Gate game design, so a Project that cannot satisfy it is not
    -- bootable through the ordinary player path.
    check(loader.getScene and loader.getScene("title") ~= nil,
        "Project is missing required startup scene 'title'")

    -- The Map host unconditionally runs exploration.step after every successful
    -- movement. A Project that owns a Map Scene therefore cannot treat this as
    -- optional extension data: without a resolved non-empty phase it validates
    -- and boots, then crashes on the player's first step (#525).
    if hasMapScene then
        check(nonEmptyPhase(loader, "exploration", "step"),
            "Map Projects require non-empty flow phase 'exploration.step'")

        local hasDangerousMap = false
        for _, map in ipairs(loader.maps or {}) do
            if map.safe ~= true then hasDangerousMap = true break end
        end
        if hasDangerousMap then
            check(nonEmptyPhase(loader, "exploration", "expedition_start"),
                "Projects with dangerous Maps require non-empty flow phase 'exploration.expedition_start'")
        end
    end

    local spawn = type(loader.system) == "table" and loader.system.spawn or nil
    if spawn ~= nil then
        check(type(spawn) == "table", "system.spawn must be an object")
        if type(spawn) == "table" then
            check(spawn.mapId ~= nil, "system.spawn needs mapId")
            if spawn.mapId ~= nil and loader.getMapIndex then
                check(loader.getMapIndex(spawn.mapId) ~= nil,
                    "system.spawn references missing map '" .. tostring(spawn.mapId) .. "'")
            end
            check(type(spawn.x) == "number" and type(spawn.y) == "number",
                "system.spawn x/y must be numeric")
        end
    end

    -- The command registry is inherited Thestra semantics. Project-authored
    -- command trees may use that vocabulary, but a fresh Project must never
    -- gain permission to invent commands just because the full Second Gate G1
    -- suite is not active.
    local commandIds = { FALLBACK = true }
    for _, command in ipairs((loader.engine and loader.engine.commands) or {}) do
        if command.id then commandIds[command.id] = true end
    end

    local function validateCommandTree(node, where, seen)
        if type(node) ~= "table" then return end
        seen = seen or {}
        if seen[node] then return end
        seen[node] = true

        if node.cmd ~= nil then
            check(nonEmptyString(node.cmd), where .. " has a command without a non-empty cmd id")
            if nonEmptyString(node.cmd) then
                check(commandIds[node.cmd] == true,
                    where .. " uses command '" .. tostring(node.cmd)
                    .. "' which is not registered by the resolved engine vocabulary")
            end

            if node.cmd == "SCENE_EVENT" and type(node.scene) == "string"
                    and node.scene ~= "" and not node.scene:find("[%(%)%+%-%*/=]") then
                check(sceneIds[node.scene] == true,
                    where .. " SCENE_EVENT references missing scene '" .. node.scene .. "'")
            elseif node.cmd == "LOAD_MAP" and type(node.mapId) == "number" and loader.getMapIndex then
                check(loader.getMapIndex(node.mapId) ~= nil,
                    where .. " LOAD_MAP references missing map '" .. tostring(node.mapId) .. "'")
            end
        end

        for key, value in pairs(node) do
            if key ~= "meta" then validateCommandTree(value, where .. "." .. tostring(key), seen) end
        end
    end

    for _, scene in ipairs(loader.scenes or {}) do
        validateCommandTree(scene.hooks,
            "scene '" .. tostring(scene.id or "?") .. "' hooks")
    end
    for host, phases in pairs(loader.flows or {}) do
        validateCommandTree(phases, "flow '" .. tostring(host) .. "'")
    end
    for id, commonEvent in pairs(loader.commonEvents or {}) do
        validateCommandTree(commonEvent.commands or commonEvent,
            "common event '" .. tostring(id) .. "'")
    end
    for _, map in ipairs(loader.maps or {}) do
        for eventIndex, event in ipairs(map.events or {}) do
            validateCommandTree(event.commands or event.script,
                "map '" .. tostring(map.id or "?") .. "' event[" .. eventIndex .. "]")
            for pageIndex, page in ipairs(event.pages or {}) do
                validateCommandTree(page.commands or page.script,
                    "map '" .. tostring(map.id or "?") .. "' event[" .. eventIndex
                    .. "] page[" .. pageIndex .. "]")
            end
        end
    end

    -- References inside optional RPG databases are checked only when the
    -- Project actually authors those systems. Empty databases are legitimate.
    for _, unit in ipairs(loader.units or {}) do
        local where = "Unit '" .. tostring(unit.id or "?") .. "'"
        if unit.role ~= nil then
            check(loader.getRole and loader.getRole(unit.role) ~= nil,
                where .. " references missing role '" .. tostring(unit.role) .. "'")
        end
        for _, skillId in ipairs(unit.skills or {}) do
            check(loader.getSkill and loader.getSkill(skillId) ~= nil,
                where .. " references missing skill '" .. tostring(skillId) .. "'")
        end
        for _, passiveId in ipairs(unit.passives or {}) do
            check(loader.getPassive and loader.getPassive(passiveId) ~= nil,
                where .. " references missing passive '" .. tostring(passiveId) .. "'")
        end
        for _, elementId in ipairs(unit.elements or {}) do
            check(loader.getElement and loader.getElement(elementId) ~= nil,
                where .. " references missing element '" .. tostring(elementId) .. "'")
        end
    end

    if #problems > 0 then
        error(table.concat(problems, "\n"), 0)
    end
end

return validator
