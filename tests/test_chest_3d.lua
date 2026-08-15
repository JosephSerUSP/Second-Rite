local viewport_3d = require("presentation.viewport_3d")
local world_camera = require("presentation.world_camera")
local world_focus = require("presentation.world_focus")
local session = require("engine.session")
local exploration = require("engine.exploration")
local interpreter = require("engine.interpreter")
local savegame = require("engine.savegame")
local validator = require("engine.validator_core")
local resource_reference = require("engine.resource_reference")
local loader = require("data.loader")

print("=== TEST CHEST 3D ===")
local passed, failed = 0, 0
local function check(cond, msg)
    if cond then
        passed = passed + 1
        print("  [PASS] " .. msg)
    else
        failed = failed + 1
        print("  [FAIL] " .. msg)
    end
end

-- 1. Camera Pitch & Unified CPU Camera-Space Depth Helper
local d0 = viewport_3d.cameraSpaceDepth(10, 5, 0, 5, 5, 0.5, 1, 0, 0)
check(math.abs(d0 - 5.0) < 1e-5, "cameraSpaceDepth neutral pitch")

local pitchRad = math.rad(25)
local dPitched = viewport_3d.cameraSpaceDepth(10, 5, 0, 5, 5, 0.5, 1, 0, pitchRad)
local expectedPitched = 5.0 * math.cos(pitchRad) - (-0.5) * math.sin(pitchRad)
check(math.abs(dPitched - expectedPitched) < 1e-5, "cameraSpaceDepth pitched depth calculation")

-- Screen-space horizon & low object direction verification:
-- Positive pitch (looking down) shifts horizon geometry and low floor objects UPWARD on screen.
local horizPitchedPos = 0.0 * math.cos(pitchRad) + 5.0 * math.sin(pitchRad) -- > 0 (moved UP on screen)
local horizPitchedNeg = 0.0 * math.cos(-pitchRad) + 5.0 * math.sin(-pitchRad) -- < 0 (moved DOWN on screen)
check(horizPitchedPos > 0, "Positive pitch shifts horizon upward")
check(horizPitchedNeg < 0, "Negative pitch shifts horizon downward")

-- 1b. #589 resolved camera seam + exact RPG/anamorphic projection metric.
local pitch45 = math.rad(45)
local sqrtHalf = math.sqrt(2) / 2
check(math.abs(world_camera.rpgGridHorizontalScale(pitch45) - sqrtHalf) < 1e-10,
    "45-degree RPG grid correction is sqrt(2)/2")
check(math.abs(world_camera.rpgGridVerticalStretch(pitch45) - math.sqrt(2)) < 1e-10,
    "45-degree equivalent vertical stretch is sqrt(2)")
check(math.abs(world_camera.rpgWallHeightInTiles(pitch45) - 1.0) < 1e-10,
    "45-degree corrected unit wall is one tile high")
check(world_camera.rpgWallHeightInTiles(math.rad(35)) > 1.0
        and world_camera.rpgWallHeightInTiles(math.rad(60)) < 1.0,
    "RPG wall-height metric responds to pitch around the 45-degree unity point")

local invalidCorrectionOk, invalidCorrectionErr = pcall(function()
    world_camera.rpgGridHorizontalScale(0)
end)
check(not invalidCorrectionOk and string.find(tostring(invalidCorrectionErr), "pitch must be", 1, true),
    "Degenerate RPG grid correction fails loud")

local resolvedCamera = world_camera.resolveFirstPerson({
    playerX = 4,
    playerY = 5,
    playerDir = "E",
}, {})
check(resolvedCamera.projection == "perspective" and resolvedCamera.profile == "first_person",
    "Default resolved Map camera names current first-person perspective policy")
check(math.abs(resolvedCamera.x - 4.5) < 1e-10
        and math.abs(resolvedCamera.y - 5.5) < 1e-10
        and math.abs(resolvedCamera.z - 0.5) < 1e-10,
    "Resolved first-person camera preserves current player-eye position")
check(math.abs(resolvedCamera.playerLightX - resolvedCamera.x) < 1e-10
        and math.abs(resolvedCamera.playerLightY - resolvedCamera.y) < 1e-10,
    "First-person player light preserves historical camera-anchored position")
