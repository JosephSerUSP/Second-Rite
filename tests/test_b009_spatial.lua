local json=require("engine.data.json")
local loader=require("engine.data.loader")
local session=require("engine.session").GameSession.new(loader)
local sh=require("engine.scene_host")
local pc=require("engine.player_controller")
local root=assert(os.getenv("THESTRA_REPOSITORY_ROOT"),"B009 test requires repository root")
local function readScene(path)
    local f=assert(io.open(root..path,"r"))
    local text=f:read("*a");f:close()
    return text,json.decode(text)
end
-- The PE Day 1 port (#1423) diverged deliberately in M1 (#1424): its combat
-- now runs on engine/realtime_battle.lua and is covered by
-- tests/test_realtime_battle.lua. This suite covers the B009 lab specimen.
local labText,labScene=readScene("/projects/labs/scene-benchmarks/data/scenes/b009_positioning.json")
local specimen
local original=loader.scenes
local ctx={session=session,loader=loader,party=session.party,events={}}
local function start()
    pc.reset();sh.init(nil);sh.push(specimen.id,ctx)
    return sh.getCurrentState().v
end
local function ticks(count,dt)
    for i=1,count do pc.update(dt,ctx);sh.update(dt,ctx) end
end
local function tap(button) pc.press(button,ctx);pc.release(button) end
local function menu() pc.press("X",ctx);ticks(1,1/60);pc.release("X");ticks(1,1/60) end
local function shoot() tap("A");tap("A") end
local function near(a,b) assert(math.abs(a-b)<1e-7,tostring(a).." ~= "..tostring(b)) end
local function suite()
    loader.scenes={specimen}
    local v=start();v.enemyTimer=100
    pc.press("RIGHT",ctx);ticks(60,1/60);near(v.px,.5)
    pc.release("RIGHT");local x=v.px;ticks(20,1/60);near(v.px,x)
    pc.press("RIGHT",ctx);ticks(180,1/60);near(v.px,2.2)
    v=start();pc.press("RIGHT",ctx);pc.press("UP",ctx);ticks(30,1/60)
    local a,b=v.px,v.py
    v=start();pc.press("RIGHT",ctx);pc.press("UP",ctx);ticks(10,.05)
    near(v.px,a);near(v.py,b);near(math.sqrt((v.px+2)^2+(v.py-1.2)^2),1.25)
    -- Readiness opens a command menu; combat and held movement pause there.
    v=start();v.atb=100;menu();assert(v.ui==1)
    local enemyX,enemyTimer,charge=v.ex,v.enemyTimer,v.atb
    pc.press("RIGHT",ctx);ticks(120,1/60)
    near(v.px,-2);near(v.ex,enemyX);near(v.enemyTimer,enemyTimer);near(v.atb,charge)
    tap("B");assert(v.ui==0);ticks(1,1/60);assert(v.px>-2);pc.release("RIGHT")
    -- Aiming is separate; the exact Euclidean boundary is inclusive.
    v=start();v.ex=2;v.ey=1.2;v.atb=100
    tap("A");assert(v.ui==2);near(v.ehp,20);tap("A")
    near(v.ehp,15);near(v.ammo,10);near(v.atb,0)
    v=start();v.ex=1;v.ey=4.2;v.atb=100;shoot()
    near(v.ehp,20);near(v.ammo,10);near(v.atb,0);near(v.damage,0)
    v=start();v.ammo=0;v.ex=-2;v.ey=1.2;v.atb=100;shoot();near(v.ehp,20)
    -- Healing consumes its resource and the AT turn exactly once.
    v=start();v.hp=10;v.atb=100;menu();tap("DOWN");tap("A")
    assert(v.ui==3);tap("A");near(v.hp,40);near(v.pe,70);near(v.atb,0)
    v=start();v.hp=10;v.atb=100;v.pe=20;menu();tap("DOWN");tap("A");tap("A")
    near(v.hp,10);near(v.pe,20);near(v.atb,100)
    v=start();v.hp=20;v.atb=100;menu();tap("DOWN");tap("DOWN");tap("A");tap("A")
    near(v.hp,45);near(v.medicine,0);near(v.atb,0)
    -- Victory freezes. Loot is obtained once before replay resets the lab.
    v=start();v.ex=-2;v.ey=1.2;v.ehp=7;v.atb=100;shoot();assert(v.mode==2)
    local ey=v.ey;pc.press("RIGHT",ctx);ticks(180,1/60)
    near(v.px,-2);near(v.ey,ey);near(v.atb,0);near(v.hp,45);near(v.flash,0)
    pc.release("RIGHT");tap("A");near(v.ammo,16);assert(v.rewarded==1)
    tap("A");assert(v.mode==0);near(v.ehp,20);near(v.hp,45);near(v.ammo,11)
    -- Locked bite can hit or be evaded; projectiles cannot hit twice.
    v=start();v.enemyMode=2;v.enemyTimer=.05;v.tx=v.px;v.ty=v.py
    ticks(5,1/60);near(v.hp,41)
    v=start();v.enemyMode=2;v.enemyTimer=.05;v.tx=5;v.ty=4
    ticks(5,1/60);near(v.hp,45)
    v=start();v.enemyTimer=100;v.fireT=0;v.fireX=v.px;v.fireY=v.py;v.hit0=1;v.hit2=1
    ticks(1,1/60);near(v.hp,41);ticks(4,1/60);near(v.hp,41)
    v=start();v.hp=4;v.enemyMode=2;v.enemyTimer=.05;v.tx=v.px;v.ty=v.py
    ticks(5,1/60);assert(v.mode==3);near(v.hp,0)
    v=start();v.atb=100;menu();tap("DOWN");tap("DOWN");tap("DOWN");tap("A")
    assert(v.mode==4);ticks(120,1/60);near(v.hp,45);near(v.exp,0)
    -- Expanded surfaces must reveal real room geometry and keep the HUD on
    -- the left edge, while classic remains a usable player-selected profile.
    local surface=require("presentation.surface")
    local previous=surface.getProfileId()
    local wr=require("presentation.window_renderer")
    v=start()
    for _,profile in ipairs({"classic","four_three","wide"}) do
        surface.setProfile(profile)
        local resolved=wr.resolveState(sh.getCurrentState(),specimen,ctx)
        local byId={}
        for _,window in ipairs(resolved.windows) do byId[window.id]=window end
        local ox,oy=surface.compositionOrigin()
        near(byId.world.x*8+ox,0);near(byId.world.y*8+oy,0)
        near(byId.world.width*8,surface.renderWidth())
        near(byId.world.height*8,surface.renderHeight())
        near(byId.combat_hud.x*8+ox,12)
    end
    surface.setProfile(previous)
    local camera=require("presentation.scene_model_view")
    local r,u,forward=camera.cameraBasis({0,-8,7},{0,5,1})
    local function dot(a,b) return a[1]*b[1]+a[2]*b[2]+a[3]*b[3] end
    near(dot(r,u),0);near(dot(r,forward),0);near(dot(u,forward),0)
    near(dot(r,r),1);near(dot(u,u),1);near(dot(forward,forward),1)
    local sx,sy=camera.projectPoint({0,5,1},{position={0,-8,7},target={0,5,1},fov=43},256,240)
    near(sx,128);near(sy,120)
    assert(camera.projectPoint({0,-10,7},{position={0,-8,7},target={0,5,1},fov=43},256,240)==nil)
    -- Pre-rendered-style plate: the camera stays put and the window slides
    -- across its plate to keep the followed point centred, stopping at the
    -- plate's edges. A [1,1] frame is the plain projection.
    local cam={position={0,-8,7},target={0,5,1},fov=60,frame={size={2,2}}}
    local identity=camera.frameWindow({position=cam.position,target=cam.target,fov=60},256,240,{3,4,0})
    near(identity[1],1);near(identity[2],1);near(identity[3],0);near(identity[4],0)
    local follow={1.2,6,0.5}
    local frame=camera.frameWindow(cam,256,240,follow)
    local fx,fy=camera.projectPoint(follow,cam,256,240,frame)
    assert(math.abs(fx-128)<=1 and math.abs(fy-120)<=1,"plate window must centre the followed point")
    local far=camera.frameWindow(cam,256,240,{400,6,0.5})
    near(far[3],-1)   -- clamped: the window rests on the plate's right edge
    local errors={}
    camera.validate({camera={},models="invalid"},function(valid,message)
        if not valid then errors[#errors+1]=message end
    end,function() return false end,function() return false end)
    assert(#errors>=4,"Malformed viewport must fail validation without crashing")
end
local ok,err=pcall(function()
    specimen=labScene;suite()
end)
loader.scenes=original;pc.reset();sh.init(nil)
assert(ok,err)
print("B009 SPATIAL TESTS OK")
