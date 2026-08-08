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