check(resolvedCamera.fogMetric == "camera_depth"
        and world_camera.fogMetricId(resolvedCamera.fogMetric)
            == world_camera.FOG_CAMERA_DEPTH,
    "First-person fog preserves historical camera-forward depth policy")
local historicalFogDepth = world_camera.cameraSpaceDepth(
    10, 5, 0, resolvedCamera.x, resolvedCamera.y, resolvedCamera.z,
    resolvedCamera.dirX, resolvedCamera.dirY, resolvedCamera.pitch)
check(math.abs(world_camera.fogDistanceAt(resolvedCamera, 10, 5, 0)
        - historicalFogDepth) < 1e-10,
    "First-person fog distance remains byte-compatible camera depth")
check(math.abs(resolvedCamera.dirX - 1.0) < 1e-10
        and math.abs(resolvedCamera.dirY) < 1e-10
        and math.abs(resolvedCamera.rightX) < 1e-10
        and math.abs(resolvedCamera.rightY - 1.0) < 1e-10,
    "Resolved first-person camera preserves current cardinal basis")
check(math.abs(resolvedCamera.fovHalfX - 0.75) < 1e-10
        and math.abs(resolvedCamera.fovHalfY - 0.421875) < 1e-10
        and resolvedCamera.nearPlane == 0.05 and resolvedCamera.farPlane == 32.0,
    "Resolved first-person camera preserves current projection constants")
check(resolvedCamera.visibilityProfile == "play",
    "Resolved first-person camera carries current play visibility policy")

local focusedCamera = world_camera.resolveFirstPerson({
    playerX = 4,
    playerY = 5,
    playerDir = "E",
}, {
    doorProgress = 0.5,
    focusOverride = { pitch = pitchRad, fovScale = 0.75, dollyX = 0.2, dollyY = 0 },
})
check(math.abs(focusedCamera.x - (4.5 + 0.5 * 0.22 + 0.2)) < 1e-10
        and math.abs(focusedCamera.y - 5.5) < 1e-10,
    "Resolved camera composes door approach and focus dolly")
check(math.abs(focusedCamera.pitch - pitchRad) < 1e-10
        and math.abs(focusedCamera.fovHalfX - 0.5625) < 1e-10
        and math.abs(focusedCamera.fovHalfY - 0.31640625) < 1e-10,
    "Resolved camera composes focus pitch and FOV")

local squareCamera = world_camera.resolveFirstPerson({
    playerX = 4,
    playerY = 5,
    playerDir = "E",
}, { squareAuthoringCamera = true })
check(math.abs(squareCamera.fovHalfX - 0.75) < 1e-10
        and math.abs(squareCamera.fovHalfY - 0.75) < 1e-10,
    "Resolved camera preserves square room-bake framing")

local cameraDepth = world_camera.cameraSpaceDepth(
    10, 5, 0, 5, 5, 0.5, 1, 0, pitchRad)
check(math.abs(cameraDepth - expectedPitched) < 1e-5,
    "WorldCamera owns the same pitched camera-space depth contract")

-- 1c. #589 phase 2 projection modes: same Map, different eye.
local overheadSession = { playerX = 4, playerY = 5, playerDir = "E" }
local plainOrtho = world_camera.resolve(overheadSession, { profile = "ortho_oblique" })
local rpgOrtho = world_camera.resolve(overheadSession, { profile = "rpg_ortho" })
local plainPerspective = world_camera.resolve(overheadSession, { profile = "perspective_oblique" })
local rpgPerspective = world_camera.resolve(overheadSession, { profile = "rpg_perspective" })
check(plainOrtho.visibilityProfile == "play-overhead"
        and rpgOrtho.visibilityProfile == "play-overhead"
        and plainPerspective.visibilityProfile == "play-overhead"
        and rpgPerspective.visibilityProfile == "play-overhead",
    "Every overhead projection family resolves dedicated play-overhead visibility")
local fallbackWallTopPlan = viewport_3d.resolveWallTopRenderPlan(nil, nil, 4, 7)
check(fallbackWallTopPlan.kind == "fallback"
        and fallbackWallTopPlan.colorScale == 0.72,
    "Live Wall Top plan preserves neutral-gray compatibility fallback")

