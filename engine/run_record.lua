local json = require("data.json")
local controls = require("engine.player_controls")

local record = {}
record.VERSION = 1

function record.new(meta)
    meta = meta or {}
    assert(type(meta.project) == "table", "run record requires project identity")
    assert(type(meta.runtime) == "table", "run record requires runtime identity")
    return {
        schema = "thestra.player-run",
        version = record.VERSION,
        id = meta.id,
        project = meta.project,
        runtime = meta.runtime,
        start = meta.start or { kind = "new-game" },
        deterministicSeed = meta.deterministicSeed,
        experientialJournalRef = meta.experientialJournalRef,
        steps = {},
        outcome = nil,
    }
end

function record.append(run, event)
    assert(run and run.schema == "thestra.player-run", "invalid player run record")
    assert(type(event) == "table", "run event must be a table")
    assert(type(event.frame) == "number", "run event requires frame boundary")
    assert(type(event.observation) == "table", "run event requires player-visible observation")
    if event.input then
        assert(type(event.input.button) == "string", "input event requires logical button")
        assert(controls.contains(event.input.button), "input event button is not a canonical logical control")
        assert(event.input.phase == "press" or event.input.phase == "hold" or event.input.phase == "release",
            "input phase must be press/hold/release")
    end
    run.steps[#run.steps + 1] = event
    return event
end

function record.finish(run, outcome)
    assert(type(outcome) == "table" and type(outcome.status) == "string",
        "run outcome requires status")
    run.outcome = outcome
    return run
end

function record.encode(run)
    assert(run and run.schema == "thestra.player-run", "invalid player run record")
    return json.encode(run)
end

return record
