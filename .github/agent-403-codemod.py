from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8")


def replace_exact(path, old, new, expected=1):
    text = read(path)
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s) of {old!r}, found {count}")
    write(path, text.replace(old, new))


# renderer owns the process dt feed, but the clock itself is generic.
replace_exact(
    "presentation/renderer.lua",
    'local small_battlers = require("presentation.small_battlers")\nlocal battle_layout',
    'local small_battlers = require("presentation.small_battlers")\nlocal sprite_sheet = require("presentation.sprite_sheet")\nlocal battle_layout')
replace_exact(
    "presentation/renderer.lua",
    "-- B.5 small battler cache/animation clock live in presentation/small_battlers.lua\n-- (shared with the generic window renderer's sprite list rows)",
    "-- Shared sprite cache/idle clock live in presentation/sprite_sheet.lua;\n-- battler-only effects remain in presentation/small_battlers.lua")
replace_exact(
    "presentation/renderer.lua",
    "-- B.5: Advance small battler animation timer (shared, drives all party sprite animations)\n    small_battlers.update(dt)",
    "-- Advance the generic shared sprite-sheet clock once per presentation frame.\n    sprite_sheet.update(dt)")

# window_renderer keeps battler rows on small_battlers, while generic
# cursor/wait sprites use the neutral service directly.
replace_exact(
    "presentation/window_renderer.lua",
    'local small_battlers = require("presentation.small_battlers")\nlocal actor_status',
    'local small_battlers = require("presentation.small_battlers")\nlocal sprite_sheet = require("presentation.sprite_sheet")\nlocal actor_status')
text = read("presentation/window_renderer.lua")
cursor_count = text.count('small_battlers.draw("Cursor"')
if cursor_count < 4:
    raise SystemExit(f"window_renderer: expected at least 4 generic Cursor draws, found {cursor_count}")
text = text.replace('small_battlers.draw("Cursor"', 'sprite_sheet.draw("Cursor"')
waiting_count = text.count('small_battlers.draw("UI_WaitingForInput')
if waiting_count != 1:
    raise SystemExit(f"window_renderer: expected 1 waiting-indicator draw, found {waiting_count}")
text = text.replace('small_battlers.draw("UI_WaitingForInput', 'sprite_sheet.draw("UI_WaitingForInput')
if 'small_battlers.draw(key' not in text:
    raise SystemExit("window_renderer: battler-row draw seam disappeared")
write("presentation/window_renderer.lua", text)

# main.lua's blue server marker is generic UI, not a battler.
replace_exact(
    "main.lua",
    'local small_battlers = require("presentation.small_battlers")',
    'local sprite_sheet = require("presentation.sprite_sheet")')
text = read("main.lua")
if text.count("small_battlers.") != 2:
    raise SystemExit(
        "main.lua: expected exactly two generic small_battlers calls, found "
        + str(text.count("small_battlers.")))
text = text.replace("small_battlers.", "sprite_sheet.")
anchor = '            "test_event_self_state",\n'
if anchor not in text:
    raise SystemExit("main.lua: unittest list anchor moved")
text = text.replace(anchor, anchor + '            "test_sprite_sheet",\n', 1)
write("main.lua", text)

# Validation asks only whether a key resolves; it must not import a battler
# presentation layer to answer a filesystem question.
replace_exact(
    "engine/validator_rules.lua",
    "-- Sprite keys resolve through small_battlers.resolveFile so validation",
    "-- Sprite keys resolve through sprite_sheet.resolveFile so validation")
replace_exact(
    "engine/validator_rules.lua",
    'local sb = require("presentation.small_battlers")',
    'local sprite_sheet = require("presentation.sprite_sheet")')
replace_exact(
    "engine/validator_rules.lua",
    "sb.resolveFile(ev.sprite)",
    "sprite_sheet.resolveFile(ev.sprite)")

