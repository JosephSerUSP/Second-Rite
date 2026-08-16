from pathlib import Path
import json


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'anchor not found in {path}: {old[:80]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')


replace_once(
    'engine/interpreter.lua',
    '-- Expected keys: rebindSession(session), isBattleLogRevealing(),\n-- finishBattleLogReveal(), isAnimationPlaying(), runCommonEvent(id).',
    '-- Expected keys: rebindSession(session), isBattleLogRevealing(),\n-- finishBattleLogReveal(), isAnimationPlaying(), signalEventAnimation(eventId, signal),\n-- runCommonEvent(id).'
)

replace_once(
    'engine/interpreter.lua',
    'handlers.SET_EVENT_LABEL = handlers.CHANGE_EVENT_PROPERTIES\nhandlers.SET_EVENT_NAME = handlers.CHANGE_EVENT_PROPERTIES\n\nhandlers.IF = function(cmd, ctx)',
    '''handlers.SET_EVENT_LABEL = handlers.CHANGE_EVENT_PROPERTIES
handlers.SET_EVENT_NAME = handlers.CHANGE_EVENT_PROPERTIES

-- One presentation sentence for deliberate Event choreography. `signal` is an
-- authored semantic name (wave/pray/open/...), never a native animation id.
-- Omitted eventId addresses the Map Event whose Program is currently running.
-- The engine forwards the request through its existing presentation seam and
-- remains unaware of controller state, sprite/model representation, or clips.
handlers.ANIMATION_SIGNAL = function(cmd, ctx)
    if type(cmd.signal) ~= "string" or cmd.signal == "" then
        error("ANIMATION_SIGNAL requires a non-empty semantic signal", 0)
    end
    local eventId = cmd.eventId
        or (ctx and ctx.eventId)
        or (ctx and ctx.event and ctx.event.id)
    if eventId == nil then return end
    present("signalEventAnimation", eventId, cmd.signal)
end

handlers.IF = function(cmd, ctx)'''
)

replace_once(
    'main.lua',
    '''    -- An item asked to run a common event (the Forbidden Lamp shape). The
    -- engine cannot do this itself: CALL_COMMON_EVENT compiles to a dialogue
''',
    '''    -- Presentation-only Event choreography (#591). Resolve the target
    -- through the same page/Event/Common-Event presentation seam the viewport
    -- uses, then enqueue one generic semantic signal on that Event's ephemeral
    -- controller instance. No controller means a deliberate no-op.
    signalEventAnimation = function(eventId, signal)
        local session = activeSession
        if not session or type(signal) ~= "string" or signal == "" then return false end
        local targetId = tonumber(eventId) or eventId
        local target = nil
        for _, candidate in ipairs((session.currentMapData and session.currentMapData.events) or {}) do
            if candidate.id == targetId or tostring(candidate.id) == tostring(targetId) then
                target = candidate
                break
            end
        end
        if not target then return false end

        local viewport = require("presentation.viewport_3d")
        require("presentation.event_presentation_policy").install(viewport)
        local resolved = viewport.resolveEventPresentation(target, session)
        local controllerId = resolved and resolved.animationController
        if not controllerId then return false end
        return require("presentation.event_animation_controller").signal(
            session, resolved.page or target, controllerId, signal)
    end,

    -- An item asked to run a common event (the Forbidden Lamp shape). The
    -- engine cannot do this itself: CALL_COMMON_EVENT compiles to a dialogue
'''
)

rtp = Path('rtp/revisions/1.0/data/engine.json')
engine = json.loads(rtp.read_text(encoding='utf-8'))
commands = engine.get('commands')
if not isinstance(commands, list):
    raise SystemExit('RTP engine commands registry missing')
if any(command.get('id') == 'ANIMATION_SIGNAL' for command in commands):
    raise SystemExit('ANIMATION_SIGNAL already exists')
record = {
    'id': 'ANIMATION_SIGNAL',
    'category': 'Presentation',
    'label': 'Signal Event Animation',
    'params': [
        {'key': 'signal', 'type': 'text'},
        {'key': 'eventId', 'type': 'number', 'optional': True},
    ],
    'contexts': ['map', 'common'],
    'interactive': False,
    'description': 'Sends one transient semantic signal to an Event animation controller. Omit eventId to target the Event Program currently running; the signal never changes gameplay state.'
}
insert_at = next((i for i, command in enumerate(commands) if command.get('id') == 'CHANGE_EVENT_PROPERTIES'), len(commands))
commands.insert(insert_at, record)
rtp.write_text(json.dumps(engine, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Self-remove agent infrastructure; the pushed commit contains only product code.
Path('.github/workflows/agent-591-signal-patch.yml').unlink(missing_ok=True)
Path('tools/agent-591-signal-patch.py').unlink(missing_ok=True)
