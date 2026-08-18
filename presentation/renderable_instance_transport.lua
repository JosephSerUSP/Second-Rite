-- EXPERIMENT (#757): lossless mesh-definition + instance transport for Studio.
--
-- The ordinary Map Renderable Bundle remains the renderer-neutral, fully expanded
-- authority consumed by exports. This module is only enabled at the editor bridge
-- boundary. While the collector is running, addPlacedModel() gives us the exact
-- runtime-resolved model object and group that produced each placed surface.
-- Repeated placements therefore share a definition because the runtime says they
-- share one -- never because Studio hashes or guesses that two meshes look alike.
local transport = {}

transport.ENV = "SECOND_RITE_RENDERABLE_ENCODING"
transport.KIND = "mesh-definitions-v1"

local active = nil

function transport.requested()
    local value = os.getenv and os.getenv(transport.ENV) or nil
    return value == "instances"
end

function transport.begin()
    active = {
        definitions = {},
        byModel = setmetatable({}, { __mode = "k" }),
    }
end

function transport.cancel()
    active = nil
end

function transport.capturing()
    return active ~= nil
end

local function expandedTuple(sourceVertex)
    return {
        sourceVertex[1], sourceVertex[2], sourceVertex[3],
        sourceVertex[4] or 0, sourceVertex[5] or 0,
        sourceVertex[6] or 0, sourceVertex[7] or 0, sourceVertex[8] or 1,
        sourceVertex[9] or 1, sourceVertex[10] or 1,
        sourceVertex[11] or 1, sourceVertex[12] or 1,
    }
end

-- Exact tuple indexing without string formatting or spatial tolerance. Lua
-- numeric table keys use exact numeric equality, so a definition only welds two
-- vertices when all twelve attributes are exactly equal after the same defaults
-- the ordinary collector applies. The index stream preserves triangle order.
local function buildDefinition(modelGroup, id)
    local definition = {
        id = id,
        positions = {},
        uvs = {},
        normals = {},
        colors = {},
        indices = {},
    }
    local root = {}
    local uniqueCount = 0

    for _, sourceVertex in ipairs(modelGroup.vertices or {}) do
        local tuple = expandedTuple(sourceVertex)
        local node = root
        for attribute = 1, 12 do
            local value = tuple[attribute]
            local child = node[value]
            if not child then
                child = {}
                node[value] = child
            end
            node = child
        end

        local index = node.index
        if index == nil then
            index = uniqueCount
            node.index = index
            uniqueCount = uniqueCount + 1

            local p, u, n, c = definition.positions, definition.uvs,
                definition.normals, definition.colors
            p[#p + 1], p[#p + 1], p[#p + 1] = tuple[1], tuple[2], tuple[3]
            u[#u + 1], u[#u + 1] = tuple[4], tuple[5]
            n[#n + 1], n[#n + 1], n[#n + 1] = tuple[6], tuple[7], tuple[8]
            c[#c + 1], c[#c + 1], c[#c + 1], c[#c + 1] =
                tuple[9], tuple[10], tuple[11], tuple[12]
        end
        definition.indices[#definition.indices + 1] = index
    end

    definition.vertexCount = uniqueCount
    definition.triangleCount = math.floor(#definition.indices / 3)
    return definition
end

-- Called only by map_renderable_bundle while capture is active. `model` table
-- identity is the authoritative reuse key: geometry.load/loadAtlasSurface return
-- the exact cached compiled object for repeated runtime geometry. Group identity
-- remains explicit because one compiled model may carry multiple materials.
function transport.capture(model, groupIndex, modelGroup, transform)
    if not active then return nil end
    if type(model) ~= "table" or type(modelGroup) ~= "table" then
        error("renderable instance transport requires a runtime model group", 0)
    end

    local groups = active.byModel[model]
    if not groups then
        groups = {}
        active.byModel[model] = groups
    end

    local definitionId = groups[groupIndex]
    if not definitionId then
        definitionId = string.format("mesh_%03d", #active.definitions + 1)
        groups[groupIndex] = definitionId
        active.definitions[#active.definitions + 1] =
            buildDefinition(modelGroup, definitionId)
    end

    return {
        definition = definitionId,
        transform = transform,
    }
end

function transport.encode(bundle)
    if not active then
        error("renderable instance transport encode called without begin()", 0)
    end
    if type(bundle) ~= "table" or type(bundle.surfaces) ~= "table" then
        active = nil
        return bundle
    end

    local literalSurfaces, placements = {}, {}
    for order, surface in ipairs(bundle.surfaces) do
        local instance = surface._instanceTransport
        surface._instanceTransport = nil
        if instance then
            placements[#placements + 1] = {
                order = order,
                id = surface.id,
                name = surface.name,
                source = surface.source,
                material = surface.material,
                definition = instance.definition,
                transform = instance.transform,
            }
        else
            surface.transportOrder = order
            literalSurfaces[#literalSurfaces + 1] = surface
        end
    end

    bundle.surfaces = literalSurfaces
    bundle.definitions = active.definitions
    bundle.placements = placements
    bundle.encoding = {
        kind = transport.KIND,
        lossless = true,
        indexed = true,
        definitionCount = #active.definitions,
        placementCount = #placements,
        literalSurfaceCount = #literalSurfaces,
    }
    active = nil
    return bundle
end

return transport
