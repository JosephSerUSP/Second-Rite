-- Authored, perspective 3D Scene window. This observes resolved Scene state;
-- movement/combat/collision remain event programs, never renderer mutations.
local models = require("presentation.model_resource")
local core = require("presentation.retro_mesh_shader")
local formula = require("engine.formula")
local surface = require("presentation.surface")
local view = {}
local shader, buffers
local vertex = [[
#ifdef VERTEX
attribute vec3 VertexNormal;
varying vec2 worldUV;
varying float affineScale;
varying vec4 worldColor;
varying vec2 sheenUV;
uniform vec3 cameraPosition;
uniform vec3 cameraRight;
uniform vec3 cameraUp;
uniform vec3 cameraForward;
uniform vec3 objectPosition;
uniform vec3 objectScale;
uniform float objectYaw;
uniform float focalLength;
uniform float aspectRatio;
uniform vec3 materialColor;
vec4 position(mat4 transform_projection, vec4 vertex_position) {
    float c=cos(objectYaw), s=sin(objectYaw);
    vec3 p=VertexPosition.xyz*objectScale;
    p=vec3(p.x*c-p.y*s,p.x*s+p.y*c,p.z)+objectPosition;
    vec3 n=VertexNormal/objectScale;
    n=normalize(vec3(n.x*c-n.y*s,n.x*s+n.y*c,n.z));
    float light=0.55+0.45*max(0.0,dot(n,normalize(vec3(-0.4,-0.6,1.0))));
    worldColor=vec4(VertexColor.rgb*materialColor*light,VertexColor.a);
    vec3 d=p-cameraPosition;
    float depth=dot(d,cameraForward);
    float clipZ=1.002002*depth-0.2002002;
    worldUV=VertexTexCoord.xy; affineScale=1.0;
    sheenUV=vec2(n.x*.5+.5,.5-n.z*.5);
    return vec4(dot(d,cameraRight)*focalLength/aspectRatio,
        -dot(d,cameraUp)*focalLength,clipZ,depth);
}
#endif
]]

local function number(v, env, label, fallback)
    if v == nil then return fallback end
    if type(v) == "number" then return v end
    local n, err = formula.eval(v,env)
    assert(not err and type(n)=="number" and n==n and math.abs(n)<math.huge,
        "3D Scene "..label..": "..tostring(err or n))
    return n
end
local function vector(v, env, label, fallback)
    local result={}
    for i=1,3 do result[i]=number(v and v[i],env,label,fallback[i]) end
    return result
end
local function normal(v)
    local len=math.sqrt(v[1]^2+v[2]^2+v[3]^2)
    assert(len>0,"3D Scene camera has degenerate basis")
    return {v[1]/len,v[2]/len,v[3]/len}
end
function view.cameraBasis(position,target)
    local f=normal({target[1]-position[1],target[2]-position[2],target[3]-position[3]})
    local r=normal({f[2],-f[1],0})
    local u={r[2]*f[3],-r[1]*f[3],r[1]*f[2]-r[2]*f[1]}
    return r,u,f
end

