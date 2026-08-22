-- Projection policy for Map Event visuals.
--
-- Gameplay owns movement and Event actor semantics. The reusable animation
-- controller owns only semantic visual-state selection. viewport_3d owns
-- concrete assets/geometry. This module is the narrow seam between them.
local event_actor = require("engine.event_actor")
local event_animation_controller = require("presentation.event_animation_controller")

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

local function defaultMode(ev, resolvedPresentation)
    if type(ev) == "table" and ev.wallEvent then return "door" end
    if resolvedPresentation and resolvedPresentation.interactionFocus then return "object" end
    return "npc"
end

local function controllerField(ev, session)
    if type(ev) ~= "table" then return nil end
    local raw = ev.animationController
    if raw == nil and ev.scriptId and session and session.loader
            and session.loader.commonEvents then
        local ce = session.loader.commonEvents[tostring(ev.scriptId)]
        if ce then raw = ce.animationController end
    end
    if raw == false or raw == "" then return false end
    if raw == nil then return nil end
    if type(raw) ~= "string" then
        error("event_presentation_policy: animationController must be a string or false", 3)
    end
    return raw
end

-- Resolve renderer-facing facts from actor state. A controller-selected
-- semantic animation may replace the actor's default idle/walk clip without
-- becoming movement authority itself.
function event_presentation_policy.resolve(
        session, authoredEvent, effectiveEvent, resolvedPresentation, override)
    local ev = effectiveEvent or authoredEvent
    if type(ev) ~= "table" then
        return {
            mode = "object", render_dir = "down", moving = false,
            clip = nil, rootX = nil, rootY = nil,
        }
    end

    override = type(override) == "table" and override or {}
    local actor = event_actor.snapshot(session, ev)
    local mode = override.mode or defaultMode(ev, resolvedPresentation)

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

-- Decorate viewport_3d's canonical Event presentation resolver. The existing
-- resolver remains sole authority for Page/Common-Event visual inheritance;
-- this wrapper extends the same precedence to animationController and then
-- selects a semantic controller state for whichever backend won (sprite/model).
function event_presentation_policy.install(viewport)
    if type(viewport) ~= "table" or type(viewport.resolveEventPresentation) ~= "function" then
        error("event_presentation_policy.install: viewport Event presentation resolver required", 2)
    end
    if viewport._eventPresentationPolicyInstalled then return viewport end

    local baseResolve = viewport.resolveEventPresentation
    viewport.resolveEventPresentation = function(ev, session)
        local presentation = baseResolve(ev, session)
        local effective = presentation.page or ev
        local controllerId = controllerField(effective, session)
        presentation.animationController = controllerId
        presentation.renderState = event_presentation_policy.resolve(
            session, ev, effective, presentation)

        if controllerId then
            local selected = event_animation_controller.resolve(session, effective, controllerId)
            presentation.controllerState = selected
            presentation.renderState.controllerState = selected.state
            presentation.renderState.clip = selected.animation
            presentation.renderState.loop = selected.loop
        end
        return presentation
    end
    viewport._eventPresentationPolicyInstalled = true
    return viewport
end

return event_presentation_policy