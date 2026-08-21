function love.conf(t)
    t.identity = "SecondRiteSpike837"
    t.window.title = "spike-837"
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

function love.errorhandler(message)
    io.stderr:write("SPIKE837 ERROR: " .. tostring(message) .. "\n"
        .. debug.traceback("", 2) .. "\n")
    io.stderr:flush()
    os.exit(1)
end
