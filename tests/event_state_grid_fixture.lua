-- Explicit grid fixture for persistent event-state tests, independent of town art.
return function(loader)
    local previous = loader.maps[1]
    loader.maps[1] = require("engine.data.json").decode(assert(love.filesystem.read("tests/fixtures/event_state_grid_map.json")))
    return function() loader.maps[1] = previous end
end