local fakeWallTopAtlas = { w = 256, h = 256, img = {}, manifest = {
    base = { wallTops = {
        { id = "cap_fixture", atlas = { 3, 1 }, weight = 100 },
    } },
} }
local atlasWallTopPlan = viewport_3d.resolveWallTopRenderPlan(
    fakeWallTopAtlas, fakeWallTopAtlas.manifest, 4, 7)
check(atlasWallTopPlan.kind == "quad"
        and atlasWallTopPlan.texture == fakeWallTopAtlas.img
        and atlasWallTopPlan.variant.id == "cap_fixture"
        and atlasWallTopPlan.colorScale == 1.0,
    "Live Wall Top plan uses authored weighted atlas variant")

local geometryWallTopDef = { base = { wallTops = {
    { id = "cap_geometry", geometry = "assets/geometry/cap_fixture", weight = 100 },
} } }
local geometryWallTopPlan = viewport_3d.resolveWallTopRenderPlan(
    fakeWallTopAtlas, geometryWallTopDef, 4, 7)
check(geometryWallTopPlan.kind == "model"
        and geometryWallTopPlan.spec.geometry == "assets/geometry/cap_fixture"
        and geometryWallTopPlan.spec.coversFace == true,
    "Live Wall Top plan routes image-authored geometry through placed-surface machinery")

local heightData = love.image.newImageData(64, 64)
local heightWallTopAtlas = {
    w = 64, h = 64, img = {}, heightData = heightData, heightMode = "tile",
    tileWidth = 64, tileHeight = 64, heightMapPath = "fixture-height",
    heightMapScale = { wallTop = 0.08 }, heightMapOperation = "add",
    heightMapMeshColumns = 4, heightMapMeshRows = 4,
    heightMapTriangleBudget = 32, heightMapOffset = 0.004,
}
local heightWallTopDef = { base = { wallTops = {
    { id = "cap_height", atlas = { 0, 0 }, weight = 100 },
} } }
local heightWallTopPlan = viewport_3d.resolveWallTopRenderPlan(
    heightWallTopAtlas, heightWallTopDef, 4, 7)
check(heightWallTopPlan.kind == "model"
        and heightWallTopPlan.spec.runtimeSurface
        and heightWallTopPlan.spec.runtimeSurface.spec.surface == "wallTop",
    "Live Wall Top plan reuses generic atlas height-surface compiler")

local viewportSource = love.filesystem.read("presentation/viewport_3d.lua") or ""
check(viewportSource:find("geometryVisibility.wallTopVisible(camera.visibilityProfile)", 1, true)
        and viewportSource:find("pendingWallTopModels", 1, true)
        and viewportSource:find("wall_top_clip", 1, true),
    "Live viewport gates Wall Top materialization through resolved consumer visibility")

check(plainOrtho.projection == "orthographic"
        and world_camera.projectionKindId(plainOrtho.projection)
            == world_camera.PROJECTION_ORTHOGRAPHIC,
    "Overhead orthographic profile resolves independently from Map semantics")
check(rpgOrtho.profile == "rpg_ortho"
        and math.abs(rpgOrtho.projectionScaleX - sqrtHalf) < 1e-10
        and rpgOrtho.projectionScaleY == 1,
    "RPG orthographic profile applies exact sin(pitch) X projection metric")
check(math.abs(rpgOrtho.targetX - 4.5) < 1e-10
        and math.abs(rpgOrtho.targetY - 5.5) < 1e-10
        and overheadSession.playerX == 4 and overheadSession.playerY == 5,
    "Camera profile resolution does not mutate player/map coordinates")
check(math.abs(rpgOrtho.playerLightX - rpgOrtho.targetX) < 1e-10
        and math.abs(rpgOrtho.playerLightY - rpgOrtho.targetY) < 1e-10
        and (math.abs(rpgOrtho.playerLightX - rpgOrtho.x)
            + math.abs(rpgOrtho.playerLightY - rpgOrtho.y)) > 1e-3,
    "Overhead player light follows the player target rather than camera XY")