function view.validate(spec, check, exists, compile)
    check(type(spec)=="table","modelScene requires a viewport definition")
    if type(spec)~="table" then return end
    check(type(spec.camera)=="table","modelScene requires camera")
    check(type(spec.models)=="table" and #spec.models>0,"modelScene requires models")
    local function validateVector(value,label,required)
        if value==nil and not required then return end
        check(type(value)=="table" and #value==3,"modelScene "..label.." must contain three components")
        if type(value)~="table" then return end
        for _, v in ipairs(value) do
            check(type(v)=="number" or type(v)=="string","modelScene "..label.." must use numbers or formulas")
            if type(v)=="string" then check(compile(v),"modelScene invalid "..label.." expression: "..v) end
        end
    end
    if type(spec.camera)=="table" then
        validateVector(spec.camera.position,"camera position",true)
        validateVector(spec.camera.target,"camera target",true)
        local fov=spec.camera.fov
        check(type(fov)=="number" and fov>0 and fov<180,"modelScene fov must be between 0 and 180")
    end
    for _, entity in ipairs(type(spec.models)=="table" and spec.models or {}) do
        check(type(entity)=="table","modelScene model entry must be a table")
        if type(entity)~="table" then return end
        check(type(entity.model)=="string" and exists(entity.model),"modelScene asset missing: "..tostring(entity.model))
        for _, key in ipairs({"position","scale","tint"}) do
            validateVector(entity[key],key,false)
        end
        for _, key in ipairs({"yaw","visible"}) do
            if type(entity[key])=="string" then check(compile(entity[key]),"modelScene invalid "..key.." expression") end
        end
    end
end

function view.draw(x,y,w,h,spec,env)
    assert(spec and spec.camera and spec.models,"modelScene definition missing")
    if not shader then
        -- Share the existing material/texture/dither fragment shader. Only the
        -- vertex projection differs from the item turntable.
        local source=core.buildItemShader()
        local start=assert(source:find("#ifdef VERTEX",1,true))
        local finish=assert(source:find("#endif",start,true))
        shader=love.graphics.newShader(source:sub(1,start-1)..vertex..source:sub(finish+6))
    end
    if not buffers or buffers.w~=w or buffers.h~=h then
        buffers={w=w,h=h,color=surface.newRasterCanvas(w,h),
            depth=surface.newRasterCanvas(w,h,{format="depth24stencil8"})}
        buffers.color:setFilter("nearest","nearest")
    end
    local cam=spec.camera
    local position=vector(cam.position,env,"camera position",{10,-12,12})
    local target=vector(cam.target,env,"camera target",{0,4,0})
    local right,up,forward=view.cameraBasis(position,target)
    local previous=love.graphics.getCanvas()
    love.graphics.push("all")
    love.graphics.setCanvas({buffers.color,depthstencil=buffers.depth})
    love.graphics.setScissor()
    local bg=spec.background or {0.04,0.035,0.045}
    love.graphics.clear(bg[1],bg[2],bg[3],1,0,1)
    love.graphics.setColor(1,1,1,1)
    love.graphics.setDepthMode("less",true)
    love.graphics.setMeshCullMode("none")
    love.graphics.setShader(shader)
    shader:send("cameraPosition",position)
    shader:send("cameraRight",right);shader:send("cameraUp",up);shader:send("cameraForward",forward)
    shader:send("focalLength",1/math.tan(math.rad(number(cam.fov,env,"fov",45))/2))
    shader:send("aspectRatio",w/h);shader:send("ditherLevels",32)
    shader:send("passCount",0)
    for _, entity in ipairs(spec.models) do
        local visible=true
        if entity.visible~=nil then
            local err
            visible,err=formula.eval(entity.visible,env)
            assert(not err,"3D Scene visible: "..tostring(err))
        end
        if visible and visible~=0 then
            local model=models.load(entity.model)
            shader:send("objectPosition",vector(entity.position,env,"position",{0,0,0}))
            shader:send("objectScale",vector(entity.scale,env,"scale",{1,1,1}))
            shader:send("objectYaw",number(entity.yaw,env,"yaw",0))
            local tint=vector(entity.tint,env,"tint",{1,1,1})
            for _,group in ipairs(model.groups) do
                local col=group.color or {1,1,1}
                shader:send("materialColor",{col[1]*tint[1],col[2]*tint[2],col[3]*tint[3]})
                require("presentation.mesh_material_shader").set(shader,group.passes)
                shader:send("hasTexture",group.texture and 1 or 0)
                if group.texture then group.mesh:setTexture(group.texture) end
                love.graphics.draw(group.mesh)
            end
        end
    end
    love.graphics.setShader();love.graphics.setDepthMode();love.graphics.setCanvas(previous)
    love.graphics.pop()
    love.graphics.push("all");love.graphics.setColor(1,1,1,1);love.graphics.draw(buffers.color,x,y);love.graphics.pop()
end
return view
