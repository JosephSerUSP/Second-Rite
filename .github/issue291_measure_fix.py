from pathlib import Path
p = Path('tests/test_map_geometry_export.lua')
text = p.read_text(encoding='utf-8')
old = '''local function printMeasurement(mapIndex)
    local session = Session.GameSession.new(loader)
    session:initializeStartingParty()
    local savedTime = os.time
    os.time = function() return 1735689600 + mapIndex end
    local ok, err = pcall(exploration.loadMap, session, mapIndex,
        { seed = 1735689600 + mapIndex })
    os.time = savedTime
    if not ok then error(err, 0) end
    viewport_3d.init()
    local playBundle = assert(renderable.collect(session, "play"))
    local authoringBundle = assert(renderable.collect(session, "authoring"))
    local wall = playBundle.stats.visibility or {}
    print(string.format(
        "PROFILE MEASURE map=%d play surfaces=%d triangles=%d vertices=%d wallFaces=%d preProfileWallFaces=%d sealed=%d exteriorCulled=%d",
        mapIndex, playBundle.stats.surfaceCount, playBundle.stats.triangleCount,
        playBundle.stats.vertexCount, wall.emittedFaces or 0,
        wall.preProfileExposedFaces or 0, wall.culledSealedFaces or 0,
        wall.culledExteriorFaces or 0))
    print(string.format(
        "PROFILE MEASURE map=%d authoring surfaces=%d triangles=%d vertices=%d wallFaces=%d wallTops=%d ceilings=%d",
        mapIndex, authoringBundle.stats.surfaceCount, authoringBundle.stats.triangleCount,
        authoringBundle.stats.vertexCount,
        (authoringBundle.stats.visibility or {}).emittedFaces or 0,
        (authoringBundle.stats.bySurfaceRole["wall-top"] or {}).surfaceCount or 0,
        (authoringBundle.stats.bySurfaceRole.ceiling or {}).surfaceCount or 0))
end'''
new = '''local function printMeasurement(mapId)
    local mapIndex
    for index, map in ipairs(loader.maps or {}) do
        if tostring(map.id) == tostring(mapId) then mapIndex = index break end
    end
    if not mapIndex then error("measurement map not found: " .. tostring(mapId), 0) end
    local session = Session.GameSession.new(loader)
    session:initializeStartingParty()
    local seed = 1735689600 + tonumber(mapId)
    local savedTime = os.time
    os.time = function() return seed end
    local ok, err = pcall(exploration.loadMap, session, mapIndex, { seed = seed })
    os.time = savedTime
    if not ok then error(err, 0) end
    viewport_3d.init()
    local playBundle = assert(renderable.collect(session, "play"))
    local authoringBundle = assert(renderable.collect(session, "authoring"))
    local wall = playBundle.stats.visibility or {}
    print(string.format(
        "PROFILE MEASURE map=%d play surfaces=%d triangles=%d vertices=%d wallFaces=%d preProfileWallFaces=%d sealed=%d exteriorCulled=%d",
        mapId, playBundle.stats.surfaceCount, playBundle.stats.triangleCount,
        playBundle.stats.vertexCount, wall.emittedFaces or 0,
        wall.preProfileExposedFaces or 0, wall.culledSealedFaces or 0,
        wall.culledExteriorFaces or 0))
    print(string.format(
        "PROFILE MEASURE map=%d authoring surfaces=%d triangles=%d vertices=%d wallFaces=%d wallTops=%d ceilings=%d",
        mapId, authoringBundle.stats.surfaceCount, authoringBundle.stats.triangleCount,
        authoringBundle.stats.vertexCount,
        (authoringBundle.stats.visibility or {}).emittedFaces or 0,
        (authoringBundle.stats.bySurfaceRole["wall-top"] or {}).surfaceCount or 0,
        (authoringBundle.stats.bySurfaceRole.ceiling or {}).surfaceCount or 0))
end'''
if text.count(old) != 1:
    raise SystemExit(f'expected one measurement helper, found {text.count(old)}')
p.write_text(text.replace(old, new, 1), encoding='utf-8')
