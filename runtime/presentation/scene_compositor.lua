-- Presentation-side owner for declarative scene composition (#150).
--
-- engine.scene_host owns stack/state/hooks and publishes semantic transition
-- facts through bindPresentation. This module owns every graphics operation and
-- the concrete scene_transition state. Loading it installs that adapter; the
-- engine never requires this module in return.
local scene_host = require("engine.scene_host")
local scene_transition = require("presentation.scene_transition")
local surface = require("presentation.surface")

local scene_compositor = {}

-- Scene-owned screen-space Effekseer effects. Unlike battler animations, these
-- are not anchored to a target rectangle: a scene declares their canvas
-- position and owns them for its lifetime. This is intentionally a small
-- lifecycle cache so a loop-forever title effect is started once, survives
-- ordinary frames, and is stopped when the scene changes.
local screenEffectSceneId
local screenEffectHandles = {}

local function syncScreenEffects(state, sceneData)
    local sceneId = state and state.id
    if sceneId == screenEffectSceneId then return end

    local effekseer = require("presentation.effekseer")
    for _, handle in ipairs(screenEffectHandles) do
        effekseer.stop(handle)
    end
    screenEffectHandles = {}
    screenEffectSceneId = sceneId

    for _, spec in ipairs((sceneData and sceneData.screenEffects) or {}) do
        local handle = effekseer.play(spec.effect, spec.x, spec.y, spec.magnification)
        if handle then table.insert(screenEffectHandles, handle) end
    end
end

-- Menu-style windows scenes reached from exploring (dialogue, shop, status,
-- ...) can opt into showing the 3D map behind their windows instead of a
-- blank canvas ("backdrop": "map" in scenes.json) — a VN-style overlay
-- rather than a scene swap. Guarded on real map state existing: the
-- deterministic golden-ui harness session never calls exploration.loadMap,
-- so this silently no-ops there rather than erroring the smoke test.
local function resolveBackdropFade(sceneData, state)
    local fade = sceneData.backdropFade
    if not fade then return 0 end
    local value = fade
    if type(fade) == "string" then
        local ok, result = pcall(require("engine.formula").eval, fade,
            { v = (state and state.v) or {} })
        value = (ok and type(result) == "number") and result or 0
    end
    if type(value) ~= "number" then return 0 end
    return math.max(0, math.min(1, value))
end

local function drawBackdropFade(sceneData, state, renderSurface)
    local value = resolveBackdropFade(sceneData, state)
    if value <= 0 then return end
    local width, height
    if renderSurface then
        width, height = surface.renderSize()
    else
        width, height = surface.compositionSize()
    end
    love.graphics.setColor(0, 0, 0, value)
    love.graphics.rectangle("fill", 0, 0, width, height)
    love.graphics.setColor(1, 1, 1, 1)
end

-- Render-surface backdrop: only real 3D world is allowed to expand. Authored
-- illustrations remain composition-space below, even when they represent a
-- location reached from the map.
local function drawRenderBackdrop(sceneData, ctx, state)
    if sceneData.backdrop ~= "map" then return false end
    local session = ctx.session
    if not (session and session.currentMapData and session.mapGrid) then return false end
    if session.locationArt then return false end
    require("presentation.vertex_shading_resolver").draw(session)
    drawBackdropFade(sceneData, state, true)
    return true
end

local function drawCompositionBackdrop(sceneData, ctx, state)
    if sceneData.backdropImage then
        require("presentation.static_backdrop").draw(sceneData.backdropImage)
    end
    if sceneData.backdrop ~= "map" then return false end
    local session = ctx.session
    if not (session and session.currentMapData and session.mapGrid and session.locationArt) then
        return false
    end
    require("presentation.location_renderer").draw(session.locationArt)
    drawBackdropFade(sceneData, state, false)
    return true
end

function scene_compositor.transition(event)
    if not event then return end
    -- PRESERVED, NOT IDEALIZED (#150): scene_transition has one active slot.
    -- scene_host.goto_scene publishes exit then enter synchronously, so this
    -- second start replaces the first. Do not queue/coalesce these here; a
    -- future transition redesign can reap that opportunity as its own visible
    -- behavior change instead of hiding it inside dependency surgery.
    scene_transition.start(event.kind, event.effect, event.duration, event.color)
end

function scene_compositor.update(dt)
    scene_transition.update(dt)
end

-- Every scene declares how it draws (scenes.json `draw`):
--   "windows" -- rendered entirely from its windows array
--   "world"   -- a world view (named by `world`) with windows layered on top
-- The old "no flag = fall back to legacy Lua drawing" rule was purged
-- 24.07.2026 once the last legacy-drawn scene (town) was deleted and map
-- became an explicit world scene, so there is no host-side fallback left:
-- a scene with an unrecognized draw mode is a data bug and says so.
function scene_compositor.draw(state, sceneData, ctx)
    syncScreenEffects(state, sceneData)
    if not sceneData then
        scene_transition.draw()
        return false
    end

    local renderBackdropDrawn = false
    if sceneData.draw == "world" then
        local worldPresentation = require("presentation.world_presentation")
            .resolve(sceneData.worldPresentation)
        require("presentation.world_renderer").draw(sceneData.world, ctx, worldPresentation)
        renderBackdropDrawn = true
    elseif sceneData.draw ~= "windows" then
        error("scene '" .. tostring(state.id) .. "' has no draw mode "
            .. "(expected \"windows\" or \"world\", got '"
            .. tostring(sceneData.draw) .. "')", 0)
    else
        renderBackdropDrawn = drawRenderBackdrop(sceneData, ctx, state)
    end

    -- A subtractive event fade dims the backdrop but not dock/windows. When
    -- that backdrop is expanded world it must cover the full render surface;
    -- composition-only art gets the same established effect inside the frame.
    if renderBackdropDrawn then
        require("presentation.subtractive_transition").draw()
    end

    surface.beginComposition()
    drawCompositionBackdrop(sceneData, ctx, state)
    require("presentation.image_picture_renderer").draw("backdrop")
    require("presentation.string_picture_renderer").draw("backdrop")
    if not renderBackdropDrawn then
        require("presentation.subtractive_transition").draw()
    end
    local window_renderer = require("presentation.window_renderer")
    -- The persistent dock owns the bottom windowskin shells. Scene windows draw
    -- above them, so battle commands can occupy a dock shell without the empty
    -- shell panel covering their controls.
    require("presentation.dock").draw(state, sceneData, ctx)
    window_renderer.draw(state, sceneData, ctx)
    surface.endComposition()

    -- Scene enter/exit fades are genuinely full-surface transitions: they cover
    -- peripheral world and the canonical composition together.
    --
    -- IMPORTANT PRESERVED Z-ORDER (#150): scene_transition.draw() ALSO draws
    -- touch_gamepad after the fade. Keeping this call as the compositor's final
    -- scene layer means platform controls remain usable/visible above a fading
    -- frame. Splitting those responsibilities later may be worthwhile, but it
    -- must be a deliberate presentation change rather than an extraction side
    -- effect.
    scene_transition.draw()
    return true
end

-- Installing the adapter from presentation -> engine keeps dependency direction
-- literal. Headless users that require only engine.scene_host never load this
-- module and therefore keep an empty/no-op presentation seam.
scene_host.bindPresentation({
    transition = scene_compositor.transition,
    update = scene_compositor.update,
    draw = scene_compositor.draw,
})

return scene_compositor
