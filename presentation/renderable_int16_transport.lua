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

-- Replaces the four float streams on every surface with base64 Int16 and
-- records how to invert it. Returns the same table, mutated.
function transport.encode(bundle)
    if type(bundle) ~= "table" or type(bundle.surfaces) ~= "table" then return bundle end
    for _, surface in ipairs(bundle.surfaces) do
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
        note = "Each stream decodes as little-endian Int16 divided by its scale.",
    }
    return bundle
end

transport.SCALES = SCALES
return transport
