function love.conf(t)
    t.identity = "SecondRite"
    t.window.title = "Second Rite"
    t.window.width = 768 -- 256 * 3
    t.window.height = 720 -- 240 * 3
    t.window.resizable = true
    t.window.minwidth = 256
    t.window.minheight = 240
    t.window.vsync = 1
    t.window.fullscreen = false
    t.window.fullscreentype = "desktop"
    t.modules.joystick = true
    t.modules.keyboard = true
    t.modules.mouse = true
    t.modules.sound = true
    t.modules.system = true
    t.modules.timer = true
    t.modules.window = true
    t.modules.graphics = true
    t.modules.image = true
    t.modules.audio = true
    t.console = true
end

-- LÖVE's normal graphical error handler intentionally keeps the process alive
-- so a human can read the crash screen. That is correct for ordinary play but
-- dangerous for unattended boot smoke: "process is still alive" can otherwise
-- certify a crash screen as a healthy game. CI/runtime probes opt into fail-fast
-- behavior explicitly; normal launches retain LÖVE's standard error screen.
if os.getenv("THESTRA_CI_FAIL_ON_ERROR") == "1" then
    function love.errorhandler(message)
        local text = "THESTRA RUNTIME ERROR: " .. tostring(message) .. "\n"
        if io and io.stderr and io.stderr.write then
            io.stderr:write(text)
            if io.stderr.flush then io.stderr:flush() end
        else
            print(text)
        end
        os.exit(1)
    end
end