check(rpgOrtho.fogMetric == "ground_distance"
        and world_camera.fogMetricId(rpgOrtho.fogMetric)
            == world_camera.FOG_GROUND_DISTANCE
        and math.abs(rpgOrtho.fogOriginX - rpgOrtho.targetX) < 1e-10
        and math.abs(rpgOrtho.fogOriginY - rpgOrtho.targetY) < 1e-10,
    "Overhead fog is anchored to gameplay focus rather than camera")
local fogEast = world_camera.fogDistanceAt(
    rpgOrtho, rpgOrtho.targetX + 3, rpgOrtho.targetY, 0)
local fogNorth = world_camera.fogDistanceAt(
    rpgOrtho, rpgOrtho.targetX, rpgOrtho.targetY - 3, 0)
check(math.abs(fogEast - 3) < 1e-10 and math.abs(fogNorth - 3) < 1e-10,
    "Overhead fog is radial in ground space, independent of camera-forward axis")
local plainRight, plainForward = world_camera.localGroundPixelScales(plainOrtho, 256, 144)
local rpgRight, rpgForward = world_camera.localGroundPixelScales(rpgOrtho, 256, 144)
check(plainRight > plainForward,
    "Uncorrected 45-degree orthographic grid visibly squashes camera-forward cells")
check(math.abs(rpgRight - rpgForward) < 1e-10,
    "Corrected 45-degree RPG orthographic grid has equal screen-pixel basis scales")
check(plainPerspective.projection == "perspective"
        and rpgPerspective.projection == "perspective",
    "Oblique perspective profiles share the same camera contract")
local perspectiveRight, perspectiveForward = world_camera.localGroundPixelScales(
    rpgPerspective, 256, 144, rpgPerspective.focusDepth)
check(math.abs(perspectiveRight - perspectiveForward) < 1e-10,
    "Anamorphic perspective is locally square at the optical target")
check(math.abs(rpgPerspective.projectionScaleX - sqrtHalf) < 1e-10,
    "Perspective RPG calibration uses the same exact sin(pitch) metric")

-- 1d. Overhead focus composition and pitched static-model clipping.
local neutralFocusOverhead = world_camera.resolve(overheadSession, {
    profile = "rpg_ortho",
    pitch = pitch45,
    focusOverride = { pitch = 0, fovScale = 1, dollyX = 0, dollyY = 0 },
})
check(math.abs(neutralFocusOverhead.pitch - pitch45) < 1e-10,
    "Neutral world_focus pitch does not erase overhead base pitch")
local focusedOverhead = world_camera.resolve(overheadSession, {
    profile = "rpg_ortho",
    pitch = pitch45,
    focusOverride = { pitch = math.rad(10), fovScale = 1, dollyX = 0, dollyY = 0 },
})
check(math.abs(focusedOverhead.pitch - math.rad(55)) < 1e-10,
    "world_focus pitch composes as an offset over overhead base pitch")

local pitchedBounds = viewport_3d.classifyBoundsToNear(
    { minX = 1, maxX = 2, minY = 0, maxY = 1 },
    0, 0, 1, 0, 0.05, 1, pitch45)
check(pitchedBounds == nil,
    "XY-only static bounds defer to exact vertices for pitched cameras")

local function worldVertex(x, y, z)
    return { x, y, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, z }
end
local pitchedTriangle = {
    worldVertex(1, 0, 0),
    worldVertex(1, 0, 3),
    worldVertex(2, 0, 0),
}
local _, neutralClipCount = viewport_3d.clipTrianglesToNear(
    pitchedTriangle, 0, 0, 1, 0, 0.05, {}, 1, 0)
local _, pitchedClipCount = viewport_3d.clipTrianglesToNear(
    pitchedTriangle, 0, 0, 1, 0, 0.05, {}, 1, pitch45)
check(neutralClipCount == 3 and pitchedClipCount == 6,
    "Static model near clipping uses WorldHeight under pitched camera depth")

local cachedPose = {
    cameraX = 0, cameraY = 0, cameraZ = 1,
    dirX = 1, dirY = 0, cameraPitch = pitch45, nearPlane = 0.005,
}
check(viewport_3d.sameNearClipPose(cachedPose, 0, 0, 1, 0, 0.005, 1, pitch45)
        and not viewport_3d.sameNearClipPose(cachedPose, 0, 0, 1, 0, 0.005, 1.1, pitch45)
        and not viewport_3d.sameNearClipPose(cachedPose, 0, 0, 1, 0, 0.005, 1, math.rad(35)),
    "Static near-clip cache identity includes camera height and pitch")

