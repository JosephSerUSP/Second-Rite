local TILE = 64
local ATLAS = 128

local function image(path)
    local data = love.image.newImageData(path)
    assert(data:getWidth() >= TILE and data:getHeight() >= TILE, path .. " is smaller than one tile")
    return data
end

local function blank(r, g, b, a)
    local data = love.image.newImageData(ATLAS, ATLAS)
    data:mapPixel(function() return r, g, b, a end)
    return data
end

local function copyCell(source, sourceRow, sourceCol, target, targetRow, targetCol)
    local sx0, sy0 = sourceCol * TILE, sourceRow * TILE
    local tx0, ty0 = targetCol * TILE, targetRow * TILE
    for y = 0, TILE - 1 do
        for x = 0, TILE - 1 do
            target:setPixel(tx0 + x, ty0 + y, source:getPixel(sx0 + x, sy0 + y))
        end
    end
end

local function assertCellEqual(source, sourceRow, sourceCol, target, targetRow, targetCol, label)
    local sx0, sy0 = sourceCol * TILE, sourceRow * TILE
    local tx0, ty0 = targetCol * TILE, targetRow * TILE
    for y = 0, TILE - 1 do
        for x = 0, TILE - 1 do
            local sr, sg, sb, sa = source:getPixel(sx0 + x, sy0 + y)
            local tr, tg, tb, ta = target:getPixel(tx0 + x, ty0 + y)
            if math.abs(sr - tr) > 1e-6 or math.abs(sg - tg) > 1e-6
                or math.abs(sb - tb) > 1e-6 or math.abs(sa - ta) > 1e-6 then
                error(label .. " cell mismatch at " .. x .. "," .. y)
            end
        end
    end
end

local function save(data, name)
    local encoded = data:encode("png")
    assert(love.filesystem.write(name, encoded:getString()))
    assert(love.filesystem.getInfo(name), "failed to save " .. name)
end

local function makeBundle(kind, sources)
    local albedo = blank(0, 0, 0, 1)
    local height = blank(0.5, 0.5, 0.5, 1)
    local glow = blank(0, 0, 0, 1)

    -- Runtime target follows today's dungeon_default 2x2 role layout:
    -- [0,0] ceiling, [0,1] floor, [1,0] wall, [1,1] door.
    copyCell(sources.dungeon, 0, 0, albedo, 0, 0)
    copyCell(sources.dungeon, 0, 1, albedo, 0, 1)
    copyCell(sources.dungeon, 1, 1, albedo, 1, 1)
    copyCell(sources.dungeonHeight, 0, 0, height, 0, 0)
    copyCell(sources.dungeonHeight, 0, 1, height, 0, 1)
    copyCell(sources.dungeonHeight, 1, 1, height, 1, 1)

    if kind == "mixed" then
        copyCell(sources.bellroot, 1, 1, albedo, 1, 0)
        copyCell(sources.bellrootHeight, 1, 1, height, 1, 0)
        copyCell(sources.bellrootGlow, 1, 1, glow, 1, 0)
        assertCellEqual(sources.bellroot, 1, 1, albedo, 1, 0, "mixed Bellroot wall albedo")
        assertCellEqual(sources.bellrootHeight, 1, 1, height, 1, 0, "mixed Bellroot wall height")
        assertCellEqual(sources.bellrootGlow, 1, 1, glow, 1, 0, "mixed Bellroot wall emission")
    elseif kind == "dungeon" then
        copyCell(sources.dungeon, 1, 0, albedo, 1, 0)
        copyCell(sources.dungeonHeight, 1, 0, height, 1, 0)
        assertCellEqual(sources.dungeon, 1, 0, albedo, 1, 0, "dungeon wall albedo")
        assertCellEqual(sources.dungeonHeight, 1, 0, height, 1, 0, "dungeon wall height")
    else
        error("unknown bundle kind " .. tostring(kind))
    end

    assertCellEqual(sources.dungeon, 0, 1, albedo, 0, 1, kind .. " dungeon floor")
    assertCellEqual(sources.dungeon, 0, 0, albedo, 0, 0, kind .. " dungeon ceiling")

    save(albedo, kind .. "-albedo.png")
    save(height, kind .. "-height.png")
    save(glow, kind .. "-glow.png")
end

local function makeZoneBundle(sources)
    local albedo = blank(0, 0, 0, 1)
    local height = blank(0.5, 0.5, 0.5, 1)
    local glow = blank(0, 0, 0, 1)

    -- Compatibility bundle for the face-owned zone experiment:
    -- [0,0] dungeon ceiling, [0,1] dungeon floor,
    -- [1,0] dungeon/default wall, [1,1] Bellroot/crypt wall.
    copyCell(sources.dungeon, 0, 0, albedo, 0, 0)
    copyCell(sources.dungeon, 0, 1, albedo, 0, 1)
    copyCell(sources.dungeon, 1, 0, albedo, 1, 0)
    copyCell(sources.bellroot, 1, 1, albedo, 1, 1)

    copyCell(sources.dungeonHeight, 0, 0, height, 0, 0)
    copyCell(sources.dungeonHeight, 0, 1, height, 0, 1)
    copyCell(sources.dungeonHeight, 1, 0, height, 1, 0)
    copyCell(sources.bellrootHeight, 1, 1, height, 1, 1)
    copyCell(sources.bellrootGlow, 1, 1, glow, 1, 1)

    assertCellEqual(sources.dungeon, 1, 0, albedo, 1, 0, "zone default wall")
    assertCellEqual(sources.bellroot, 1, 1, albedo, 1, 1, "zone crypt wall")
    assertCellEqual(sources.dungeonHeight, 1, 0, height, 1, 0, "zone default wall height")
    assertCellEqual(sources.bellrootHeight, 1, 1, height, 1, 1, "zone crypt wall height")
    assertCellEqual(sources.bellrootGlow, 1, 1, glow, 1, 1, "zone crypt wall emission")

    save(albedo, "zone-albedo.png")
    save(height, "zone-height.png")
    save(glow, "zone-glow.png")
end

function love.load()
    local sources = {
        dungeon = image("dungeon.png"),
        dungeonHeight = image("dungeon-height.png"),
        bellroot = image("bellroot.png"),
        bellrootHeight = image("bellroot-height.png"),
        bellrootGlow = image("bellroot-glow.png"),
    }

    makeBundle("dungeon", sources)
    makeBundle("mixed", sources)
    makeZoneBundle(sources)

    local provenance = table.concat({
        "#558 Surface+Palette runtime normalization",
        "mixed target[0,0] ceiling <- dungeon atlas [0,0]",
        "mixed target[0,1] floor <- dungeon atlas [0,1]",
        "mixed target[1,0] wall <- Bellroot atlas [1,1] / dungeon atlas [1,0] control",
        "mixed target[1,1] door <- dungeon atlas [1,1]",
        "zone target[1,0] default wall <- dungeon atlas [1,0]",
        "zone target[1,1] crypt wall <- Bellroot atlas [1,1]",
        "height follows each source Surface independently",
        "emission follows Bellroot wall independently; unassigned runtime cells are black",
        "authored source atlases remain unchanged; these 2x2 bundles are derived runtime data",
    }, "\n") .. "\n"
    assert(love.filesystem.write("provenance.txt", provenance))

    print("SURFACE_PALETTE_PACK OK save=" .. love.filesystem.getSaveDirectory())
    print("SURFACE_PALETTE_PACK sources=2 runtimeBundles=3 authoredMergePrecedence=none")
    love.event.quit(0)
end
