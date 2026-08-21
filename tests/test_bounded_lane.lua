-- Bounded-lane traversal is a provider capability, not a replacement Map.
local loader = require("engine.data.loader")
local session = require("engine.session")
local exploration = require("engine.exploration")
local lane = require("engine.bounded_lane")
local interpreter = require("engine.interpreter")
local director = require("engine.director")

local function check(condition, message)
    if not condition then error("CHECK FAILED: " .. message, 2) end
end

loader.init()
local game = session.GameSession.new(loader)
game:initializeStartingParty()
exploration.loadMap(game, loader.getMapIndex(16))

check(lane.isActive(game), "town proof map selects bounded_lane")
check(game.townTraversal.environment.manifest.contractVersion == 1,
    "runtime reads the baked environment manifest")
local startX, startY = game.townTraversal.x, game.townTraversal.y
check(startX == 7.8 and startY == 5.5, "spawn comes from the package anchor")

local worldCamera = require("presentation.world_camera")
local cameraAtStart = worldCamera.resolve(game, {
    profile = "town_sideview",
    authoredCamera = game.townTraversal.camera,
    projectionFrame = { targetWidth = 426, targetHeight = 240,
        compositionWidth = 256, canonicalCenterX = 213, canonicalHorizonY = 110 },
})
local moved = lane.move(game, 1)
check(moved and game.townTraversal.y > startY,
    "right movement uses the camera-right world axis")
check(game.townTraversal.x == 7.8, "horizontal movement keeps authored depth fixed")
check(game.townTraversal.cameraTargetOffsetX < 0,
    "right movement drives the projection window target left to keep the eye fixed")
check(game.worldCameraProjectionWindowOffsetX == cameraAtStart.projectionWindowOffsetX,
    "camera tracking keeps its current offset until the interpolation update")
local cameraAfterMove = worldCamera.resolve(game, {
    profile = "town_sideview",
    authoredCamera = game.townTraversal.camera,
    projectionFrame = { targetWidth = 426, targetHeight = 240,
        compositionWidth = 256, canonicalCenterX = 213, canonicalHorizonY = 110 },
})
check(cameraAfterMove.x == cameraAtStart.x and cameraAfterMove.y == cameraAtStart.y
        and cameraAfterMove.z == cameraAtStart.z,
    "projection-window tracking leaves the camera eye invariant")
check(cameraAfterMove.fovHalfX == cameraAtStart.fovHalfX,
    "projection-window tracking leaves the lens/FOV invariant")
lane.update(game, 0.15)
check(game.worldCameraProjectionWindowOffsetX < 0,
    "camera tracking interpolates toward the projection-window target")

for _ = 1, 20 do lane.move(game, 1) end
check(game.townTraversal.y <= game.townTraversal.maxY, "right movement clamps at the authored bound")
for _ = 1, 20 do lane.move(game, -1) end
check(game.townTraversal.y >= game.townTraversal.minY, "left movement clamps at the authored bound")

game.townTraversal.y = 5.5
lane.update(game)
local door = lane.interact(game)
check(door and door.instanceId == "town-church-entrance",
    "church interaction resolves through the package anchor")
check(game.townTraversal.z == -1.5, "provider has no jump/gravity state")

local function runAuthoredEvent(event)
    local ctx = { session = game, loader = loader, events = {},
        party = game.party, event = event }
    local graph = interpreter.runInteractive(event.commands, ctx)
    local walker = director.GraphWalker.new(game, graph)
    local texts = {}
    local guard = 0
    while walker:getCurrentNode() do
        guard = guard + 1
        check(guard < 32, "authored event graph does not terminate")
        local node = walker:getCurrentNode()
        if node.type == "TEXT" then
            texts[#texts + 1] = node.content
            walker:advance()
        elseif node.type == "ACTION" and node.action == "RUN_IMMEDIATE" then
            interpreter.runImmediate(node.commands, ctx)
            walker:advance()
        else
            error("CHECK FAILED: unexpected town proof event node " .. tostring(node.type), 2)
        end
    end
    return texts
end

local firstDoorText = runAuthoredEvent(door)
check(game.currentMapData.id == 2, "church Event LOAD_MAP enters the Labyrinth")
check(firstDoorText[1] == "The church is the center of St. Maria. Beneath its altar, the Labyrinth of Thestra begins.",
    "church doorway uses the initial authored branch")

exploration.loadMap(game, loader.getMapIndex(16))
local sideDoor
for _, event in ipairs(game.currentMapData.events or {}) do
    if event.instanceId == "town-apothecary-door" then sideDoor = event end
end
check(sideDoor ~= nil, "town retains an authored side-door event")
local sideDoorText = runAuthoredEvent(sideDoor)
check(game.currentMapData.id == 17, "side-door Event LOAD_MAP enters the interior")
check(sideDoorText[1] == "The side door leads into the apothecary's warm room.",
    "side doorway uses its authored introduction")
local interiorNpc = game.currentMapData.events[1]
check(interiorNpc.instanceId == "town-apothecary-npc", "interior has the authored NPC")
runAuthoredEvent(interiorNpc)
check(game.flags.town_room_changed == true, "interior Event owns the changed-return flag")

local interiorDoor = game.currentMapData.events[2]
runAuthoredEvent(interiorDoor)
check(game.currentMapData.id == 16, "ordinary Event LOAD_MAP returns to the exterior")
game.townTraversal.y = 5.5
lane.update(game)
local changedDoor = lane.interact(game)
local changedDoorText = runAuthoredEvent(changedDoor)
check(game.currentMapData.id == 2, "returning to the church still enters the Labyrinth")
check(changedDoorText[1] == "The church is the center of St. Maria. Beneath its altar, the Labyrinth of Thestra begins.",
    "return visit preserves the church doorway dialogue")

print("=== Bounded Lane Tests: all checks passed ===")
return true
