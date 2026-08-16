from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


main_path = Path("main.lua")
text = main_path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''-- Auto-repeat state (update-driven, not OS key repeat)\nlocal heldKeys = {}  -- key → { holdTime = seconds, lastFire = count }\n\n''',
    '''-- Auto-repeat/held state is owned by engine.player_controller after raw\n-- device input has resolved to the canonical logical-button vocabulary.\n\n''',
    "remove physical heldKeys owner",
)

old_transition = '''        -- When the transition animation finishes, immediately re-fire the held\n        -- directional key so movement continues without waiting for the next\n        -- auto-repeat tick (closing the gap between timer expiry and repeat).\n        if prevTransition and prevTransition > 0\n            and (not activeSession.transitionTimer or activeSession.transitionTimer <= 0)\n            and scene_host.getCurrent() == "map" then\n            local REPEAT_DIR_KEYS = { "up", "down", "left", "right",\n                                      "w", "a", "s", "d", "q", "e" }\n            for _, key in ipairs(REPEAT_DIR_KEYS) do\n                if love.keyboard.isDown(key) then\n                    local ctx = { session = activeSession, loader = loader, party = activeSession.party or {} }\n                    if not scene_host.keypressed(key, ctx) then\n                        handleKeyPressed(key)\n                    end\n                    break\n                end\n            end\n        end\n'''
new_transition = '''        -- Preserve the historical transition-finish refire, but ask the\n        -- logical controller which player button is held rather than polling\n        -- device keys. Physical and automated players therefore share it.\n        if prevTransition and prevTransition > 0\n            and (not activeSession.transitionTimer or activeSession.transitionTimer <= 0)\n            and scene_host.getCurrent() == "map" then\n            local ctx = { session = activeSession, loader = loader, party = activeSession.party or {} }\n            require("engine.player_controller").refireFirstHeld(ctx)\n        end\n'''
text = replace_once(text, old_transition, new_transition, "transition refire")

old_repeat = '''    -- ── Auto-repeat for held directional keys ────────────────────────────\n    -- Driven by love.keyboard.isDown() + timers instead of OS key repeat,\n    -- giving controlled initial delay and interval for menu scrolling and\n    -- map movement. Routes through the input mapper (scene_host.keypressed)\n    -- so rebindable controls work automatically.\n    local REPEAT_DIR_KEYS = { "up", "down", "left", "right",\n                              "w", "a", "s", "d", "q", "e" }\n    local REPEAT_INITIAL  = conf("ui", "autoRepeatInitial", 0.3)\n    local REPEAT_INTERVAL = conf("ui", "autoRepeatInterval", 0.06)\n\n    for _, key in ipairs(REPEAT_DIR_KEYS) do\n        if love.keyboard.isDown(key) then\n            local state = heldKeys[key]\n            if not state then\n                heldKeys[key] = { holdTime = 0, lastFire = 0 }\n                state = heldKeys[key]\n            end\n            state.holdTime = state.holdTime + dt\n            if state.holdTime >= REPEAT_INITIAL then\n                local elapsed = state.holdTime - REPEAT_INITIAL\n                local fireCount = math.floor(elapsed / REPEAT_INTERVAL)\n                if fireCount > state.lastFire then\n                    state.lastFire = fireCount\n                    local ctx = { session = activeSession, loader = loader, party = activeSession.party or {} }\n                    if not scene_host.keypressed(key, ctx) then\n                        handleKeyPressed(key)\n                    end\n                end\n            end\n        else\n            heldKeys[key] = nil\n        end\n    end\n'''
new_repeat = '''    -- Logical held-input repeat. The timing policy is still Project-owned,\n    -- but the controller sees canonical buttons only; no keyboard polling or\n    -- device-specific synthetic input exists on the automation path.\n    require("engine.player_controller").update(dt, ctx, {\n        initial = conf("ui", "autoRepeatInitial", 0.3),\n        interval = conf("ui", "autoRepeatInterval", 0.06),\n    })\n'''
text = replace_once(text, old_repeat, new_repeat, "logical auto-repeat")

start = text.index("handleKeyPressed = function(key)\n")
end = text.index("\nfunction love.keypressed(key, scancode, isrepeat)", start)
block = text[start:end]
block = replace_once(block, "handleKeyPressed = function(key)\n", "handleKeyPressed = function(button)\n", "logical fallback signature")
block = block.replace("if inputCooldown > 0 then return end", "if inputCooldown > 0 then return true end")
block = block.replace("if not activeSession then return end", "if not activeSession then return true end")
block = block.replace("if door_transition.isActive() then return end", "if door_transition.isActive() then return true end")

skip_block = '''    if eventSkipLabel and activeWalker\n        and (key == "escape" or key == "backspace") then\n        local target = activeWalker.graph\n            and activeWalker.graph.labels\n            and activeWalker.graph.labels[eventSkipLabel]\n        if not target then\n            error("event skip references unknown label '" .. tostring(eventSkipLabel) .. "'", 0)\n        end\n        eventWaitRemaining = 0\n        activeWalker:goToNode(target)\n        handleDialogueAction()\n        return\n    end\n\n'''
block = replace_once(block, skip_block, "", "move event-skip ahead of authored hooks")

scene_dispatch = '''    local ctx = { session = activeSession, loader = loader, party = activeSession.party or {} }\n    if scene_host.keypressed(key, ctx) then\n        return\n    end\n\n'''
block = replace_once(block, scene_dispatch, "", "remove second physical Scene dispatch")

# Translate the existing host fallback vocabulary in-place. These replacements
# are scoped to handleKeyPressed only, so comments/dev shortcuts elsewhere stay
# physical where they belong.
translations = {
    '(key == "q" or key == "e")': '(button == "L" or button == "R")',
    'key == "up" or key == "w"': 'button == "UP"',
    'key == "down" or key == "s"': 'button == "DOWN"',
    'key == "left" or key == "a"': 'button == "LEFT"',
    'key == "right" or key == "d"': 'button == "RIGHT"',
    'key == "q"': 'button == "L"',
    'key == "e"': 'button == "R"',
    'key == "space" or key == "return"': 'button == "A" or button == "START"',
    '(key == "escape" or key == "backspace")': '(button == "B")',
    'activeSession.bumpCooldowns[key]': 'activeSession.bumpCooldowns[button]',
    'activeSession.bumpNudgeKey = key': 'activeSession.bumpNudgeKey = button',
}
for old, new in translations.items():
    block = block.replace(old, new)

map_open = '''    if scene_host.getCurrent() == "map" then\n        if require("presentation.world_focus").isActive() then return end\n'''
map_new = '''    if scene_host.getCurrent() == "map" then\n        if button ~= "UP" and button ~= "DOWN" and button ~= "LEFT" and button ~= "RIGHT"\n            and button ~= "L" and button ~= "R" and button ~= "A" and button ~= "START" then\n            return false\n        end\n        if require("presentation.world_focus").isActive() then return true end\n'''
block = replace_once(block, map_open, map_new, "map logical vocabulary guard")

map_to_dialogue = '''        end\n        \n    elseif scene_host.getCurrent() == "dialogue" then\n        local node = activeWalker:getCurrentNode()\n'''
map_to_dialogue_new = '''        end\n        return true\n        \n    elseif scene_host.getCurrent() == "dialogue" then\n        if button ~= "UP" and button ~= "DOWN" and button ~= "A"\n            and button ~= "START" and button ~= "B" then\n            return false\n        end\n        local node = activeWalker and activeWalker:getCurrentNode()\n'''
block = replace_once(block, map_to_dialogue, map_to_dialogue_new, "map/dialogue handled boundary")

suffix = '''        end\n        \n    end\nend\n'''
suffix_new = '''        end\n        return true\n        \n    end\n    return false\nend\n'''
if not block.endswith(suffix):
    raise SystemExit("logical fallback suffix: expected exact function suffix")
block = block[:-len(suffix)] + suffix_new

text = text[:start] + block + text[end:]

bind = '''\n-- Main-host gameplay that still owns transient dialogue walkers and Map\n-- interaction closures plugs into the logical Scene-host membrane here. The\n-- adapter receives canonical buttons only; automation cannot name a map step,\n-- dialogue option, Event, coordinate, or Scene hook.\nscene_host.bindPlayerInput({\n    before = function(button)\n        if inputCooldown > 0 or not activeSession or door_transition.isActive() then\n            return true\n        end\n        -- Event skip historically outranked the current Scene's cancel hook.\n        -- Preserve that modal priority, now on logical B rather than Escape.\n        if eventSkipLabel and activeWalker and button == "B" then\n            local target = activeWalker.graph\n                and activeWalker.graph.labels\n                and activeWalker.graph.labels[eventSkipLabel]\n            if not target then\n                error("event skip references unknown label '" .. tostring(eventSkipLabel) .. "'", 0)\n            end\n            eventWaitRemaining = 0\n            activeWalker:goToNode(target)\n            handleDialogueAction()\n            return true\n        end\n        return nil\n    end,\n    fallback = function(button)\n        return handleKeyPressed(button)\n    end,\n})\n'''
needle = "\nfunction love.keypressed(key, scancode, isrepeat)"
text = replace_once(text, needle, bind + needle, "bind main-host logical fallback")

old_tail = '''    handleKeyPressed(key)\nend\n\n-- heldKeys is declared at module level (near inputCooldown); this handler\n-- clears the tracked state so the update loop stops repeating on release.\nfunction love.keyreleased(key)\n    heldKeys[key] = nil\nend\n'''
new_tail = '''    local ctx = { session = activeSession, loader = loader, party = activeSession and activeSession.party or {} }\n    scene_host.keypressed(key, ctx)\nend\n\nfunction love.keyreleased(key)\n    scene_host.keyreleased(key)\nend\n'''
text = replace_once(text, old_tail, new_tail, "physical key edge adapter")

if "heldKeys" in text:
    raise SystemExit("physical heldKeys ownership remains in main.lua")
if "handleKeyPressed(key)" in text:
    raise SystemExit("raw-key fallback call remains in main.lua")

main_path.write_text(text, encoding="utf-8", newline="\n")

camera_path = Path("presentation/world_camera.lua")
camera = camera_path.read_text(encoding="utf-8")
camera = replace_once(camera, 'if key == "down" or key == "s" then',
                      'if key == "DOWN" or key == "down" or key == "s" then',
                      "logical backward bump nudge")
camera = replace_once(camera, 'elseif key == "q" then',
                      'elseif key == "L" or key == "q" then',
                      "logical left-strafe bump nudge")
camera = replace_once(camera, 'elseif key == "e" then',
                      'elseif key == "R" or key == "e" then',
                      "logical right-strafe bump nudge")
camera_path.write_text(camera, encoding="utf-8", newline="\n")

print("#381 main/player-input host patch applied")
