local surface = require("presentation.surface")

local function eq(actual, expected, label)
    assert(actual == expected, label .. ": expected " .. tostring(expected)
        .. ", got " .. tostring(actual))
end

local original = surface.getProfileId()

surface.setProfile("classic")
do
    local cw, ch = surface.compositionSize()
    local rw, rh = surface.renderSize()
    local ox, oy = surface.compositionOrigin()
    eq(cw, 256, "classic composition width")
    eq(ch, 240, "classic composition height")
    eq(rw, 256, "classic render width")
    eq(rh, 240, "classic render height")
    eq(ox, 0, "classic origin x")
    eq(oy, 0, "classic origin y")
end

surface.setProfile("wide")
do
    local rw, rh = surface.renderSize()
    local ox, oy = surface.compositionOrigin()
    eq(rw, 426, "wide render width")
    eq(rh, 240, "wide render height")
    eq(ox, 85, "wide origin x")
    eq(oy, 0, "wide origin y")

    local centerX, horizonY = surface.compositionToRender(128, 70)
    eq(centerX, 213, "wide canonical center")
    eq(horizonY, 70, "wide canonical horizon")

    local cx, cy = surface.renderToComposition(centerX, horizonY)
    eq(cx, 128, "wide inverse x")
    eq(cy, 70, "wide inverse y")

    assert(surface.isInsideComposition(85, 0), "wide composition left edge")
    assert(surface.isInsideComposition(340, 239), "wide composition right edge")
    assert(not surface.isInsideComposition(84, 120), "wide left peripheral world")
    assert(not surface.isInsideComposition(341, 120), "wide right peripheral world")

    local scale, outX, outY = surface.outputTransform(1000, 600)
    eq(scale, 2, "wide integer output scale")
    eq(outX, 74, "wide host offset x")
    eq(outY, 60, "wide host offset y")

    local renderX, renderY = surface.hostToRender(500, 300, scale, outX, outY)
    eq(renderX, 213, "host to wide render x")
    eq(renderY, 120, "host to wide render y")
    local compX, compY = surface.hostToComposition(500, 300, scale, outX, outY)
    eq(compX, 128, "host to composition x")
    eq(compY, 120, "host to composition y")
end

-- A deterministic pixel fixture protects the compositor itself, including the
-- easy-to-miss fact that LÖVE scissors do not follow draw transforms. The
-- canonical crop of Wide must be byte-equivalent to Classic for identical
-- composition-space drawing; only the pixels outside that crop are new.
local function renderCompositionFixture(profileId)
    surface.setProfile(profileId)
    local rw, rh = surface.renderSize()
    local previousCanvas = love.graphics.getCanvas()
    local canvas = love.graphics.newCanvas(rw, rh)

    -- Unit suites share one graphics context. Isolate this fixture from a
    -- caller's transform/scissor/blend state so it proves only the surface
    -- compositor contract, rather than inheriting presentation state from the
    -- suite that happened to run immediately before it.
    love.graphics.push("all")
    love.graphics.origin()
    love.graphics.setScissor()
    love.graphics.setBlendMode("replace", "premultiplied")
    love.graphics.setCanvas(canvas)
    love.graphics.clear(0, 0, 0, 1)
    love.graphics.setColor(0.15, 0.2, 0.3, 1)

    surface.beginComposition()
    love.graphics.rectangle("fill", 0, 0, 256, 240)
    love.graphics.setScissor(16, 16, 48, 40)
    love.graphics.setColor(0.8, 0.35, 0.2, 1)
    love.graphics.rectangle("fill", 0, 0, 96, 72)
    love.graphics.setScissor()
    love.graphics.setColor(0.95, 0.9, 0.5, 1)
    love.graphics.rectangle("fill", 120, 96, 17, 13)
    surface.endComposition()

    love.graphics.setCanvas(previousCanvas)
    love.graphics.pop()
    return canvas:newImageData()
end

local classicFixture = renderCompositionFixture("classic")
local wideFixture = renderCompositionFixture("wide")
for y = 0, 239 do
    for x = 0, 255 do
        local cr, cg, cb, ca = classicFixture:getPixel(x, y)
        local wr, wg, wb, wa = wideFixture:getPixel(x + 85, y)
        assert(cr == wr and cg == wg and cb == wb and ca == wa,
            string.format(
                "wide center crop diverged from classic at %d,%d: classic=(%.4f,%.4f,%.4f,%.4f) wide=(%.4f,%.4f,%.4f,%.4f)",
                x, y, cr, cg, cb, ca, wr, wg, wb, wa))
    end
end
local lr, lg, lb = wideFixture:getPixel(84, 120)
local rr, rg, rb = wideFixture:getPixel(341, 120)
assert(lr == 0 and lg == 0 and lb == 0, "wide left peripheral pixel was composition-painted")
assert(rr == 0 and rg == 0 and rb == 0, "wide right peripheral pixel was composition-painted")

-- This fixture deliberately proves the compositor/UI half of #199's crop
-- invariant. The actual 3D-world crop remains a G5/manual visual check because
-- its pixels are GPU/driver-sensitive and the repository forbids silently
-- replacing screenshot goldens.

-- The registry, rather than a classic/wide conditional, is the extension seam
-- for future asymmetric/tall profiles. Exercise a deliberately upward-biased
-- composition to protect #199's explicit-origin requirement without shipping
-- portrait as a production profile yet.
surface.registerProfile("test_portrait_bias", {
    renderWidth = 256,
    renderHeight = 400,
    compositionOriginX = 0,
    compositionOriginY = 24,
})
surface.setProfile("test_portrait_bias")
do
    local anchorX, anchorY = surface.compositionToRender(128, 70)
    eq(anchorX, 128, "biased profile anchor x")
    eq(anchorY, 94, "biased profile horizon follows composition")
end

local ok = pcall(surface.registerProfile, "test_bad_origin", {
    renderWidth = 300,
    renderHeight = 240,
    compositionOriginX = 60,
    compositionOriginY = 0,
})
assert(not ok, "profile origin outside render surface must fail loudly")

surface.setProfile(original)
print("presentation surface tests passed")
