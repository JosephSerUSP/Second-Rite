-- tests/test_scene_timing_authoring.lua
-- Unit tests for Scene timing contract, SCRIPT ctx.time surface, and formula evaluation (#386/#518).

local sceneUpdateContract = require("engine.scene_update_contract")
local formula = require("engine.formula")
local interpreter = require("engine.interpreter")
local session = require("engine.session")
local loader = require("data.loader")

-- 1. Contract resolution for authored vs default timing
do
    -- Legacy/default: absent update config
    local defaultScene = { id = "menu_test", name = "Test Menu", kind = "menu" }
    assert(sceneUpdateContract.resolve(defaultScene) == nil, "default scene must resolve to nil updateConfig")

    -- Authored fixed timing
    local fixedScene = {
        id = "snake_test",
        name = "Snake",
        kind = "menu",
        update = {
            mode = "fixed",
            step = 0.0166666666666667,
            maxCatchUp = 8,
        },
    }
    local cfg = sceneUpdateContract.resolve(fixedScene)
    assert(cfg ~= nil, "fixed scene must resolve updateConfig")
    assert(cfg.mode == "fixed", "mode must be fixed")
    assert(math.abs(cfg.step - 0.0166666666666667) < 1e-12, "step must match")
    assert(cfg.maxCatchUp == 8, "maxCatchUp must match")

    -- Omitted optional maxCatchUp defaults to 8
    local fixedSceneDefaultCatchUp = {
        id = "fixed_default_catchup",
        update = {
            mode = "fixed",
            step = 0.0333333333333333,
        },
    }
    local cfg2 = sceneUpdateContract.resolve(fixedSceneDefaultCatchUp)
    assert(cfg2.maxCatchUp == 8, "omitted maxCatchUp must default to 8")

    -- Validation rejections
    local invalidCases = {
        { scene = { update = "not_a_table" }, err = "must be an object" },
        { scene = { update = { mode = "variable", step = 0.016 } }, err = "mode must be 'fixed'" },
        { scene = { update = { mode = "fixed", step = 0 } }, err = "finite positive number" },
        { scene = { update = { mode = "fixed", step = -0.1 } }, err = "finite positive number" },
        { scene = { update = { mode = "fixed", step = 0.016, maxCatchUp = 0 } }, err = "from 1 to 120" },
        { scene = { update = { mode = "fixed", step = 0.016, maxCatchUp = 121 } }, err = "from 1 to 120" },
        { scene = { update = { mode = "fixed", step = 0.016, maxCatchUp = 8.5 } }, err = "integer" },
    }
    for _, tc in ipairs(invalidCases) do
        local ok, err = pcall(sceneUpdateContract.resolve, tc.scene)
        assert(not ok, "expected error for invalid scene update: " .. tc.err)
        assert(tostring(err):find(tc.err, 1, true), "error message mismatch: " .. tostring(err))
    end
end

-- 2. SCRIPT ctx.time surface
do
    local sess = session.GameSession.new(loader)
    local timeView = setmetatable({}, {
        __index = { dt = 0.0166666666666667, tick = 120, elapsed = 2.0 },
        __newindex = function() error("attempt to mutate read-only time view", 0) end,
    })

    -- During fixed on_frame: ctx.time is exposed
    local ctx = {
        session = sess,
        time = timeView,
        v = { time = timeView, result = 0, readDt = 0, readTick = 0 },
    }
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.readDt = ctx.time.dt; ctx.v.readTick = ctx.time.tick; ctx.v.result = ctx.time.elapsed" },
    }, ctx)

    assert(math.abs(ctx.v.readDt - 0.0166666666666667) < 1e-12, "SCRIPT must read ctx.time.dt")
    assert(ctx.v.readTick == 120, "SCRIPT must read ctx.time.tick")
    assert(ctx.v.result == 2.0, "SCRIPT must read ctx.time.elapsed")

    -- Mutation of ctx.time must fail (read-only transient context)
    local okMutate, _ = pcall(function()
        interpreter.runImmediate({
            { cmd = "SCRIPT", code = "ctx.time.dt = 99" },
        }, ctx)
    end)
    assert(not okMutate, "mutating ctx.time must fail")

    -- Outside fixed on_frame: ctx.time is nil
    local ctxNoTime = {
        session = sess,
        v = { testTime = 999 },
    }
    interpreter.runImmediate({
        { cmd = "SCRIPT", code = "ctx.v.testTime = ctx.time" },
    }, ctxNoTime)
    assert(ctxNoTime.v.testTime == nil, "ctx.time must be nil outside fixed on_frame")
end

-- 3. Formula evaluation of time tokens
do
    local sess = session.GameSession.new(loader)
    local timeView = { dt = 0.05, tick = 10, elapsed = 0.5 }
    local ctx = {
        session = sess,
        time = timeView,
        v = { time = timeView },
    }

    local dtVal = formula.eval("time.dt", ctx)
    assert(math.abs(dtVal - 0.05) < 1e-12, "formula must evaluate time.dt")

    local tickVal = formula.eval("time.tick", ctx)
    assert(tickVal == 10, "formula must evaluate time.tick")

    local elapsedVal = formula.eval("time.elapsed", ctx)
    assert(math.abs(elapsedVal - 0.5) < 1e-12, "formula must evaluate time.elapsed")

    local combinedVal = formula.eval("time.elapsed + (time.tick * time.dt)", ctx)
    assert(math.abs(combinedVal - 1.0) < 1e-12, "formula must evaluate combined expression")
end

-- 4. a003_snake.json contract verification
do
    local json = require("data.json")
    local file, err = io.open("projects/labs/scene-benchmarks/data/scenes/a003_snake.json", "rb")
    assert(file, "could not open a003_snake.json: " .. tostring(err))
    local content = file:read("*a")
    file:close()
    local snakeData = json.decode(content)
    assert(snakeData, "a003_snake.json must decode")
    local cfg = sceneUpdateContract.resolve(snakeData)
    assert(cfg ~= nil, "a003_snake must resolve valid fixed update config")
    assert(cfg.mode == "fixed", "a003_snake mode must be fixed")
    assert(math.abs(cfg.step - 0.0166666666666667) < 1e-12, "a003_snake step must be 60 Hz")
    assert(cfg.maxCatchUp == 8, "a003_snake maxCatchUp must be 8")
end

print("=== test_scene_timing_authoring: ALL OK ===")
