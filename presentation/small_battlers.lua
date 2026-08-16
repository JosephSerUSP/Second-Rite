-- Battler-specific sprite presentation.
--
-- Generic sprite resolution, image loading/cache, frame slicing, quad caching,
-- and idle-animation timing live in presentation/sprite_sheet.lua. This module
-- owns only behavior that is genuinely about a battler: dead-state tint plus
-- animation-player-driven transforms, particles, gradients, flash/shake and
-- reap/swap-out treatment.

local small_battlers = {}

-- Dead-tint applied when a battler's game-state is dead (not an animation —
-- this is the static visual that replaces the sprite for dead party members
-- in the grid). The death animation (system.death) handles enemy portraits.
local DEAD_TINT = { 0.28, 0.26, 0.32, 1 }

local sprite_sheet = require("presentation.sprite_sheet")
local animation_player = require("presentation.animation_player")
local gradient_shader = require("presentation.gradient_shader")

-- Per-battler-object damage feedback is owned by animation_player; this seam
-- gives callers one battler-facing action without exposing the player itself.
function small_battlers.triggerDamage(battlerRef)
    if not battlerRef then return end
    animation_player.play("system.small_damage", battlerRef)
end

-- The single shared "draw a battler's animated sprite" call: idle animation,
-- dead tint, and (when battlerRef has live presentation state) transform,
-- particles, gradient and flash/shake overlays. Generic UI sprites should call
-- presentation.sprite_sheet.draw instead of depending on this battler layer.
--
-- Permadeath / emergency wave: a dead party member normally renders as a flat
-- DEAD_TINT silhouette. system.reap/system.swap_out still need the full live
-- animation treatment while fading out, matching the enemy-side death special
-- case. system.swap_in plays on an alive incoming battler and needs no branch.
function small_battlers.draw(spriteKey, x, y, size, dead, battlerRef, session)
    local sheet = sprite_sheet.get(spriteKey)
    if not (sheet and sheet.img) then return false end

    local rect = { x = x, y = y, w = size, h = size }

    local isFadingOut = dead and battlerRef and
        (animation_player.isPlaying(battlerRef, "system.reap")
            or animation_player.isPlaying(battlerRef, "system.swap_out"))
    -- A state can pin the sprite still (data/states.json display.sprite.static).
    local frozen = battlerRef and battlerRef.spriteStatic
    local animated = ((not dead) or isFadingOut) and not frozen
    local frame = animated and sprite_sheet.frame(sheet) or 0

    local drawX = x
    local drawY = y
    local scaleX = 1
    local scaleY = 1
    if animated and battlerRef then
        local shakeOff = animation_player.getShakeOffset(battlerRef)
        local xf = animation_player.getTransform(battlerRef)
        drawX = x + shakeOff + xf.offsetX
        drawY = y + xf.offsetY
        scaleX = xf.scaleX
        scaleY = xf.scaleY
    end

    local quad = sprite_sheet.quad(sheet, frame)
    local drawScale = size / sheet.cellW

    local function drawSprite()
        love.graphics.draw(sheet.img, quad, drawX, drawY, 0,
            drawScale * scaleX, drawScale * scaleY)
    end

    if animated and battlerRef then
        love.graphics.setColor(1, 1, 1, 1)
        animation_player.drawParticles(battlerRef, rect, drawSprite, "back", session)
        -- The drawer owns the final rect, so it is also the correct place to
        -- resolve size-relative Effekseer anchors.
        require("presentation.effekseer").spawnFor(battlerRef, rect)
    end

    if dead and not isFadingOut then
        love.graphics.setColor(DEAD_TINT[1], DEAD_TINT[2], DEAD_TINT[3], DEAD_TINT[4] or 1)
        drawSprite()
    else
        love.graphics.setColor(1, 1, 1, 1)
        gradient_shader.drawWithGradient(battlerRef, drawSprite, animation_player)
    end

    if animated and battlerRef then
        local tint = animation_player.getTint(battlerRef)
        local blend = animation_player.getBlendMode(battlerRef)
        if tint and blend then
            love.graphics.setBlendMode(blend)
            love.graphics.setColor(tint.color[1], tint.color[2], tint.color[3], tint.alpha)
            drawSprite()
            love.graphics.setBlendMode("alpha")
        end
    end

    if animated and battlerRef then
        love.graphics.setColor(1, 1, 1, 1)
        animation_player.drawParticles(battlerRef, rect, drawSprite, "front", session)
    end

    love.graphics.setColor(1, 1, 1, 1)
    return true
end

return small_battlers
