local marker=require('presentation.transition_markers')
local settings=require('engine.user_settings')
local passed=0
local function check(value,label) assert(value,label); passed=passed+1;print('  [PASS] '..label) end
settings.pinForCapture()
check(marker.isVisible(),'navigation markers start visible')
marker.setVisible(false);check(not marker.isVisible(),'player preference hides markers')
marker.setVisible(true);check(marker.isVisible(),'player preference restores markers')
local loader=require('engine.data.loader');loader.init()
local game=require('engine.session').GameSession.new(loader)
local interpreter=require('engine.interpreter')
interpreter.bindPresentation({getTransitionArrowsVisible=marker.isVisible,setTransitionArrowsVisible=marker.setVisible})
marker.setVisible(true)
local host=require('engine.scene_host');local ctx={loader=loader,session=game}
host.init(nil);host.goto_scene('options',ctx)
local scene=host.getCurrentSceneData(ctx);local row
for i,c in ipairs(scene.config.optionsCommands) do if c.id=='navigation_arrows' then row=i end end
check(row~=nil,'authored Options exposes navigation arrows')
for i=2,row do host.buttonpressed('DOWN',ctx);host.update(1,ctx) end
host.buttonpressed('A',ctx);host.update(1,ctx)
check(not marker.isVisible(),'Options button dispatch hides arrows through the real hook')
host.buttonpressed('A',ctx);host.update(1,ctx)
check(marker.isVisible(),'Options button dispatch restores arrows')
host.init(nil);interpreter.bindPresentation(nil);settings.reset()
local fs=love.filesystem;local stored
love.filesystem={getInfo=function() return stored and {} end,read=function() return stored end,
 write=function(_,contents) stored=contents;return true end}
marker.setVisible(false);settings.reset()
check(not marker.isVisible(),'hidden preference survives settings reload')
marker.setVisible(true);settings.reset()
check(marker.isVisible(),'visible preference survives settings reload')
love.filesystem=fs;settings.reset()
print('=== Transition Markers: '..passed..' passed ===')
