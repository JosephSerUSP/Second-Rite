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
local ANGLE = math.rad(35) -- Off-axis, so a silhouette is not read edge-on.

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

    local columns = math.min(COLUMNS, #entries)
    local rows = math.ceil(#entries / columns)
    local cellHeight = CELL + LABEL_HEIGHT
    local sheet = love.graphics.newCanvas(columns * CELL, rows * cellHeight)

    love.graphics.setCanvas(sheet)
    love.graphics.clear(0.10, 0.10, 0.12, 1)

    for index, entry in ipairs(entries) do
        local column = (index - 1) % columns
        local row = math.floor((index - 1) / columns)
        local x, y = column * CELL, row * cellHeight

        -- Alternating cell backing: without it, adjacent dark models on a flat
        -- field read as one blob and the grid is impossible to count.
        if (column + row) % 2 == 0 then
            love.graphics.setColor(1, 1, 1, 0.04)
            love.graphics.rectangle("fill", x, y, CELL, cellHeight)
        end

        love.graphics.setColor(1, 1, 1, 1)
        item_model_view.draw(x, y, CELL, CELL, entry.model,
            "sheet_" .. index, entry.name, ANGLE)

        love.graphics.setColor(0.75, 0.75, 0.8, 1)
        local label = entry.name
        while label ~= "" and love.graphics.getFont():getWidth(label) > CELL - 4 do
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
