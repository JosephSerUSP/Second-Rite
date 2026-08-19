-- Consumer-specific structural visibility/finalization policy.
--
-- Authored maps describe structure, never camera/consumer geometry. These
-- profiles live at the resolved-geometry seam so runtime play, authoring tools,
-- and future consumers can ask for the structural faces they are entitled to
-- observe without re-deriving topology in a renderer.
local visibility = {}

local PROFILES = {
    play = {
        name = "play",
        wallTopCaps = false,
        walkableCeilings = true,
        exteriorWallFaces = false,
    },
    -- Overhead gameplay deliberately has its own consumer identity even
    -- though its current static open-top facts match authoring. Gameplay
    -- must be free to gain cutaway/occlusion rules later without making
    -- camera semantics depend on an editor-only visibility profile.
    ["play-overhead"] = {
        name = "play-overhead",
        wallTopCaps = true,
        walkableCeilings = false,
        exteriorWallFaces = true,
    },
    authoring = {
        name = "authoring",
        wallTopCaps = true,
        walkableCeilings = false,
        exteriorWallFaces = true,
    },
}

function visibility.resolve(name)
    name = name or "play"
    local profile = PROFILES[name]
    if not profile then
        error("unknown geometry visibility profile: " .. tostring(name), 0)
    end
    return profile
end

-- A wall side is structurally sealed when another solid wall occupies the
-- adjacent grid cell. That rule predates #291 and remains true for every
-- consumer. A missing neighbour is the map exterior: play cannot reach an
-- outside-in camera, while authoring cameras deliberately can.
function visibility.wallSideDecision(profileName, grid, neighbourX, neighbourY)
    local profile = visibility.resolve(profileName)
    local row = grid and grid[neighbourY]
    local neighbour = row and row[neighbourX] or nil
    if neighbour == "#" then return false, "sealed-solid" end
    if neighbour == nil then
        if profile.exteriorWallFaces then return true, "exterior-retained" end
        return false, "exterior-culled"
    end
    -- Openings, floor cells, and future non-solid structural cell kinds stay
    -- visible. Do not wishfully cull them merely because they are often hidden.
    return true, "non-solid-neighbour"
end

function visibility.walkableCeilingVisible(profileName, ceilingStyle)
    return visibility.resolve(profileName).walkableCeilings
        and ceilingStyle ~= "sky"
end

function visibility.wallTopVisible(profileName)
    return visibility.resolve(profileName).wallTopCaps
end

return visibility
