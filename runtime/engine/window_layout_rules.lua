-- Window authoring checks shared by sparse Projects and the canonical fixture.
local rules = {}

function rules.validate(loader, check)
    local mode = loader.system and loader.system.ui and loader.system.ui.windowskinMode
    if mode ~= nil then
        check(mode == "skin" or mode == "overlay",
            "system.ui.windowskinMode must be 'skin' or 'overlay'")
    end
    local function layout(value, where)
        if type(value) ~= "table" then return end
        if value.textScale ~= nil then
            local scale = value.textScale
            check(type(scale) == "number" and scale > 0 and scale < math.huge,
                where .. ".textScale must be a positive finite number")
        end
        for i, page in ipairs(value.pages or {}) do
            layout(page, where .. ".pages[" .. i .. "]")
        end
    end
    for id, value in pairs(loader.engine and loader.engine.windowLayout or {}) do
        layout(value, "windowLayout '" .. tostring(id) .. "'")
    end
    for _, scene in ipairs(loader.scenes or {}) do
        for i, value in ipairs(scene.windows or {}) do
            layout(value, "scene '" .. tostring(scene.id) .. "' windows[" .. i .. "]")
        end
    end
end

return rules
