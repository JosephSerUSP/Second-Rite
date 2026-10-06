local json=require("engine.data.json")
local loader=require("engine.data.loader")
local session=require("engine.session").GameSession.new(loader)
local sh=require("engine.scene_host")
local pc=require("engine.player_controller")
local root=assert(os.getenv("THESTRA_REPOSITORY_ROOT"),"B009 test requires repository root")
local f=assert(io.open(root.."/projects/labs/scene-benchmarks/data/scenes/b009_positioning.json","r"))
local specimen=json.decode(f:read("*a"));f:close()
local original=loader.scenes
local ctx={session=session,loader=loader,party=session.party,events={}}
local function start()
    pc.reset();sh.init(nil);sh.push(specimen.id,ctx)
    return sh.getCurrentState().v
end
local function ticks(count,dt)
    for i=1,count do pc.update(dt,ctx);sh.update(dt,ctx) end
end
local function near(a,b) assert(math.abs(a-b)<1e-7,tostring(a).." ~= "..tostring(b)) end
local ok,err=pcall(function()
    loader.scenes={specimen}
    local v=start()
    pc.press("RIGHT",ctx);ticks(60,1/60);near(v.px,2.8)
    pc.release("RIGHT");local x=v.px;ticks(20,1/60);near(v.px,x)
    v=start();pc.press("RIGHT",ctx);pc.press("UP",ctx);ticks(30,1/60)
    local a,b=v.px,v.py
    v=start();pc.press("RIGHT",ctx);pc.press("UP",ctx);ticks(10,.05)
    near(v.px,a);near(v.py,b);near(math.sqrt(v.px^2+(v.py-1)^2),1.5)
    v=start();v.ex=4;v.ey=1;v.atb=100
    pc.press("A",ctx);pc.release("A");near(v.ehp,75);near(v.atb,0)
    v=start();v.ex=3;v.ey=4;v.atb=100
    pc.press("A",ctx);pc.release("A");near(v.ehp,100);near(v.atb,100)
    v=start();v.ex=0;v.ey=1;v.ehp=25;v.atb=100
    pc.press("A",ctx);pc.release("A");assert(v.mode==2)
    local ey=v.ey;pc.press("RIGHT",ctx);ticks(180,1/60)
    near(v.px,0);near(v.ey,ey);near(v.atb,0);near(v.hp,100)
    pc.release("RIGHT");pc.press("A",ctx);pc.release("A")
    assert(v.mode==0);near(v.ehp,100);near(v.hp,100)
    v=start();v.enemyMode=1;v.enemyTimer=.05;v.tx=v.px;v.ty=v.py
    ticks(5,1/60);near(v.hp,82)
    v=start();v.enemyMode=1;v.enemyTimer=.05;v.tx=2.8;v.ty=7
    ticks(5,1/60);near(v.hp,100)
    v=start();v.hp=18;v.enemyMode=1;v.enemyTimer=.05;v.tx=v.px;v.ty=v.py
    ticks(5,1/60);assert(v.mode==3);near(v.hp,0)
    local camera=require("presentation.scene_model_view")
    local r,u,forward=camera.cameraBasis({0,-8,7},{0,5,1})
    local function dot(a,b) return a[1]*b[1]+a[2]*b[2]+a[3]*b[3] end
    near(dot(r,u),0);near(dot(r,forward),0);near(dot(u,forward),0)
    near(dot(r,r),1);near(dot(u,u),1);near(dot(forward,forward),1)
    local errors={}
    camera.validate({camera={},models="invalid"},function(valid,message)
        if not valid then errors[#errors+1]=message end
    end,function() return false end,function() return false end)
    assert(#errors>=4,"Malformed viewport must fail validation without crashing")
end)
loader.scenes=original;pc.reset();sh.init(nil)
assert(ok,err)
print("B009 SPATIAL TESTS OK")
