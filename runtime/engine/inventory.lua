-- The inventory ordering contract.
--
-- session.inventory is a sparse id->qty map, so every consumer that speaks
-- in 1-based indices ("use item 3") has to agree on the order those indices
-- number. The window renderer's 'inventory' list source displays that order;
-- the interpreter and the battle item menus index back into it. If any of
-- them sorted differently the player would pick one item and use another,
-- so the comparator lives here rather than being restated per call site.
--
-- Numeric ids sort numerically and ahead of string ids, which sort
-- lexically -- a plain tostring() sort would put id 10 before id 2.

local inventory = {}

function inventory.compareIds(a, b)
    local na, nb = tonumber(a), tonumber(b)
    if na and nb then return na < nb end
    if na then return true end
    if nb then return false end
    return tostring(a) < tostring(b)
end

-- Carried slots include worn equipment. Unstacked quantities occupy one row
-- per unit; an authored meta.carriedStack item occupies one row for its stack.
-- This is the semantic authority that later formula/list/command adapters must
-- consume rather than independently reconstructing carried order.
function inventory.carriedRows(session)
    local rows, ids = {}, {}
    for id, qty in pairs(session.inventory or {}) do
        if qty > 0 then ids[#ids + 1] = id end
    end
    table.sort(ids, inventory.compareIds)
    for _, id in ipairs(ids) do
        local item = assert(session.loader.getItem(id), "Unknown carried item: " .. tostring(id))
        local qty = session.inventory[id]
        local stacked = item.meta and item.meta.carriedStack == true
        for n = 1, stacked and 1 or qty do
            rows[#rows + 1] = { id = id, name = item.name, icon = item.icon or 0,
                qty = stacked and qty or 1, type = item.type, description = item.description or "",
                equipped = false, key = "item:" .. tostring(id) .. ":" .. n }
        end
    end
    for member, battler in pairs(session.party or {}) do
        for slot, item in pairs(battler.equipment or {}) do
            rows[#rows + 1] = { id = item.id, name = item.name, icon = item.icon or 0,
                qty = 1, type = item.type, description = item.description or "", equipped = true,
                key = "equip:" .. member .. ":" .. slot }
        end
    end
    table.sort(rows, function(a, b)
        if a.id ~= b.id then return inventory.compareIds(a.id, b.id) end
        return a.key < b.key
    end)
    local byKey, ordered = {}, {}
    for _, row in ipairs(rows) do byKey[row.key] = row end
    for _, key in ipairs(session.carriedItemOrder or {}) do
        if byKey[key] then ordered[#ordered + 1] = byKey[key]; byKey[key] = nil end
    end
    for _, row in ipairs(rows) do
        if byKey[row.key] then ordered[#ordered + 1] = row end
    end
    return ordered
end

function inventory.moveCarried(session, from, to)
    local rows = inventory.carriedRows(session)
    assert(rows[from] and rows[to], "Carried item move index out of range")
    rows[from], rows[to] = rows[to], rows[from]
    session.carriedItemOrder = {}
    for _, row in ipairs(rows) do session.carriedItemOrder[#session.carriedItemOrder + 1] = row.key end
end

return inventory