-- 2. Presentation Resolution (3-State Map/Page & Common Event Canonical Absence)
local mockLoader = {
    commonEvents = {
        ["12"] = {
            id = 12,
            name = "Chest",
            model = "assets/models/dungeon/dungeon_chest.obj",
            interactionFocus = { kind = "low_prop" },
            sprite = "assets/sprites/OBJ_TreasureChest_001.png"
        }
    }
}
local mockSession = { loader = mockLoader }

-- Base event inherits from CE
local baseEv = { scriptId = 12 }
local pres1 = viewport_3d.resolveEventPresentation(baseEv, mockSession)
check(pres1.visual == "model", "Base event resolves model from CE")
check(pres1.model == "assets/models/dungeon/dungeon_chest.obj", "Model path resolves correctly")
check(pres1.interactionFocus and pres1.interactionFocus.kind == "low_prop", "Focus preset resolves correctly")

-- Page overrides model with false (suppressed) -> falls back to sprite
local evWithPage = {
    scriptId = 12,
    pages = {
        { model = false, sprite = "assets/sprites/OBJ_TreasureChest_001.png" }
    }
}
local pres2 = viewport_3d.resolveEventPresentation(evWithPage, mockSession)
check(pres2.visual == "sprite", "Page suppressing model falls back to sprite")

