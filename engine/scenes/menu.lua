-- Generic menu-scene extension point.
--
-- `scene_host` automatically asks engine/scenes/<kind>.lua to register when a
-- scene of that kind is pushed. Menus historically needed no Lua module, but
-- the Developer menu is engine tooling rather than campaign content: the map
-- geometry exporter belongs to the runtime that provides the capability. Keep
-- the visible command/data shape in the scene registry, and keep the actual
-- export implementation in presentation/map_geometry_export.lua.
local menu = {}

local EXPORT_SCENE_ID = "developer_geometry_export"
local EXPORT_COMMAND_ID = "export_map"

local function findScene(loader, id)
    if loader.scenesById and loader.scenesById[id] then return loader.scenesById[id] end
    for _, scene in ipairs(loader.scenes or {}) do
        if scene.id == id then return scene end
    end
    return nil
end

local function addExportScene(loader)
    if findScene(loader, EXPORT_SCENE_ID) then return end
    local scene = {
        id = EXPORT_SCENE_ID,
        name = "Map Geometry Export",
        kind = "menu",
        draw = "windows",
        backdrop = "map",
        config = {
            note = "Engine developer tool: exports the complete current runtime 3D world as OBJ."
        },
        windows = {
            {
                id = "export_result",
                rect = { x = 3, y = 5, w = 26, h = 12 },
                style = "confirm",
                title = "MAP GEOMETRY EXPORT",
                content = {
                    { type = "text", text = "{v.statusText or 'Exporting...'}" }
                }
            },
            {
                id = "help",
                content = {
                    { type = "text", text = "[Confirm / Cancel] Back" }
                }
            }
        },
        hooks = {
            on_enter = {},
            on_select = {
                { cmd = "SCENE_EVENT", kind = "pop" }
            },
            on_cancel = {
                { cmd = "SCENE_EVENT", kind = "pop" }
            }
        }
    }
    table.insert(loader.scenes, scene)
    loader.scenesById = loader.scenesById or {}
    loader.scenesById[scene.id] = scene
end

local function isTitleAction(cmd)
    if type(cmd) ~= "table" or cmd.cmd ~= "IF" or type(cmd["then"]) ~= "table" then return false end
    for _, nested in ipairs(cmd["then"]) do
        if nested.cmd == "RESET_SESSION" then return true end
        if nested.cmd == "SCENE_EVENT" and nested.scene == "title" then return true end
    end
    return false
end

local function addDeveloperCommand(loader)
    local scene = findScene(loader, "developer_menu")
    if not scene then return end
    scene.config = scene.config or {}
    scene.config.developerCommands = scene.config.developerCommands or {}
    local commands = scene.config.developerCommands
    for _, command in ipairs(commands) do
        if command.id == EXPORT_COMMAND_ID then return end
    end

    -- Keep TITLE SCREEN as the final escape hatch. The export action is added
    -- immediately before it and the matching authored selection index moves by
    -- one; all earlier developer commands retain their existing indices.
    local titleIndex = nil
    for index, command in ipairs(commands) do
        if command.id == "title" then titleIndex = index break end
    end
    if not titleIndex or titleIndex ~= #commands then
        error("developer_menu export extension expects TITLE SCREEN to be the final command", 0)
    end
    table.insert(commands, titleIndex, {
        id = EXPORT_COMMAND_ID,
        name = "EXPORT MAP GEOMETRY",
        help = "Export the complete current runtime 3D world as a geometry-only OBJ."
    })
    local exportIndex = titleIndex
    local finalCount = #commands

    scene.hooks = scene.hooks or {}
    local onDown = scene.hooks.on_down
    if type(onDown) == "table" and type(onDown[1]) == "table" and onDown[1].condition then
        onDown[1].condition = "v.idx < " .. tostring(finalCount)
    else
        error("developer_menu export extension could not find the cursor-down bound", 0)
    end

    local onSelect = scene.hooks.on_select
    if type(onSelect) ~= "table" then
        error("developer_menu export extension requires on_select hooks", 0)
    end

    local titleHookIndex = nil
    for index, cmd in ipairs(onSelect) do
        if isTitleAction(cmd) then
            titleHookIndex = index
            cmd.condition = "v._guard == 0 and v.idx == " .. tostring(exportIndex + 1)
            break
        end
    end
    if not titleHookIndex then
        error("developer_menu export extension could not find TITLE SCREEN action", 0)
    end

    table.insert(onSelect, titleHookIndex, {
        cmd = "IF",
        condition = "v._guard == 0 and v.idx == " .. tostring(exportIndex),
        ["then"] = {
            { cmd = "SET_VAR", name = "_guard", value = 1 },
            { cmd = "SCENE_EVENT", kind = "push", scene = EXPORT_SCENE_ID }
        }
    })
end

local function runExport(scene_host, session)
    local state = scene_host.getCurrentState()
    if not state or state.id ~= EXPORT_SCENE_ID or state.v._exportRan then return end
    state.v._exportRan = true

    if not (session and session.currentMapData and session.mapGrid) then
        state.v.statusText = "NO RUNTIME MAP LOADED.\n\nOpen this tool while exploring a 3D map."
        return
    end

    -- Actual geometry/compiler failures stay fail-loud. The only friendly
    -- failure above is the ordinary UX case of invoking the tool without a map.
    local result, err = require("presentation.map_geometry_export").export(session)
    if not result then
        state.v.statusText = "EXPORT FAILED\n\n" .. tostring(err or "Unknown export error")
        return
    end
    state.v.statusText = string.format(
        "EXPORTED OBJ\n%s\n\n%d triangles  %d vertices\n%d groups\n\nTextures are not included yet.",
        result.relativePath, result.triangleCount, result.vertexCount, result.groupCount)
end

function menu.registerKindWindows(scene_host)
    local session = require("engine.session").activeSession
    -- This module is loaded for every menu-kind scene. Installing an engine
    -- developer tool into the shared scene registry during a normal run would
    -- be invisible to the player but would still mutate validation/golden
    -- contexts. Developer launch state is the capability boundary.
    if not (session and session.developerMode == true) then return end

    local loader = require("data.loader")
    addExportScene(loader)
    addDeveloperCommand(loader)
    runExport(scene_host, session)
end

return menu
