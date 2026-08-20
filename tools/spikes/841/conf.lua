function love.conf(t)
    t.identity = "SecondRiteSpike841"
    t.window.title = "spike-841"
    t.window.width = 640
    t.window.height = 480
    t.window.resizable = false
    t.window.vsync = 0
    t.console = true
    t.modules.audio = false
    t.modules.sound = false
    t.modules.joystick = false
    t.modules.physics = false
end

-- Never fall through to LOVE's graphical error screen: an unattended spike run
-- would otherwise hang on a modal instead of reporting a failure.
function love.errorhandler(message)
    io.stderr:write("SPIKE841 ERROR: " .. tostring(message) .. "\n"
        .. debug.traceback("", 2) .. "\n")
    io.stderr:flush()
    os.exit(1)
end