-- 3. collectEventModelPlacements(session) Helper
local testMap = {
    id = "test_map_3d",
    events = {
        { id = 1, x = 3, y = 4, scriptId = 12 },
        { id = 2, x = 5, y = 6, sprite = "assets/sprites/OBJ_TreasureChest_001.png" }
    }
}
mockSession.currentMapData = testMap
local placements = viewport_3d.collectEventModelPlacements(mockSession)
check(#placements == 1, "collectEventModelPlacements returns 1 model placement")
check(placements[1].x == 4.5 and placements[1].y == 5.5, "Model placement cell center coordinates correct")
check(placements[1].model == "assets/models/dungeon/dungeon_chest.obj", "Model placement model path matches")

-- 4. Fail-Loud Focus Error Propagation & State Reset in world_focus
local okUnknown, errUnknown = pcall(function()
    world_focus.begin("non_existent_preset", { x = 1, y = 1 }, mockSession, nil)
end)
check(not okUnknown and string.find(tostring(errUnknown), "unknown focus preset"), "Unknown focus preset fails loud")

world_focus.begin({ kind = "low_prop" }, { x = 1, y = 1 }, mockSession, function()
    error("Simulated event failure inside focus callback", 0)
end)

local okUpdate, errUpdate = pcall(function()
    world_focus.update(0.3) -- triggers duration finish and fires callback
end)
check(not okUpdate and string.find(tostring(errUpdate), "Simulated event failure"), "Focus update re-throws callback error loud")
check(not world_focus.isActive(), "Focus state resets after callback error")


-- 4b. Focus operation ownership, validation and cancellation.
check(world_focus.hasPreset("low_prop"), "Known focus preset is discoverable")
check(not world_focus.hasPreset("missing"), "Unknown focus preset is not discoverable")

local badCallbackOk, badCallbackErr = pcall(function()
    world_focus.begin("low_prop", { x = 1, y = 1 }, mockSession, "not a callback")
end)
check(not badCallbackOk and string.find(tostring(badCallbackErr), "callback must be"),
    "Non-function focus callback fails loud")

local badTargetOk, badTargetErr = pcall(function()
    world_focus.begin("low_prop", { x = "1", y = 1 }, mockSession, nil)
end)
check(not badTargetOk and string.find(tostring(badTargetErr), "targetCoords"),
    "Malformed focus coordinates fail loud")

local firstOp
local replacementOp
firstOp = world_focus.begin("low_prop", { x = 1, y = 1 }, mockSession, function()
    replacementOp = world_focus.begin("low_prop", { x = 2, y = 2 }, mockSession, nil)
end)
world_focus.update(0.3)
check(replacementOp and replacementOp ~= firstOp,
    "Callback-created focus receives a distinct operation token")
check(world_focus.getOperationId() == replacementOp and world_focus.isActive(),
    "Completed old focus does not release callback-created replacement")
check(not world_focus.cancel(firstOp), "Stale operation cannot cancel current focus")
check(world_focus.cancel(replacementOp) and not world_focus.isActive(),
    "Current operation token cancels focus")

local mapSession = { currentMapIndex = 0 }
world_focus.begin("low_prop", { x = 1, y = 1 }, mapSession, nil)
mapSession.currentMapIndex = 1
world_focus.update(0.01)
check(not world_focus.isActive(), "Map change cancels focus even from map index zero")

local errorReplacement
world_focus.begin("low_prop", { x = 1, y = 1 }, mockSession, function()
    errorReplacement = world_focus.begin("low_prop", { x = 3, y = 3 }, mockSession, nil)
    error("replacement owner failure", 0)
end)
local replacementErrorOk, replacementError = pcall(function() world_focus.update(0.3) end)
check(not replacementErrorOk and string.find(tostring(replacementError), "replacement owner failure"),
    "Reentrant callback error remains fail-loud")
check(world_focus.getOperationId() == errorReplacement and world_focus.isActive(),
    "Old callback error does not reset replacement focus")
world_focus.cancel(errorReplacement)

-- 4c. Holding Phase & Release Lifecycle
local holdOp = world_focus.begin("low_prop", { x = 1, y = 1 }, mockSession, nil)
world_focus.update(0.3)
check(world_focus.getPhase() == "holding", "Focus enters holding phase after focus_in finishes")
check(world_focus.getCameraOverride().pitch > 0, "Camera maintains pitch during holding phase")
world_focus.update(1.0)
check(world_focus.getPhase() == "holding", "Focus remains in holding phase indefinitely until released")

check(world_focus.release(holdOp), "world_focus.release transitions holding to focus_out")
check(world_focus.getPhase() == "focus_out", "Phase is focus_out after release")
world_focus.update(0.3)
check(not world_focus.isActive(), "Focus resets to idle after focus_out completes")

-- 5. Exact emptyCtx Assertion for CHANGE_ITEM random
local emptyMapSession = {
    currentMapData = { id = "empty_map", treasures = {} },
    loader = mockLoader
}
local emptyCtx = {
    session = emptyMapSession,
    loader = mockLoader,
    events = {}
}

local okRandom, errRandom = pcall(function()
    interpreter.runImmediate({ { cmd = "CHANGE_ITEM", item = "random", count = 1 } }, emptyCtx)
end)
check(not okRandom and string.find(tostring(errRandom), "missing or empty treasures array"), "CHANGE_ITEM random on empty treasures fails loud")

-- 6. Multi-Floor Save/Load Persistence Lifecycle Test
local s = session.GameSession.new(loader)
s:initializeStartingParty()
exploration.loadMap(s, 1) -- Load Floor 1

-- Find or insert chest event on Floor 1
local f1Events = s.currentMapData.events or {}
local chestEv = nil
for _, e in ipairs(f1Events) do
    if e.scriptId == 12 then chestEv = e break end
end
if not chestEv then
    chestEv = { id = 999, x = 2, y = 2, scriptId = 12 }
    table.insert(f1Events, chestEv)
    s.currentMapData.events = f1Events
end

-- Erase chest event on Floor 1 via ERASE_EVENT command
interpreter.runImmediate({ { cmd = "ERASE_EVENT" } }, { session = s, eventId = chestEv.id })

-- Transfer to Floor 2 (which saves Floor 1 state into s.mapStates[1])
exploration.loadMap(s, 2)
check(s.currentMapIndex == 2, "Session transferred to Floor 2")

-- Save session on Floor 2
savegame.save(s, loader, "map", "test_chest_save")

-- Load saved game
local rawSave = savegame.load("test_chest_save", loader)
check(rawSave ~= nil, "Saved game data exists")
local loadedSession, loadedScene = savegame.deserialize(rawSave, loader)
check(loadedSession.currentMapIndex == 2, "Loaded session starts on Floor 2")

-- Return to Floor 1 and assert chest remains erased
exploration.loadMap(loadedSession, 1)
local activeEventsF1 = loadedSession.currentMapData.events or {}
local foundChest = false
for _, e in ipairs(activeEventsF1) do
    if e.id == chestEv.id then foundChest = true break end
end
check(not foundChest, "Chest event remains erased on Floor 1 after save/load cycle")

-- Cleanup test save
savegame.delete("test_chest_save")

-- 7. Validator Regression Tests
local badLoader1 = {}
for k, v in pairs(loader) do badLoader1[k] = v end
badLoader1.maps = {
    {
        id = 1, name = "Bad Treasures Map",
        treasures = { [1] = "1", [3] = "2" }, -- Sparse array hole!
        events = {}
    }
}
local okVal1, errVal1 = pcall(function() validator.run(badLoader1) end)
check(not okVal1 and string.find(tostring(errVal1), "is sparse at index 2"), "Validator catches sparse treasures array")

local badLoader2 = {}
for k, v in pairs(loader) do badLoader2[k] = v end
badLoader2.maps = {
    {
        id = 1, name = "Missing Treasures Map",
        events = {
            { x = 1, y = 1, commands = { { cmd = "CHANGE_ITEM", item = "random" } } }
        }
    }
}
local okVal2, errVal2 = pcall(function() validator.run(badLoader2) end)
check(not okVal2 and string.find(tostring(errVal2), "missing or empty treasures array"), "Validator catches missing treasures array when random loot used")

-- 7b. Authored resource-reference validation (#353).
local okCurrent, errCurrent = pcall(function() validator.run(loader) end)
check(okCurrent, "Canonical validator accepts current legitimate authored resource references"
    .. (okCurrent and "" or (": " .. tostring(errCurrent))))
check(loader.commonEvents["4"].sprite == nil,
    "Recruit Creature has no dead default sprite; recruit host owns presentation")

local chestSpriteOk = resource_reference.required("sprite",
    "assets/sprites/OBJ_TreasureChest_001.png")
check(chestSpriteOk, "Shared sprite resolver accepts authored chest sprite")

local chestModelOk = resource_reference.required("file",
    "assets/models/dungeon/dungeon_chest.obj")
check(chestModelOk, "Shared file resolver accepts authored chest model")

local panoramaOk = resource_reference.required("panorama", "fog_001")
check(panoramaOk, "Panorama shorthand resolves through authored resource contract")

local locationArtOk = resource_reference.required("location_art", "st_maria_chapel.png")
check(locationArtOk, "Location-art shorthand resolves through authored resource contract")

local optionalOmittedOk = resource_reference.optional("file", nil)
local optionalSuppressedOk = resource_reference.optional("file", false)
check(optionalOmittedOk and optionalSuppressedOk,
    "Optional omitted and explicitly suppressed resource references remain legal")

local embeddedOk, embeddedResolved = resource_reference.required("tileset_texture", nil, {
    id = "embedded_test",
    definition = { textureImage = {} }
})
check(embeddedOk and embeddedResolved == resource_reference.EMBEDDED,
    "Embedded/generated tileset texture remains legal without a filesystem path")

local plantedResolverOk = resource_reference.required("sprite",
    "assets/sprites/__issue_353_missing__.png")
check(not plantedResolverOk, "Missing required sprite is rejected by shared resolver")

local badAssetLoader = {}
for k, v in pairs(loader) do badAssetLoader[k] = v end
badAssetLoader.commonEvents = {}
for k, v in pairs(loader.commonEvents) do badAssetLoader.commonEvents[k] = v end
local badCommonEvent = {}
for k, v in pairs(loader.commonEvents["12"]) do badCommonEvent[k] = v end
badCommonEvent.sprite = "assets/sprites/__issue_353_missing__.png"
badAssetLoader.commonEvents["12"] = badCommonEvent

local okMissingAsset, errMissingAsset = pcall(function()
    validator.run(badAssetLoader)
end)
local missingAssetText = tostring(errMissingAsset)
check(not okMissingAsset
        and string.find(missingAssetText, "common event '12'.sprite", 1, true)
        and string.find(missingAssetText, "__issue_353_missing__.png", 1, true),
    "Canonical validator fails loudly on planted missing common-event sprite")

require("tests.fail_fast")("test_chest_3d", failed, passed)
