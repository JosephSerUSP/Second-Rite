-- Conservative player-visible projection for #375.
--
-- This is not a second window renderer. Source resolution, filtering, priority,
-- formatting, visibility and cursor evaluation all happen in the generic
-- window renderer's side-effect-free resolveDataState seam. This module only
-- reduces that already-resolved presentation data to facts that can be proven
-- visible without inspecting GameSession or backing list rows.
local window_renderer = require("presentation.window_renderer")
local ui = require("presentation.ui")

local projection = {}
projection.VERSION = 1

local function definitionsById(sceneData)
    local defs = {}
    for _, win in ipairs((sceneData and sceneData.windows) or {}) do
        if win.id then defs[win.id] = win end
    end
    return defs
end

local function findListBlock(winDef)
    for _, block in ipairs((winDef and winDef.content) or {}) do
        if block.type == "list" then return block end
    end
    return nil
end

local function plainLabelSource(listId)
    if type(listId) ~= "string" then return false end
    return listId:match("^term:") ~= nil or listId:match("^static:") ~= nil
end

local function simpleLabelList(entry, winDef, block)
    if entry.style ~= "list" or not block then return false end
    if entry.hasLayout then return false end
    if not plainLabelSource(block.listId) then return false end
    if block.formatRight ~= nil or block.sprite ~= nil
        or block.gaugeValue ~= nil or block.gaugeMax ~= nil
        or block.labelField ~= nil then
        return false
    end
    return true
end

local function visibleIndices(entry, winDef)
    local rows = entry.rows or {}
    if #rows == 0 then return {} end

    -- An explicit visibleRows that covers the resolved row set proves every
    -- row is on-screen. If scrolling exists (or geometry is implicit), expose
    -- only the selected row: the renderer guarantees the cursor is scrolled
    -- into view, while guessing its neighboring slice would duplicate renderer
    -- policy and could leak an offscreen label.
    local authoredVisible = tonumber(winDef and winDef.visibleRows)
    if authoredVisible and authoredVisible >= #rows then
        local indices = {}
        for i = 1, #rows do indices[#indices + 1] = i end
        return indices
    end

    local cursor = math.floor(tonumber(entry.cursor) or 0)
    if cursor >= 1 and cursor <= #rows then return { cursor } end
    return {}
end

local function labelFits(entry, row)
    if not row or type(row.text) ~= "string" then return false end
    if row.icon and row.icon ~= 0 then return false end
    -- Rich-text layout and clipping need renderer-owned projection metadata;
    -- omit them in v1 rather than exposing a string that may be only partly
    -- visible. Plain labels use a deliberately smaller width than drawList's
    -- default content area, so passing this check proves the whole label fits.
    if row.text:find("\\c%[") then return false end
    local maxWidth = ui.toPx(tonumber(entry.width) or 0) - ui.toPx(4)
    if maxWidth <= 0 then return false end
    local font = love.graphics.getFont()
    return font and font:getWidth(row.text) <= maxWidth
end

function projection.resolve(sceneData, state, ctx)
    local resolved = window_renderer.resolveDataState(sceneData, ctx or {}, state)
    local defs = definitionsById(sceneData)
    local result = { version = projection.VERSION, windows = {} }

    for _, entry in ipairs(resolved.windows or {}) do
        if entry.open == true then
            local out = { id = entry.id, style = entry.style }
            local winDef = defs[entry.id]
            local block = findListBlock(winDef)

            if simpleLabelList(entry, winDef, block) then
                local rows = {}
                for _, index in ipairs(visibleIndices(entry, winDef)) do
                    local row = entry.rows and entry.rows[index]
                    if labelFits(entry, row) then
                        local projected = {
                            text = row.text,
                            selected = index == entry.cursor,
                            highlighted = row.highlighted == true,
                        }
                        rows[#rows + 1] = projected
                        if projected.selected then out.selected = projected.text end
                    end
                end
                if #rows > 0 then out.rows = rows end
            end

            -- Free text, titles and complex list cells are intentionally absent
            -- from projection v1. resolveDataState currently materializes their
            -- full strings before clipping/reveal; exporting them here would be
            -- less fair than exporting nothing until presentation owns an exact
            -- visible-text projection for those styles.
            result.windows[#result.windows + 1] = out
        end
    end

    return result
end

return projection
