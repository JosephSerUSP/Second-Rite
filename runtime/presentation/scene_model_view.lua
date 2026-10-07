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
uniform float bakedLighting;
uniform vec4 frameWindow;
vec4 position(mat4 transform_projection, vec4 vertex_position) {
    float c=cos(objectYaw), s=sin(objectYaw);
    vec3 p=VertexPosition.xyz*objectScale;
    p=vec3(p.x*c-p.y*s,p.x*s+p.y*c,p.z)+objectPosition;
    vec3 n=VertexNormal/objectScale;
    n=normalize(vec3(n.x*c-n.y*s,n.x*s+n.y*c,n.z));
    float light=0.55+0.45*max(0.0,dot(n,normalize(vec3(-0.4,-0.6,1.0))));
    // A baked appearance consumes its authored illumination (viewport_3d's
    // bakedLighting contract): draw the atlas as baked, never relit.
    light=mix(light,1.0,bakedLighting);
    worldColor=vec4(VertexColor.rgb*materialColor*light,VertexColor.a);
    vec3 d=p-cameraPosition;
    float depth=dot(d,cameraForward);
    float clipZ=1.002002*depth-0.2002002;
    worldUV=VertexTexCoord.xy; affineScale=1.0;
    sheenUV=vec2(n.x*.5+.5,.5-n.z*.5);
    // frameWindow maps the camera's whole pre-rendered-style plate to the
    // visible window: scale (xy) and shift (zw), in clip units.
    return vec4((dot(d,cameraRight)*focalLength/aspectRatio)*frameWindow.x+frameWindow.z*depth,
        (-dot(d,cameraUp)*focalLength)*frameWindow.y+frameWindow.w*depth,clipZ,depth);
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

local function dot(a,b) return a[1]*b[1]+a[2]*b[2]+a[3]*b[3] end

-- A camera may own a plate larger than the window, the way the original's
-- pre-rendered backgrounds (and Second Gate's town plates) are larger than
-- the screen. The camera never moves; the WINDOW slides across its plate to
-- follow a point and stops at the plate's edges. frame.size is the plate in
-- windows ([1,1] = no plate); fov describes the whole plate.
--
-- Returns {kx,ky,sx,sy}: plate-to-window scale and shift in clip units.
function view.frameWindow(cam,w,h,follow)
    local size=cam.frame and cam.frame.size or {1,1}
    local kx,ky=math.max(1,size[1] or 1),math.max(1,size[2] or 1)
    local cx,cy=0,0
    if follow and (kx>1 or ky>1) then
        local r,u,f=view.cameraBasis(cam.position,cam.target)
        local d={follow[1]-cam.position[1],follow[2]-cam.position[2],follow[3]-cam.position[3]}
        local depth=dot(d,f)
        if depth>.1 then
            local focal=1/math.tan(math.rad(cam.fov)/2)
            cx=dot(d,r)*focal/((w/h)*kx/ky)/depth
            cy=-dot(d,u)*focal/depth
        end
    end
    local function window(c,k,pixels)
        local edge=1-1/k
        c=math.max(-edge,math.min(edge,c))
        -- whole pixels, as a scrolled plate would be, so nothing shimmers
        local shift=-c*k
        return math.floor(shift*pixels/2+.5)/(pixels/2)
    end
    return {kx,ky,window(cx,kx,w),window(cy,ky,h)}
end

-- One CPU projection helper for world-anchored labels and inspection tools.
function view.projectPoint(point,cam,w,h,frame)
    frame=frame or {1,1,0,0}
    local r,u,f=view.cameraBasis(cam.position,cam.target)
    local d={point[1]-cam.position[1],point[2]-cam.position[2],point[3]-cam.position[3]}
    local depth=dot(d,f)
    if depth<=.1 then return nil end
    local focal=1/math.tan(math.rad(cam.fov)/2)
    local aspect=(w/h)*frame[1]/frame[2]
    local nx=dot(d,r)*focal/aspect/depth*frame[1]+frame[3]
    local ny=-dot(d,u)*focal/depth*frame[2]+frame[4]
    return w/2+nx*w/2,h/2+ny*h/2
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
        local frame=spec.camera.frame
        if frame~=nil then
            check(type(frame)=="table","modelScene camera frame must be a table")
            local size=type(frame)=="table" and frame.size
            check(type(size)=="table" and type(size[1])=="number" and type(size[2])=="number"
                and size[1]>=1 and size[2]>=1,"modelScene camera frame.size must be two numbers >= 1")
            if type(frame)=="table" then validateVector(frame.follow,"camera frame follow",false) end
        end
    end
    for _, entity in ipairs(type(spec.models)=="table" and spec.models or {}) do
        check(type(entity)=="table","modelScene model entry must be a table")
        if type(entity)~="table" then return end
        check(type(entity.model)=="string" and exists(entity.model),"modelScene asset missing: "..tostring(entity.model))
        for _, key in ipairs({"position","scale","tint"}) do
            validateVector(entity[key],key,false)
        end
        check(entity.bakedLighting==nil or type(entity.bakedLighting)=="boolean","modelScene bakedLighting must be a boolean")
        for _, key in ipairs({"yaw","visible"}) do
            if type(entity[key])=="string" then check(compile(entity[key]),"modelScene invalid "..key.." expression") end
        end
    end
    if spec.labels ~= nil then check(type(spec.labels)=="table","modelScene labels must be a list") end
    for _, label in ipairs(type(spec.labels)=="table" and spec.labels or {}) do
        check(type(label)=="table","modelScene label must be a table")
        if type(label)~="table" then return end
        validateVector(label.position,"label position",true)
        check(type(label.value)=="string" and compile(label.value),"modelScene label requires a value expression")
        if label.visible then check(compile(label.visible),"modelScene invalid label visibility") end
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
    local fov=number(cam.fov,env,"fov",45)
    local resolved={position=position,target=target,fov=fov,frame=cam.frame}
    local frame=view.frameWindow(resolved,w,h,
        cam.frame and cam.frame.follow and vector(cam.frame.follow,env,"camera frame follow",{0,0,0}))
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
    shader:send("focalLength",1/math.tan(math.rad(fov)/2))
    shader:send("aspectRatio",(w/h)*frame[1]/frame[2]);shader:send("frameWindow",frame)
    shader:send("ditherLevels",32)
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
            shader:send("bakedLighting",entity.bakedLighting==true and 1 or 0)
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
    love.graphics.setShader();love.graphics.setDepthMode()
    for _, label in ipairs(spec.labels or {}) do
        local visible,err=true,nil
        if label.visible then visible,err=formula.eval(label.visible,env) end
        assert(not err,"3D Scene label visibility: "..tostring(err))
        if visible then
            local lx,ly=view.projectPoint(vector(label.position,env,"label position",{0,0,0}),
                resolved,w,h,frame)
            local value,valueErr=formula.eval(label.value,env)
            assert(not valueErr,"3D Scene label value: "..tostring(valueErr))
            if lx then
                local ui=require("presentation.ui")
                local text=tostring(value)
                local tx=lx-ui.measureText(text)/2
                ui.drawString(text,tx+1,ly+1,{0,0,0,1})
                ui.drawString(text,tx,ly,label.color or {1,1,1,1})
            end
        end
    end
    love.graphics.setCanvas(previous)
    love.graphics.pop()
    love.graphics.push("all");love.graphics.setColor(1,1,1,1);love.graphics.draw(buffers.color,x,y);love.graphics.pop()
end
return view
