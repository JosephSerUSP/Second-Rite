-- EXPERIMENT (#736/#739): quantized Int16 transport for the Map Renderable Bundle.
--
-- The bundle is ~55 MiB for a 17x17 Map, and essentially all of it is vertex
-- floats serialized as JSON text: 5.7M numbers at full double precision. The
-- runtime renders that at 256x240 with vertexSnapPixels = 1 and ditherLevels =
-- 31, so most of those digits cannot reach a pixel.
--
-- Quantizing alone only recovers about half, because JSON's per-number text is
-- the real cost, not the precision. This carries the same values as packed
-- Int16 streams instead, which measured 54.8 MiB -> ~15 MiB.
--
-- OFF unless SECOND_RITE_RENDERABLE_ENCODING=int16. The default path is
-- untouched, so no committed frame changes without opting in.
--
-- Deliberately NOT chosen for the grids: the screen-space snap. Vertex snapping
-- happens in the vertex shader after projection, so it is not a licence to
-- quantize source geometry to the screen grid. Two other consumers read this
-- bundle at higher fidelity than the game does -- the editor's Three viewport
-- (1440x900, no snapping) and the OBJ/.blend export path -- so the grids below
-- are sized for them, not for the 256x240 target.
local transport = {}

transport.ENV = "SECOND_RITE_RENDERABLE_ENCODING"

-- Declared in the bundle so a consumer never infers a scale.
local SCALES = {
    positions = 256,    -- 1/256 of a map cell
    uvs = 4096,         -- ~1/4096 of the atlas
    normals = 10000,    -- unit vectors
    colors = 4096,      -- lit colours can exceed 1.0, hence the headroom
}

local INT16_MIN, INT16_MAX = -32768, 32767

function transport.requested()
    local value = os.getenv and os.getenv(transport.ENV) or nil
    return value == "int16"
end

local function packStream(values, scale, label)
    local parts, count = {}, #values
    for index = 1, count do
        local quantized = math.floor(values[index] * scale + 0.5)
        if quantized < INT16_MIN or quantized > INT16_MAX then
            -- Fail loud: a silently clamped vertex is a wrong picture, and the
            -- caller can only fix this by choosing a different scale.
            error(string.format(
                "renderable int16 transport: %s value %s exceeds Int16 at scale %d "
                .. "(quantized %d). Choose a coarser scale or keep JSON floats.",
                label, tostring(values[index]), scale, quantized), 0)
        end
        if quantized < 0 then quantized = quantized + 65536 end
        parts[index] = string.char(quantized % 256, math.floor(quantized / 256))
    end
    return love.data.encode("string", "base64", table.concat(parts))
end

local function packIndices(indices, uniqueCount)
    -- Welding is per surface, and the largest surface in a real bundle holds
    -- ~1342 unique vertices, so uint16 indices are the honest width. Fail loud
    -- rather than silently truncating if a surface ever exceeds it.
    if uniqueCount > 65535 then
        error("renderable int16 transport: surface has " .. uniqueCount
            .. " unique vertices, which exceeds uint16 indices", 0)
    end
    local parts = {}
    for i = 1, #indices do
        local v = indices[i]
        parts[i] = string.char(v % 256, math.floor(v / 256))
    end
    return love.data.encode("string", "base64", table.concat(parts))
end

-- Weld identical vertices and emit an index buffer.
--
-- The collector emits a triangle soup: adjacent triangles repeat their shared
-- vertices verbatim. Measured on a 17x17 Map, 480,720 vertices reduce to 95,039
-- unique -- 80% of the payload is duplication, which no amount of quantization
-- touches. map_geometry_export already welds for OBJ (#302); this applies the
-- same idea to the transport.
--
-- Welding on the QUANTIZED integers, not the source floats, is deliberate: it
-- is exactly the equality the consumer will see after decoding, so no vertex is
-- merged that would have decoded differently.
local function weldSurface(surface)
    local positions = surface.positions or {}
    local uvs, normals, colors = surface.uvs or {}, surface.normals or {}, surface.colors or {}
    local vertexCount = math.floor(#positions / 3)
    local q = function(value, scale) return math.floor(value * scale + 0.5) end

    local seen, indices = {}, {}
    local outP, outU, outN, outC = {}, {}, {}, {}
    local unique = 0
    for v = 0, vertexCount - 1 do
        local px, py, pz = q(positions[v * 3 + 1], SCALES.positions),
            q(positions[v * 3 + 2], SCALES.positions), q(positions[v * 3 + 3], SCALES.positions)
        local u1, u2 = q(uvs[v * 2 + 1] or 0, SCALES.uvs), q(uvs[v * 2 + 2] or 0, SCALES.uvs)
        local n1, n2, n3 = q(normals[v * 3 + 1] or 0, SCALES.normals),
            q(normals[v * 3 + 2] or 0, SCALES.normals), q(normals[v * 3 + 3] or 0, SCALES.normals)
        local c1, c2, c3, c4 = q(colors[v * 4 + 1] or 0, SCALES.colors),
            q(colors[v * 4 + 2] or 0, SCALES.colors), q(colors[v * 4 + 3] or 0, SCALES.colors),
            q(colors[v * 4 + 4] or 0, SCALES.colors)
        local key = table.concat({ px, py, pz, u1, u2, n1, n2, n3, c1, c2, c3, c4 }, ",")
        local at = seen[key]
        if not at then
            at = unique
            seen[key] = at
            unique = unique + 1
            outP[#outP + 1] = positions[v * 3 + 1]
            outP[#outP + 1] = positions[v * 3 + 2]
            outP[#outP + 1] = positions[v * 3 + 3]
            outU[#outU + 1] = uvs[v * 2 + 1] or 0
            outU[#outU + 1] = uvs[v * 2 + 2] or 0
            outN[#outN + 1] = normals[v * 3 + 1] or 0
            outN[#outN + 1] = normals[v * 3 + 2] or 0
            outN[#outN + 1] = normals[v * 3 + 3] or 0
            outC[#outC + 1] = colors[v * 4 + 1] or 0
            outC[#outC + 1] = colors[v * 4 + 2] or 0
            outC[#outC + 1] = colors[v * 4 + 3] or 0
            outC[#outC + 1] = colors[v * 4 + 4] or 0
        end
        indices[#indices + 1] = at
    end
    return outP, outU, outN, outC, indices
end

-- Replaces the four float streams on every surface with base64 Int16 and
-- records how to invert it. Returns the same table, mutated.
function transport.encode(bundle)
    if type(bundle) ~= "table" or type(bundle.surfaces) ~= "table" then return bundle end
    for _, surface in ipairs(bundle.surfaces) do
        local p, u, n, c, indices = weldSurface(surface)
        surface.positions, surface.uvs, surface.normals, surface.colors = p, u, n, c
        surface.indices = { kind = "uint16-base64", count = #indices,
            base64 = packIndices(indices, #p / 3) }
        for _, key in ipairs({ "positions", "uvs", "normals", "colors" }) do
            local values = surface[key]
            if type(values) == "table" then
                surface[key] = {
                    kind = "int16-base64",
                    count = #values,
                    base64 = packStream(values, SCALES[key], key),
                }
            end
        end
    end
    bundle.encoding = {
        kind = "int16-base64",
        scales = SCALES,
        indexed = true,
        note = "Streams decode as little-endian Int16 / scale; indices as uint32."
            .. " Expand indices to restore the original triangle soup.",
    }
    return bundle
end

transport.SCALES = SCALES
return transport
