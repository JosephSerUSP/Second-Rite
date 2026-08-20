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
check(startX == 5.35 and startY == 5.5, "spawn comes from the package anchor")

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
check(game.townTraversal.x == 5.35, "horizontal movement keeps authored depth fixed")
check(game.worldCameraProjectionWindowOffsetX < 0,
    "right movement drives the projection window left to keep the eye fixed")
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

for _ = 1, 20 do lane.move(game, 1) end
check(game.townTraversal.y <= game.townTraversal.maxY, "right movement clamps at the authored bound")
for _ = 1, 20 do lane.move(game, -1) end
check(game.townTraversal.y >= game.townTraversal.minY, "left movement clamps at the authored bound")

game.townTraversal.y = 5.5
lane.update(game)
local door = lane.interact(game)
check(door and door.instanceId == "town-door-exterior",
    "doorway interaction resolves through the package anchor")
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
check(game.currentMapData.id == 17, "ordinary Event LOAD_MAP enters the interior")
check(firstDoorText[1] == "A narrow apothecary door opens onto the side street.",
    "first doorway visit uses the initial authored branch")

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
check(changedDoorText[1] == "The apothecary has left a fresh sign on the door.",
    "return visit uses the changed authored dialogue branch")

print("=== Bounded Lane Tests: all checks passed ===")
return true
