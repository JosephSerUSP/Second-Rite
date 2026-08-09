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

surface.setProfile("four_three")
do
    local rw, rh = surface.renderSize()
    local ox, oy = surface.compositionOrigin()
    eq(rw, 320, "4:3 render width")
    eq(rh, 240, "4:3 render height")
    eq(ox, 32, "4:3 origin x")
    eq(oy, 0, "4:3 origin y")

    local centerX, horizonY = surface.compositionToRender(128, 70)
    eq(centerX, 160, "4:3 canonical center")
    eq(horizonY, 70, "4:3 canonical horizon")

    local cx, cy = surface.renderToComposition(centerX, horizonY)
    eq(cx, 128, "4:3 inverse x")
    eq(cy, 70, "4:3 inverse y")

    assert(surface.isInsideComposition(32, 0), "4:3 composition left edge")
    assert(surface.isInsideComposition(287, 239), "4:3 composition right edge")
    assert(not surface.isInsideComposition(31, 120), "4:3 left peripheral world")
    assert(not surface.isInsideComposition(288, 120), "4:3 right peripheral world")

    local scale, outX, outY = surface.outputTransform(960, 720)
    eq(scale, 3, "4:3 integer output scale")
    eq(outX, 0, "4:3 host offset x")
    eq(outY, 0, "4:3 host offset y")
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
-- canonical crop of every wider horizontal surface must be byte-equivalent to
-- Classic for identical composition-space drawing; only the peripheral pixels
-- are new.
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
local fourThreeFixture = renderCompositionFixture("four_three")
local wideFixture = renderCompositionFixture("wide")
for y = 0, 239 do
    for x = 0, 255 do
        local cr, cg, cb, ca = classicFixture:getPixel(x, y)
        local fr, fg, fb, fa = fourThreeFixture:getPixel(x + 32, y)
        assert(cr == fr and cg == fg and cb == fb and ca == fa,
            string.format(
                "4:3 center crop diverged from classic at %d,%d: classic=(%.4f,%.4f,%.4f,%.4f) 4:3=(%.4f,%.4f,%.4f,%.4f)",
                x, y, cr, cg, cb, ca, fr, fg, fb, fa))

        local wr, wg, wb, wa = wideFixture:getPixel(x + 85, y)
        assert(cr == wr and cg == wg and cb == wb and ca == wa,
            string.format(
                "wide center crop diverged from classic at %d,%d: classic=(%.4f,%.4f,%.4f,%.4f) wide=(%.4f,%.4f,%.4f,%.4f)",
                x, y, cr, cg, cb, ca, wr, wg, wb, wa))
    end
end
local flr, flg, flb = fourThreeFixture:getPixel(31, 120)
local frr, frg, frb = fourThreeFixture:getPixel(288, 120)
assert(flr == 0 and flg == 0 and flb == 0, "4:3 left peripheral pixel was composition-painted")
assert(frr == 0 and frg == 0 and frb == 0, "4:3 right peripheral pixel was composition-painted")
local lr, lg, lb = wideFixture:getPixel(84, 120)
local rr, rg, rb = wideFixture:getPixel(341, 120)
assert(lr == 0 and lg == 0 and lb == 0, "wide left peripheral pixel was composition-painted")
assert(rr == 0 and rg == 0 and rb == 0, "wide right peripheral pixel was composition-painted")

-- Real 3D world pixels are intentionally not asserted here. G5 owns world
-- image verification because textured rasterization is GPU/driver-sensitive;
-- its surface-crop check compares Classic and Wide in one renderer process.

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

-- #200: the platform touch module ships representative mobile profiles while
-- keeping every controller target outside the guaranteed canonical frame.
local touch_gamepad = require("presentation.touch_gamepad")
local virtual_input = require("engine.virtual_input")

