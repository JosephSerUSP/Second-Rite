-- Installation-owned presentation contract (#967, from the #965 audit).
--
-- `presentation/presentation.json` holds the windowskin/target atlas
-- rectangles, the UI grid metrics and the colour vocabulary that BOTH the LOVE
-- renderer and the browser adapter (#968) draw from. This module is the LOVE
-- host's reader for it; `tools/presentation/contract.js` is the browser
-- publication's reader of the same file. One spelling, two hosts.
--
-- Every accessor below is fail-loud. A missing file, a missing key or a
-- malformed rectangle is authored-data corruption, not a condition to render
-- around: the honest failure is a hard error at load, the same way the data
-- loader rejects an unknown skill scope. This is deliberately NOT the same
-- thing as a missing windowskin PNG, which `ui.init` still degrades from on
-- purpose -- a panel wearing the wrong skin beats a panel that draws nothing.
local json = require("engine.data.json")

local PATH = "presentation/presentation.json"

local contract = {}

local function fail(message)
    error("presentation contract: " .. message .. " (" .. PATH .. ")", 0)
end

local data
do
    local contents = love.filesystem.read(PATH)
    if not contents then fail("installation presentation contract is missing") end
    local ok, decoded = pcall(json.decode, contents)
    if not ok or type(decoded) ~= "table" then
        fail("is not valid JSON: " .. tostring(decoded))
    end
    if decoded.version ~= 1 then
        fail("declares unsupported version " .. tostring(decoded.version))
    end
    data = decoded
end

contract.data = data

-- Dotted lookup so a caller names the fact it wants and the error names the
-- exact path that was absent, rather than a nil index three frames later.
local function at(path)
    local node = data
    for segment in path:gmatch("[^%.]+") do
        if type(node) ~= "table" then fail("'" .. path .. "' is not reachable") end
        node = node[segment]
        if node == nil then fail("'" .. path .. "' is missing") end
    end
    return node
end
contract.at = at

function contract.number(path)
    local value = at(path)
    if type(value) ~= "number" then
        fail("'" .. path .. "' must be a number, got " .. type(value))
    end
    return value
end

function contract.name(path)
    local value = at(path)
    if type(value) ~= "string" or value == "" then
        fail("'" .. path .. "' must be a non-empty string")
    end
    return value
end

-- An RGB or RGBA array, returned as a fresh table so a consumer that mutates
-- a colour in place cannot corrupt the contract for every other consumer.
function contract.color(path)
    local value = at(path)
    if type(value) ~= "table" or (#value ~= 3 and #value ~= 4) then
        fail("'" .. path .. "' must be a 3- or 4-component colour array")
    end
    local out = {}
    for i = 1, #value do
        if type(value[i]) ~= "number" then
            fail("'" .. path .. "' component " .. i .. " is not a number")
        end
        out[i] = value[i]
    end
    return out
end

-- One atlas rectangle, as the four numbers love.graphics.newQuad wants.
function contract.rect(path)
    local value = at(path)
    if type(value) ~= "table" then fail("'" .. path .. "' must be a rectangle object") end
    local out = {}
    for index, key in ipairs({ "x", "y", "w", "h" }) do
        local component = value[key]
        if type(component) ~= "number" or component ~= math.floor(component) or component < 0 then
            fail("'" .. path .. "." .. key .. "' must be a non-negative integer")
        end
        if (key == "w" or key == "h") and component == 0 then
            fail("'" .. path .. "." .. key .. "' must be positive")
        end
        out[index] = component
    end
    return out
end

-- Every named rectangle under one atlas part table, built into quads against
-- an image's real dimensions. The part NAMES come from the contract, so a part
-- added there reaches the renderer without a code change, and a part the
-- renderer asks for that the contract does not define fails by name.
function contract.quads(path, imageWidth, imageHeight)
    local parts = at(path)
    if type(parts) ~= "table" then fail("'" .. path .. "' must be an object of rectangles") end
    local out = {}
    for key in pairs(parts) do
        if key:sub(1, 1) ~= "_" then
            local r = contract.rect(path .. "." .. key)
            out[key] = love.graphics.newQuad(r[1], r[2], r[3], r[4], imageWidth, imageHeight)
        end
    end
    return out
end

return contract