# Animation preview consumes the same resolver, cached image, slicing, quad
# cache and frame-rate math as runtime rather than reimplementing the sheet.
text = read("engine/cli_tools.lua")
text = text.replace("small_battlers.resolveFile", "sprite_sheet.resolveFile")
text = text.replace(
    'local small_battlers = require("presentation.small_battlers")\n        local resolved = sprite_sheet.resolveFile(spritePath)',
    'local sprite_sheet = require("presentation.sprite_sheet")\n        local resolved = sprite_sheet.resolveFile(spritePath)',
    1)
old_block = '''        local texture = resolved and love.graphics.newImage(resolved.path) or nil
        if texture then texture:setFilter("nearest", "nearest") end

        -- Frame slicing: square cells laid out in a row (matches the
        -- small_battlers convention). Idle animation advances by the sheet's
        -- fps (or speed*4, default 4) and loops across the preview.
        --
        -- With no sprite, the anchor still needs a footprint or the animation
        -- would preview against a different origin than battle gives it. The
        -- small_battlers default cell keeps the anchor honest while nothing is
        -- drawn in it.
        local DEFAULT_CELL = 24
        local cellW, cellH, numFrames, spriteQuad
        if texture then
            local texW, texH = texture:getDimensions()
            cellH = texH
            cellW = math.min(texW, cellH)
            numFrames = math.max(1, math.floor(texW / cellW))
            spriteQuad = love.graphics.newQuad(0, 0, cellW, cellH, texW, texH)
        else
            cellW, cellH, numFrames = DEFAULT_CELL, DEFAULT_CELL, 1
        end
        local spriteRate = spriteOverrides.fps or (spriteOverrides.speed and 4 * spriteOverrides.speed) or 4
'''
new_block = '''        local sprite = resolved and sprite_sheet.get(spritePath) or nil
        local texture = sprite and sprite.img or nil

        -- Runtime and preview share the same cached sheet shape and frame-rate
        -- math. With no sprite the anchor still gets the historical 24px
        -- footprint so animation-only previews keep the same origin.
        local DEFAULT_CELL = 24
        local cellW = sprite and sprite.cellW or DEFAULT_CELL
        local cellH = sprite and sprite.cellH or DEFAULT_CELL
        local spriteQuad = nil
'''
if text.count(old_block) != 1:
    raise SystemExit("cli_tools: preview frame-slicing block moved")
text = text.replace(old_block, new_block, 1)
old_frame = '''            local frame = math.floor(elapsed * spriteRate) % numFrames
            if spriteQuad then
                spriteQuad:setViewport(frame * cellW, 0, cellW, cellH)
            end
'''
new_frame = '''            local frame = sprite and sprite_sheet.frameAt(sprite, elapsed) or 0
            spriteQuad = sprite and sprite_sheet.quad(sprite, frame) or nil
'''
if text.count(old_frame) != 1:
    raise SystemExit("cli_tools: preview frame-selection block moved")
text = text.replace(old_frame, new_frame, 1)
reset_old = 'require("presentation.small_battlers").reset()'
if text.count(reset_old) != 1:
    raise SystemExit(
        "cli_tools: expected one screenshot clock reset, found "
        + str(text.count(reset_old)))
text = text.replace(reset_old, 'require("presentation.sprite_sheet").reset()', 1)
if "small_battlers.resolveFile" in text or 'require("presentation.small_battlers").reset' in text:
    raise SystemExit("cli_tools: generic small_battler dependency remains")
write("engine/cli_tools.lua", text)

# Architectural guardrails: battler-specific module must no longer advertise
# generic cache/resolver/clock methods.
sb = read("presentation/small_battlers.lua")
for forbidden in (
    "function small_battlers.get",
    "function small_battlers.resolveFile",
    "function small_battlers.update",
    "function small_battlers.reset",
):
    if forbidden in sb:
        raise SystemExit(f"small_battlers still owns generic API: {forbidden}")

print("#403 call-site codemod completed with all expected anchors intact")
