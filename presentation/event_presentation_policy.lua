-- Projection policy for Map Event visuals.
--
-- Gameplay owns movement and Event actor semantics. viewport_3d owns concrete
-- assets/geometry. This module is the narrow seam between them: it turns an
-- Event actor snapshot into renderer-facing facts without making movement type
-- itself a rendering contract.
local event_actor = require("engine.event_actor")

local event_presentation_policy = {}

local RENDER_DIR = {
    N = "up",
    E = "right",
    S = "down",
    W = "left",
}

local function normalizedRenderDir(value)
    local facing = event_actor.normalizeFacing(value)
    return facing and RENDER_DIR[facing] or nil
end

local function authoredRenderDir(ev)
    if type(ev) ~= "table" then return "down" end
    return normalizedRenderDir(ev.facing or ev.direction or ev.dir) or "down"
end

-- This classification deliberately does not inspect movement type. A stationary
-- NPC is still an NPC; an object does not become character-like merely because
-- some gameplay system happens to move its root.
local function defaultMode(ev, resolvedPresentation)
    if type(ev) == "table" and ev.wallEvent then return "door" end
    if resolvedPresentation and resolvedPresentation.interactionFocus then
        return "object"
    end
    return "npc"
end

-- Resolve one renderer-facing state record.
--
-- `effectiveEvent` should be the already page/override-resolved Event when the
-- caller has one. `resolvedPresentation` is the asset/focus record produced by
-- the renderer's ordinary Event presentation resolver. `override` is an
-- optional presentation-only policy for future archetypes/special cases; it
-- never mutates gameplay or Event actor state.
--
-- Supported override fields:
--   mode, tracksFacing, tracksLocomotion, render_dir, moving, clip
function event_presentation_policy.resolve(
        session, authoredEvent, effectiveEvent, resolvedPresentation, override)
    local ev = effectiveEvent or authoredEvent
    if type(ev) ~= "table" then
        return {
            mode = "object",
            render_dir = "down",
            moving = false,
            clip = nil,
            rootX = nil,
            rootY = nil,
        }
    end

    override = type(override) == "table" and override or {}
    local actor = event_actor.snapshot(session, ev)
    local mode = override.mode or defaultMode(ev, resolvedPresentation)

    -- Character presentation follows the actor by default. Static/object
    -- presentation follows authored facing and ignores locomotion, so movement
    -- storage cannot accidentally turn a chest/door into a walking sprite.
    local tracksFacing = override.tracksFacing
    if tracksFacing == nil then tracksFacing = mode == "npc" end
    local tracksLocomotion = override.tracksLocomotion
    if tracksLocomotion == nil then tracksLocomotion = mode == "npc" end

    local renderDir = override.render_dir
    if renderDir ~= nil then
        renderDir = normalizedRenderDir(renderDir)
        if not renderDir then
            error("event_presentation_policy.resolve: invalid render_dir '"
                .. tostring(override.render_dir) .. "'", 2)
        end
    elseif tracksFacing then
        renderDir = RENDER_DIR[actor.facing] or authoredRenderDir(ev)
    else
        renderDir = authoredRenderDir(ev)
    end

    local moving = override.moving
    if moving == nil then
        moving = tracksLocomotion and actor.locomotion == "moving" or false
    else
        moving = moving == true
    end

    local clip = override.clip
    if clip == nil and tracksLocomotion then clip = actor.clip end

    return {
        mode = tostring(mode),
        render_dir = renderDir,
        moving = moving,
        clip = clip,
        rootX = actor.rootX,
        rootY = actor.rootY,
    }
end

-- viewport_3d already has one canonical Event asset/page resolver. Wrap that
-- seam instead of teaching every sprite/model branch how to read actor state.
-- This follows the same install-an-adapter pattern used by prepared_map_cache.
function event_presentation_policy.install(viewport)
    if type(viewport) ~= "table" or type(viewport.resolveEventPresentation) ~= "function" then
        error("event_presentation_policy.install: viewport Event presentation resolver required", 2)
    end
    if viewport._eventPresentationPolicyInstalled then return viewport end

    local baseResolve = viewport.resolveEventPresentation
    viewport.resolveEventPresentation = function(ev, session)
        local presentation = baseResolve(ev, session)
        presentation.renderState = event_presentation_policy.resolve(
            session, ev, presentation.page, presentation)
        return presentation
    end
    viewport._eventPresentationPolicyInstalled = true
    return viewport
end

return event_presentation_policy