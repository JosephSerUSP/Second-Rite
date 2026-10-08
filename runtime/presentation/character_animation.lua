-- Pure CPU posing of compiled deform skins. Studio receives this module's
-- resolved geometry; neither the browser nor traversal reimplements skinning.
local animation = {}
local instance = require("engine.geometry.model_instance")
local function finite(x)
    return type(x) == "number" and x == x and math.abs(x) < math.huge
end
local function array(a, count)
    assert(type(a) == "table" and #a == count, "character attribute length mismatch")
    for _, x in ipairs(a) do assert(finite(x), "character attribute must be finite") end
end
local function index(i, count)
    assert(finite(i) and i == math.floor(i) and i >= 1 and i <= count, "character index out of range")
end
function animation.validate(asset)
    assert(asset.kind == "thestra-character" and asset.version == 1, "unsupported character contract")
    assert(asset.source and asset.source.up=="y" and asset.source.forward=="+z", "unsupported deform source basis")
    assert(type(asset.nodes) == "table" and #asset.nodes > 0, "character nodes missing")
    local visited, active = {}, {}
    local function visit(i)
        if visited[i] then return end
        assert(not active[i], "character hierarchy cycle")
        active[i] = true
        local n = asset.nodes[i]
        array(n.translation, 3); array(n.rotation, 4); array(n.scale, 3)
        assert(n.scale[1] > 0 and math.abs(n.scale[1]-n.scale[2]) < 1e-5
            and math.abs(n.scale[1]-n.scale[3]) < 1e-5, "character scale must be positive uniform")
        local q = n.rotation
        assert(math.abs(q[1]^2+q[2]^2+q[3]^2+q[4]^2-1) < .001, "character quaternion must be unit")
        if n.parent then index(n.parent, #asset.nodes); visit(n.parent) end
        active[i], visited[i] = nil, true
    end
    for i=1,#asset.nodes do visit(i) end
    assert(#asset.joints > 0 and #asset.joints == #asset.inverseBind, "character bind matrices missing")
    for j,n in ipairs(asset.joints) do index(n,#asset.nodes); array(asset.inverseBind[j],16) end
    assert(#asset.primitives > 0, "character geometry missing")
    for _, p in ipairs(asset.primitives) do
        assert(type(p.texture) == "string" and p.texture ~= "", "character texture missing")
        array(p.color,4)
        assert(#p.vertices > 0 and #p.indices > 0 and #p.indices % 3 == 0, "character triangles missing")
        for _, v in ipairs(p.vertices) do
            array(v,16)
            assert(v[6]^2+v[7]^2+v[8]^2>1e-12,"character vertex normal is empty")
            local weight = 0
            for k=9,12 do
                index(v[k], #asset.joints)
                assert(v[k+4] >= 0, "negative character weight")
                weight = weight + v[k+4]
            end
            assert(math.abs(weight-1)<.001, "character weights must sum to one")
        end
        for _, i in ipairs(p.indices) do index(i,#p.vertices) end
    end
    assert(type(asset.clips)=="table" and next(asset.clips), "deform skin requires clips")
    for _, clip in pairs(asset.clips) do
        assert(finite(clip.duration) and clip.duration > 0, "character clip duration invalid")
        local targets = {}
        for _, c in ipairs(clip.channels) do
            index(c.node,#asset.nodes)
            local width = c.path == "rotation" and 4 or 3
            assert(c.path == "rotation" or c.path == "translation" or c.path == "scale", "unknown character track")
            assert(c.interpolation == "LINEAR" or c.interpolation == "STEP", "unsupported character interpolation")
            local key = c.node .. ":" .. c.path
            assert(not targets[key], "duplicate character track"); targets[key]=true
            assert(#c.times > 0 and #c.times == #c.values and c.times[1] == 0, "character keys invalid")
            local previous = -1
            for i,t in ipairs(c.times) do
                assert(finite(t) and t > previous and t <= clip.duration, "character key times invalid")
                previous=t; array(c.values[i],width)
                if c.path == "rotation" then
                    local q=c.values[i]
                    assert(math.abs(q[1]^2+q[2]^2+q[3]^2+q[4]^2-1)<.001,"character key quaternion must be unit")
                elseif c.path == "scale" then
                    local s=c.values[i]
                    assert(s[1]>0 and math.abs(s[1]-s[2])<1e-5 and math.abs(s[1]-s[3])<1e-5,
                        "character animated scale must be positive uniform")
                end
            end
        end
    end
    return asset
end

-- Column-major glTF matrices; hierarchy and inverse binds stay in their source
-- basis until skinning is complete. Convert to runtime Z-up exactly once.
local function multiply(a,b)
    local out={}
    for c=0,3 do for r=1,4 do
        local v=0
        for k=0,3 do v=v+a[k*4+r]*b[c*4+k+1] end
        out[c*4+r]=v
    end end
    return out
end
local function trs(t,q,s)
    local x,y,z,w=q[1],q[2],q[3],q[4]
    return {
        (1-2*y*y-2*z*z)*s[1],(2*x*y+2*z*w)*s[1],(2*x*z-2*y*w)*s[1],0,
        (2*x*y-2*z*w)*s[2],(1-2*x*x-2*z*z)*s[2],(2*y*z+2*x*w)*s[2],0,
        (2*x*z+2*y*w)*s[3],(2*y*z-2*x*w)*s[3],(1-2*x*x-2*y*y)*s[3],0,
        t[1],t[2],t[3],1,
    }
end
local function interpolate(c,time)
    local times,values=c.times,c.values
    local lo,hi=1,#times
    while lo<hi do
        local mid=math.ceil((lo+hi)/2)
        if times[mid]<=time then lo=mid else hi=mid-1 end
    end
    local a=values[lo]
    if lo==#times or c.interpolation=="STEP" then return a end
    local b=values[lo+1]
    local f=(time-times[lo])/(times[lo+1]-times[lo])
    local out={}
    if c.path=="rotation" then
        local dot=0
        for k=1,4 do dot=dot+a[k]*b[k] end
        local sign=dot<0 and -1 or 1
        dot=math.min(1,math.abs(dot))
        local wa,wb=1-f,f
        if dot<.9995 then
            local angle=math.acos(dot)
            wa,wb=math.sin((1-f)*angle)/math.sin(angle),math.sin(f*angle)/math.sin(angle)
        end
        local length=0
        for k=1,4 do out[k]=a[k]*wa+b[k]*wb*sign; length=length+out[k]^2 end
        for k=1,4 do out[k]=out[k]/math.sqrt(length) end
    else
        for k=1,3 do out[k]=a[k]+(b[k]-a[k])*f end
    end
    return out
end
local function palettes(asset,clipName,time)
    local overrides={}
    if clipName then
        local clip=assert(asset.clips[clipName],"unknown character clip: "..tostring(clipName))
        assert(finite(time),"character sample time must be finite")
        time=time%clip.duration
        for _,c in ipairs(clip.channels) do
            overrides[c.node]=overrides[c.node] or {}
            overrides[c.node][c.path]=interpolate(c,time)
        end
    end
    local globals={}
    local function global(i)
        if globals[i] then return globals[i] end
        local n,o=asset.nodes[i],overrides[i] or {}
        local m=trs(o.translation or n.translation,o.rotation or n.rotation,o.scale or n.scale)
        if n.parent then m=multiply(global(n.parent),m) end
        globals[i]=m; return m
    end
    local result={}
    for j,n in ipairs(asset.joints) do result[j]=multiply(global(n),asset.inverseBind[j]) end
    return result
end
local function skin(vertex,matrices)
    local x,y,z,nx,ny,nz=0,0,0,0,0,0
    for k=9,12 do
        local m,w=matrices[vertex[k]],vertex[k+4]
        if w>0 then
            x=x+w*(m[1]*vertex[1]+m[5]*vertex[2]+m[9]*vertex[3]+m[13])
            y=y+w*(m[2]*vertex[1]+m[6]*vertex[2]+m[10]*vertex[3]+m[14])
            z=z+w*(m[3]*vertex[1]+m[7]*vertex[2]+m[11]*vertex[3]+m[15])
            -- Node scales are uniform and positive. Divide by squared scale
            -- to apply the inverse transpose rather than scaling the normal.
            local scale2=m[1]^2+m[2]^2+m[3]^2
            assert(scale2>1e-12,"singular character joint")
            nx=nx+w*(m[1]*vertex[6]+m[5]*vertex[7]+m[9]*vertex[8])/scale2
            ny=ny+w*(m[2]*vertex[6]+m[6]*vertex[7]+m[10]*vertex[8])/scale2
            nz=nz+w*(m[3]*vertex[6]+m[7]*vertex[7]+m[11]*vertex[8])/scale2
        end
    end
    return {x,y,z,vertex[4],vertex[5],nx,ny,nz}
end
function animation.prepare(asset)
    animation.validate(asset)
    local matrices=palettes(asset)
    local minX,minY,minZ,maxX,maxY,maxZ=math.huge,math.huge,math.huge,-math.huge,-math.huge,-math.huge
    for _,p in ipairs(asset.primitives) do for _,v in ipairs(p.vertices) do
        local s=skin(v,matrices)
        minX,minY,minZ=math.min(minX,s[1]),math.min(minY,s[2]),math.min(minZ,s[3])
        maxX,maxY,maxZ=math.max(maxX,s[1]),math.max(maxY,s[2]),math.max(maxZ,s[3])
    end end
    assert(maxY-minY>1e-6,"character height is empty")
    return {asset=asset,root={(minX+maxX)/2,minY,(minZ+maxZ)/2},height=maxY-minY}
end
function animation.sample(prepared,clipName,time,pose,height)
    array({pose.x,pose.y,pose.z},3)
    assert(finite(height) and height>0,"character world height must be positive")
    local matrices=palettes(prepared.asset,clipName,time)
    local fx,fy=pose.facingX or 0,pose.facingY or 1
    local length=math.sqrt(fx*fx+fy*fy)
    assert(length>0 and finite(length),"character facing must be nonzero")
    -- Source front is Blender -Y / glTF +Z. Basis is (x,-z,y).
    local cosine,sine=-fy/length,fx/length
    local placement=instance.new("traversal-actor", "character", {
        translation={pose.x,pose.y,pose.z},
        orientation={cosine,-sine,0,sine,cosine,0,0,0,1},
        scale=height/prepared.height,
    }, prepared.asset.source, false)
    local groups={}
    for _,p in ipairs(prepared.asset.primitives) do
        local unique={}
        for i,v in ipairs(p.vertices) do
            local s=skin(v,matrices)
            local x,y,z=instance.position(placement,
                s[1]-prepared.root[1],-(s[3]-prepared.root[3]),s[2]-prepared.root[2])
            local nx,ny,nz=s[6],-s[8],s[7]
            local normalLength=math.sqrt(nx*nx+ny*ny+nz*nz)
            assert(normalLength>1e-9,"character normal is empty")
            nx,ny,nz=instance.direction(placement,nx/normalLength,ny/normalLength,nz/normalLength)
            unique[i]={x,y,z,s[4],s[5],nx,ny,nz,
                p.color[1],p.color[2],p.color[3],p.color[4]}
        end
        local vertices={}
        for _,i in ipairs(p.indices) do vertices[#vertices+1]=unique[i] end
        groups[#groups+1]={vertices=vertices,texture=p.texture,color=p.color,material=p.material}
    end
    return groups
end
return animation
