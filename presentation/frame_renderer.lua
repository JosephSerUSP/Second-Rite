-- Native game-frame compositor shared by live play and screenshot tools.
local frame_renderer = {}
local battle_view = require("presentation.battle_view")
local surface = require("presentation.surface")
-- Loading the scene compositor installs scene_host's injected presentation
-- adapter. scene_host itself never requires presentation (#150).
require("presentation.scene_compositor")

-- The party HUD this file used to draw itself for battle, and briefly for
-- dialogue to cover the transition, is now the persistent dock: both scenes
-- declare `config.dock` in scenes.json and the scene compositor draws it. What
-- is left here is battle's own chrome, which the dock does not own.
function frame_renderer.draw(scene_host, renderer, session, loader, gameHeight)
    local current = scene_host.getCurrent()
    local drawSession = session
    if current == "battle" then
        drawSession = battle_view.sessionFor(session)
    elseif battle_view.isActive() then
        -- A projection never escapes its battle scene. Once another scene owns
        -- the frame, render authoritative session state directly again.
        battle_view.clear()
    end

    local ctx = {
        session = drawSession,
        loader = loader,
        party = drawSession and drawSession.party or {},
    }
    local stringPictures = require("presentation.string_picture_renderer")
    local imagePictures = require("presentation.image_picture_renderer")

    -- scene_host delegates this presentation seam to scene_compositor, which
    -- owns the world/sky/backdrop-vs-composition split. Battle overlays remain
    -- authored in canonical composition space.
    scene_host.draw(ctx)

    if current == "battle" then
        local bv = require("engine.scenes.battle").getState()
        -- Reticles track battler positions, which battler_geometry authors in
        -- canonical composition coordinates, so they belong inside the frame.
        surface.beginComposition()
        renderer.drawTargetReticles(
            bv, bv.combatState or "input", bv.selectedIndex or 1,
            bv.skillSelect or false, bv.itemSelect or false,
            bv.livingMembers or {}, bv.activeMemberIdx or 1
        )
        surface.endComposition()

        -- The flash and defeat fade are full-surface effects, not framed ones
        -- (#199): battle's backdrop is the 3D world across the whole render
        -- surface, so confining them to the composition would flash or dim a
        -- 256-wide rectangle over an undimmed 426-wide world. Drawn outside the
        -- composition block so their own renderSize() sizing is not also
        -- translated by the origin. Z-order is unchanged.
        renderer.drawScreenFlashOverlay(bv.battle)
        renderer.drawDefeatFadeOverlay(bv.defeatFinalFade)
    end

    -- Effekseer is a native GL draw and does not consume LOVE's transform or
    -- translated scissors. Its own projection is surface-aware instead; keep
    -- this call between reticles and popups to preserve the established z-order.
    require("presentation.effekseer").draw()

    surface.beginComposition()
    renderer.drawDamagePopups()
    imagePictures.draw("screen")
    stringPictures.draw("screen")
    imagePictures.draw("top")
    stringPictures.draw("top")
    surface.endComposition()

    -- Diagnostics describe the actual logical output and therefore belong to
    -- render-surface space, not the authored 256x240 composition.
    require("presentation.dev_overlay").draw()
end

return frame_renderer
