-- Contact sheet of every item model, rendered through the REAL item viewer.
--
-- Model review kept happening in prose and pixel counts, which is not a thing
-- an owner can look at. This renders each item through
-- presentation.item_model_view -- the same turntable, lighting, dithering and
-- material passes the game uses -- and lays the results out in one PNG.
--
-- It is a dev tool: labels use the default LOVE font rather than the game's
-- windowskin, because the subject under review is the model, not the UI.
local item_model_sheet = {}

local item_model_view = require("presentation.item_model_view")

local CELL = 96
local LABEL_HEIGHT = 12
local COLUMNS = 14

-- One frozen viewpoint hides exactly the defects a review is for. Yaw alone is
-- not enough either: the game's 10-degree tilt never shows the top of a plate
-- or the underside of a bowl, which is where an unclosed base or a missing
-- interior goes unnoticed. Each view is an explicit {yaw, tilt} pair, and the
-- set deliberately includes a high angle looking down and one looking up.
local VIEWS = {
    { yaw = math.rad(20), tilt = math.rad(10) },   -- the in-game presentation angle
    { yaw = math.rad(110), tilt = math.rad(10) },
    { yaw = math.rad(45), tilt = math.rad(70) },   -- from above
    { yaw = math.rad(45), tilt = math.rad(-55) },  -- from below
}

local function collectEntries(loader, onlyNames)
    local entries = {}
    for _, item in ipairs(loader.items or {}) do
        local model = item.model
        if model and model ~= "" then
            if not onlyNames or onlyNames[item.name] then
                entries[#entries + 1] = { name = item.name, model = model }
            end
        end
    end
    table.sort(entries, function(a, b) return a.name < b.name end)
    return entries
end

-- `onlyPath` optionally names a newline-separated list of item names, so a
-- cohort can be reviewed on its own instead of against 200 neighbours.
function item_model_sheet.run(loader, onlyPath, outputName)
    local onlyNames = nil
    if onlyPath and onlyPath ~= "" then
        local text = love.filesystem.read(onlyPath)
        if not text then
            error("item-sheet: filter list not found: " .. tostring(onlyPath), 0)
        end
        onlyNames = {}
        for line in text:gmatch("[^\r\n]+") do
            local trimmed = line:match("^%s*(.-)%s*$")
            if trimmed ~= "" then onlyNames[trimmed] = true end
        end
    end

    local entries = collectEntries(loader, onlyNames)
    if #entries == 0 then
        error("item-sheet: no item models matched", 0)
    end

    -- Each entry occupies a block of #VIEWS cells side by side, so the grid is
    -- counted in blocks rather than in items.
    local perEntry = #VIEWS
    local blockWidth = CELL * perEntry
    local columns = math.max(1, math.min(math.floor(COLUMNS / perEntry), #entries))
    local rows = math.ceil(#entries / columns)
    local cellHeight = CELL + LABEL_HEIGHT
    local sheet = love.graphics.newCanvas(columns * blockWidth, rows * cellHeight)

    love.graphics.setCanvas(sheet)
    love.graphics.clear(0.10, 0.10, 0.12, 1)

    for index, entry in ipairs(entries) do
        local column = (index - 1) % columns
        local row = math.floor((index - 1) / columns)
        local x, y = column * blockWidth, row * cellHeight

        -- Alternating block backing: without it, adjacent dark models on a flat
        -- field read as one blob and the grid is impossible to count.
        if (column + row) % 2 == 0 then
            love.graphics.setColor(1, 1, 1, 0.04)
            love.graphics.rectangle("fill", x, y, blockWidth, cellHeight)
        end

        love.graphics.setColor(1, 1, 1, 1)
        for viewIndex, view in ipairs(VIEWS) do
            -- A distinct state key per view, or the viewer's own rotation
            -- clock would fight the explicit angle between cells.
            item_model_view.draw(x + (viewIndex - 1) * CELL, y, CELL, CELL, entry.model,
                "sheet_" .. index .. "_" .. viewIndex, entry.name, view.yaw, view.tilt)
        end

        love.graphics.setColor(0.75, 0.75, 0.8, 1)
        local label = entry.name
        while label ~= "" and love.graphics.getFont():getWidth(label) > blockWidth - 4 do
            label = label:sub(1, #label - 1)
        end
        love.graphics.print(label, x + 2, y + CELL)
    end

    love.graphics.setCanvas()
    love.graphics.setColor(1, 1, 1, 1)

    local name = (outputName and outputName ~= "" and outputName) or "item-model-sheet.png"
    sheet:newImageData():encode("png", name)
    print(string.format("ITEM SHEET OK: %d models, %dx%d, written to %s",
        #entries, sheet:getWidth(), sheet:getHeight(),
        love.filesystem.getSaveDirectory() .. "/" .. name))
    return #entries
end

return item_model_sheet
