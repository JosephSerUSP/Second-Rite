-- Shared visibility preference for authored floating 3D navigation models.
local settings = require("engine.user_settings")
local M = {}
function M.isVisible() return settings.get("transitionArrowsVisible", true) == true end
function M.setVisible(value)
    assert(type(value) == "boolean", "transition arrow visibility must be boolean")
    settings.set("transitionArrowsVisible", value)
    return value
end
function M.isArrow(path)
    return type(path) == "string" and path:match("transition_arrow") ~= nil
end
return M
