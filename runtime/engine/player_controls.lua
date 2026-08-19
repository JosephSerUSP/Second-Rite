local input_map = require("engine.input_map")

local controls = {}

function controls.contains(name)
    if type(name) ~= "string" then return false end
    return input_map.getBindings()[name] ~= nil
end

return controls
