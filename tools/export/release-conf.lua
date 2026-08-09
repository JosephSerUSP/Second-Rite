-- Release configuration is deliberately separate from the developer conf.lua.
-- Export copies this file as conf.lua, so a distributed game never opens a
-- development console or inherits a workstation-specific window setting.
function love.conf(t)
    t.identity = "SecondRite"
    t.window.title = "Second Rite"
    t.window.width = 768
    t.window.height = 720
    t.window.resizable = true
    t.window.minwidth = 256
    t.window.minheight = 240
    t.window.vsync = 1
    t.window.fullscreen = false
    t.window.fullscreentype = "desktop"
    t.modules.joystick = true
    t.console = false
end
