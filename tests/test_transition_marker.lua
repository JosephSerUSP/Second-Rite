-- Semantic orientation tests for transition-arrow geometry.
local marker = require("presentation.transition_marker")

local function near(actual, expected, message)
    if math.abs(actual - expected) > 0.000001 then
        error(message .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual), 0)
    end
end

local baseX, baseY, baseZ = marker.worldPoint("away", { 0, 0, 0 }, {
    depthX = 7.8, arrowY = 10.5, groundZ = 0,
})
local tipX, tipY, tipZ = marker.worldPoint("away", { 0, 0, 1.04 }, {
    depthX = 7.8, arrowY = 10.5, groundZ = 0,
})
near(baseZ, 0.15, "flat depth marker starts at its authored base height")
near(tipZ, baseZ, "flat depth exit keeps the arrow shaft level")
near(tipX - baseX, 1.04, "away marker points through the doorway in world depth")
marker.assertFlatDepthExit("away", { baseX, baseY, baseZ }, { tipX, tipY, tipZ })

local leftBaseX, leftBaseY, leftBaseZ = marker.worldPoint("left", { 0, 0, 0 }, {
    depthX = 7.8, arrowY = 10.5, groundZ = 0, minY = -2.8, maxY = 32.9,
})
local leftTipX, leftTipY, leftTipZ = marker.worldPoint("left", { 0, 0, 1.04 }, {
    depthX = 7.8, arrowY = 10.5, groundZ = 0, minY = -2.8, maxY = 32.9,
})
near(leftTipY - leftBaseY, -1.04, "left marker points along the lane")
near(leftTipZ, leftBaseZ, "left marker stays at its fixed presentation height")

local bad = pcall(function()
    marker.assertFlatDepthExit("away", { 0, 0, 0 }, { 0, 0, 0.1 })
end)
if bad then error("flat depth exit regression must reject upward-pointing arrow geometry", 0) end

local invalid = pcall(function()
    marker.worldPoint("up", { 0, 0, 0 }, {})
end)
if invalid then error("unknown transition marker direction must fail loudly", 0) end

print("TRANSITION MARKER OK")
