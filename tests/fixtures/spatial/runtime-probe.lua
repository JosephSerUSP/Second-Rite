-- Experimental #1088 probe. Runs only in a disposable canonical Project stage.
local json = require('engine.data.json')
function love.load()
    local ok, err = xpcall(function()
        local input = json.decode(love.filesystem.read('spatial-input.json'))
        local loader = require('engine.data.loader')
        loader.init()
        require('engine.config').load()
        loader.system.dungeon = input.dungeonPolicy
        local exploration = require('engine.exploration')
        local function generate()
            local inspection = {}
            local grid = exploration.generateDungeon(input.map, input.seed, nil, {inspection = inspection})
            local rows = {}
            for i, row in ipairs(grid) do rows[i] = table.concat(row) end
            return {rows = rows, rooms = inspection.rooms, openings = inspection.openings,
                corridors = inspection.corridors}
        end
        local a, b = generate(), generate()
        assert(json.encode(a) == json.encode(b), 'generator repeat differs')
        input.seed = input.seed + 1
        assert(json.encode(a.rows) ~= json.encode(generate().rows), 'seed has no effect')
        local camera = require('presentation.world_camera').resolve(
            {playerX = 4, playerY = 5, playerDir = 'E'}, {profile = 'rpg_ortho'})
        assert(camera.projection == 'orthographic')
        assert(math.abs(camera.projectionScaleX - math.sqrt(0.5)) < 1e-10)
        assert(camera.projectionScaleY == 1)
        local collision = require('presentation.obj_model').parse(input.collisionObj, 'Praca snapshot')
        local vertices = {}
        for _, group in ipairs(collision.groups) do
            for _, v in ipairs(group.vertices) do vertices[#vertices + 1] = {v[1], v[2], v[3]} end
        end
        local output = {dungeon = a, collisionVertices = vertices, camera = {
            profile = camera.profile, projection = camera.projection,
            projectionScale = {camera.projectionScaleX, camera.projectionScaleY},
            pitch = camera.pitch,
        }}
        local file = assert(io.open(input.output, 'wb'))
        file:write(json.encode(output)); file:close()
        print('SPATIAL RUNTIME PROBE OK')
    end, debug.traceback)
    if not ok then print(err) end
    love.event.quit(ok and 0 or 1)
end
