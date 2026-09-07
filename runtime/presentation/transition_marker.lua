-- Shared semantic orientation contract for transition-arrow markers.
--
-- The OBJ is authored in the standard runtime model frame: its shaft runs
-- along local +Z after obj_model converts Y-up OBJ into engine Z-up. A lane
-- arrow uses that shaft along world Y; a depth/door arrow uses it along world
-- X. Flat exits never acquire a presentation-only pitch: elevation belongs to
-- an authored traversal contract, not to the marker's camera projection.
local transition_marker = {}

local function requiredDirection(direction)
    if direction ~= "left" and direction ~= "right" and direction ~= "away" then
        error("transition marker direction is unsupported: " .. tostring(direction), 0)
    end
    return direction
end

function transition_marker.worldPoint(direction, vertex, spec)
    direction = requiredDirection(direction)
    spec = spec or {}
    local scale = tonumber(spec.scale) or 1
    local lx = (tonumber(vertex[1]) or 0) * scale
    local ly = (tonumber(vertex[2]) or 0) * scale
    local lz = (tonumber(vertex[3]) or 0) * scale
    local depthX = tonumber(spec.depthX) or 0
    local laneY = tonumber(spec.laneY) or 0
    local groundZ = tonumber(spec.groundZ) or 0
    local baseHeight = tonumber(spec.baseHeight) or 0.02
    local arrowLength = tonumber(spec.arrowLength) or (1.04 * scale)
    local arrowY = tonumber(spec.arrowY) or laneY
    if direction == "left" then
        local tipY = math.max(arrowY, (tonumber(spec.minY) or arrowY) + 0.15)
        tipY = math.min(tipY, (tonumber(spec.maxY) or tipY) - 0.15 - arrowLength)
        return depthX + lx, tipY + (arrowLength - lz), groundZ + baseHeight + ly
    elseif direction == "right" then
        local tipY = math.max(arrowY, (tonumber(spec.minY) or arrowY) + 0.15)
        tipY = math.max(tipY, (tonumber(spec.minY) or tipY) + 0.15 + arrowLength)
        return depthX + lx, tipY - (arrowLength - lz), groundZ + baseHeight + ly
    end
    -- A flat depth exit points through the doorway at ground height. The
    -- local radial axis supplies the marker's small vertical thickness; the
    -- shaft itself must not be tilted toward the sky.
    return depthX - 0.10 * scale + lz, arrowY + lx, groundZ + baseHeight + ly
end

function transition_marker.assertFlatDepthExit(direction, base, tip, tolerance)
    requiredDirection(direction)
    if direction ~= "away" then return true end
    tolerance = tolerance or 0.000001
    if math.abs((tip[3] or 0) - (base[3] or 0)) > tolerance then
        error("flat transition marker depth exit changes elevation", 0)
    end
    return true
end

return transition_marker