surface.setProfile("mobile_landscape")
do
    local rw, rh = surface.renderSize()
    local ox, oy = surface.compositionOrigin()
    eq(rw, 426, "mobile landscape width")
    eq(rh, 240, "mobile landscape height")
    eq(ox, 85, "mobile landscape centered origin x")
    eq(oy, 0, "mobile landscape origin y")
    local layout = touch_gamepad.layout()
    eq(layout.orientation, "landscape", "mobile landscape orientation")
    assert(#layout.buttons >= 8, "mobile landscape exposes full logical controller")
    for _, button in ipairs(layout.buttons) do
        local x = button.shape == "circle" and button.x or (button.x + button.w / 2)
        local y = button.shape == "circle" and button.y or (button.y + button.h / 2)
        assert(not surface.isInsideComposition(x, y),
            "mobile landscape target overlaps canonical frame: " .. tostring(button.button))
    end
end

surface.setProfile("mobile_portrait")
do
    local rw, rh = surface.renderSize()
    local ox, oy = surface.compositionOrigin()
    eq(rw, 256, "mobile portrait width")
    eq(rh, 426, "mobile portrait height")
    eq(ox, 0, "mobile portrait origin x")
    eq(oy, 24, "mobile portrait is biased upward")
    local layout = touch_gamepad.layout()
    eq(layout.orientation, "portrait", "mobile portrait orientation")
    assert(#layout.buttons >= 8, "mobile portrait exposes full logical controller")
    for _, button in ipairs(layout.buttons) do
        local x = button.shape == "circle" and button.x or (button.x + button.w / 2)
        local y = button.shape == "circle" and button.y or (button.y + button.h / 2)
        assert(not surface.isInsideComposition(x, y),
            "mobile portrait target overlaps canonical frame: " .. tostring(button.button))
    end
end

-- Semantic lifecycle: multi-touch direction + action, deterministic held repeat,
-- direction changes while held, release, and focus-loss style clearing.
virtual_input.clear()
local fired = {}
local function dispatch(button) fired[#fired + 1] = button end
virtual_input.press("dir", "UP")
virtual_input.press("face", "A")
assert(virtual_input.isDown("UP") and virtual_input.isDown("A"), "multi-touch logical hold")
virtual_input.update(0, dispatch, 0.30, 0.06)
eq(fired[1], "UP", "touch-down directional press")
eq(fired[2], "A", "touch-down action press")
virtual_input.update(0.31, dispatch, 0.30, 0.06)
eq(fired[3], "UP", "held directional repeat")
virtual_input.move("dir", "RIGHT")
assert(not virtual_input.isDown("UP") and virtual_input.isDown("RIGHT"),
    "direction changes while touch remains active")
virtual_input.update(0, dispatch, 0.30, 0.06)
eq(fired[#fired], "RIGHT", "moved touch emits new logical direction")
virtual_input.release("face")
virtual_input.release("dir")
assert(not virtual_input.isDown("A") and not virtual_input.isDown("RIGHT"),
    "touch-up releases logical buttons")
virtual_input.press("lost-focus", "DOWN")
virtual_input.clear()
assert(virtual_input.activeTouchCount() == 0 and not virtual_input.isDown("DOWN"),
    "clear prevents stuck input")

local fakeOptions = {
    {
        id = "options",
        config = { optionsCommands = { { id = "controls", name = "CONTROLS" } } },
        windows = { {
            content = { { listId = "config:optionsCommands", formatRight = "{''}" } },
        } },
    },
}
local decorated = touch_gamepad.decorateOptions(fakeOptions)
assert(decorated == fakeOptions[1], "touch option decorator finds options scene")
eq(#decorated.config.optionsCommands, 2, "touch option row appended")
eq(decorated.config.optionsCommands[2].id, "touch_gamepad", "touch option semantic id")
assert(decorated.windows[1].content[1].formatRight:find("touch_gamepad", 1, true),
    "touch option displays ON/OFF state")

-- Sky anchoring across surface heights. The panorama art is authored against
-- the 240-line composition and has no vertical headroom, so a taller surface
-- must not rescale the sky or repeat it on Y: the horizon stays put in
-- canonical space and the revealed band above is extended from the top row.
do
    local viewport_3d = require("presentation.viewport_3d")
    local PANORAMA_H = 60

    surface.setProfile("classic")
    local classic = viewport_3d.skyAnchor(PANORAMA_H, surface.compositionHeight(),
        select(2, surface.compositionOrigin()))
    eq(classic.backdropH, 120, "classic sky occupies the top half of the composition")
    eq(classic.extraTop, 0, "classic reveals no band above the composition")
    eq(classic.horizonY, 120, "classic horizon")

    surface.setProfile("four_three")
    local fourThree = viewport_3d.skyAnchor(PANORAMA_H, surface.compositionHeight(),
        select(2, surface.compositionOrigin()))
    eq(fourThree.scale, classic.scale, "4:3 must not rescale the sky")
    eq(fourThree.extraTop, 0, "4:3 grows sideways only")
    eq(fourThree.horizonY, classic.horizonY, "4:3 horizon is unmoved")

    surface.setProfile("wide")
    local wide = viewport_3d.skyAnchor(PANORAMA_H, surface.compositionHeight(),
        select(2, surface.compositionOrigin()))
    eq(wide.scale, classic.scale, "wide must not rescale the sky")
    eq(wide.extraTop, 0, "wide grows sideways only")
    eq(wide.horizonY, classic.horizonY, "wide horizon is unmoved")

    surface.setProfile("mobile_portrait")
    local portrait = viewport_3d.skyAnchor(PANORAMA_H, surface.compositionHeight(),
        select(2, surface.compositionOrigin()))
    eq(portrait.scale, classic.scale, "portrait must not rescale the sky either")
    eq(portrait.horizonY, classic.horizonY + 24, "portrait horizon shifts with the composition")
    eq(portrait.extraTop, 24 / classic.scale, "portrait extends upward by the revealed band")
    -- The load-bearing invariant: whatever the surface, the horizon sits at the
    -- same place in CANONICAL space. Only its render-space y moves.
    eq(portrait.horizonY - select(2, surface.compositionOrigin()), classic.backdropH,
        "horizon is anchored in canonical composition space")
end

surface.setProfile(original)
print("presentation surface tests passed")
