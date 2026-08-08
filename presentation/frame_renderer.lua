-- Native game-frame compositor shared by live play and screenshot tools.
local frame_renderer = {}
local battle_view = require("presentation.battle_view")
local surface = require("presentation.surface")

-- The party HUD this file used to draw itself for battle, and briefly for
-- dialogue to cover the transition, is now the persistent dock: both scenes
-- declare `config.dock` in scenes.json and scene_host draws it. What is left
-- here is battle's own chrome, which the dock does not own.
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

    -- scene_host owns the world/backdrop-vs-composition split for scene
    -- content. Everything below is authored battle/screen chrome, so it lives
    -- in the canonical composition regardless of the render-surface profile.
    scene_host.draw(ctx)
    surface.beginComposition()

    if current == "battle" then
        local bv = require("engine.scenes.battle").getState()
        renderer.drawTargetReticles(
            bv, bv.combatState or "input", bv.selectedIndex or 1,
            bv.skillSelect or false, bv.itemSelect or false,
            bv.livingMembers or {}, bv.activeMemberIdx or 1
        )
        renderer.drawScreenFlashOverlay(bv.battle)
        renderer.drawDefeatFadeOverlay(bv.defeatFinalFade)
    end

    -- Effekseer draws ALL live screen-space effects in one call, not per
    -- battler. The native binding uses the canonical 256x240 projection, so
    -- the active composition translation is the semantic scope even though
    -- the native draw itself does not consume LOVE geometry transforms.
    require("presentation.effekseer").draw()

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
