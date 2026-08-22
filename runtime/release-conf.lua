-- Generic release configuration template. Export materializes the two Project
-- identity tokens below before this becomes the staged game's conf.lua.
-- Installed Thestra runtime must never supply a particular game's save identity
-- or player-facing window title.
function love.conf(t)
    t.identity = __THESTRA_PROJECT_IDENTITY__
    t.window.title = __THESTRA_PROJECT_WINDOW_TITLE__
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
