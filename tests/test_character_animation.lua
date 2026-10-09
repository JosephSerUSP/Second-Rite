local animation=require("presentation.character_animation")
local passed=0
local function check(v,label) assert(v,label); passed=passed+1 end
local function near(a,b) return math.abs(a-b)<1e-5 end
local identity={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1}
local asset={kind="hichaukitoden-character",version=1,
    source={up="y",forward="+z"},
    nodes={{translation={0,0,0},rotation={0,0,0,1},scale={1,1,1}},
        {parent=1,translation={0,0,0},rotation={0,0,0,1},scale={1,1,1}}},
    joints={1,2},inverseBind={identity,identity},
    primitives={{texture="texture.png",color={1,1,1,1},indices={1,2,3},vertices={
        {1,0,0,0,0,0,0,1,1,2,1,1,.5,.5,0,0},
        {0,1,0,1,0,0,0,1,1,2,1,1,1,0,0,0},
        {0,0,1,0,1,0,0,1,1,2,1,1,1,0,0,0}}}},
    clips={idle={duration=1,channels={}},walk={duration=1,channels={
        {node=2,path="rotation",interpolation="LINEAR",times={0,1},values={{0,0,0,1},{0,0,1,0}}}}}}}
local prepared=animation.prepare(asset)
local pose={x=10,y=20,z=3,facingX=0,facingY=-1}
local a=animation.sample(prepared,"idle",0,pose,1)[1].vertices[1]
local b=animation.sample(prepared,"walk",.5,pose,1)[1].vertices[1]
check(near(a[1],10.5) and near(a[2],20.5) and near(a[3],3),"bind pose and Z-up grounding")
check(near(b[1],10) and near(b[2],20.5) and near(b[3],3.5),"slerp and two-joint blending")
local endPose=animation.sample(prepared,"walk",1,pose,1,"once")[1].vertices[1]
local held=animation.sample(prepared,"walk",5,pose,1,"once")[1].vertices[1]
check(near(endPose[1],held[1]) and near(endPose[3],held[3]),"one-shot clamps beyond end without looping")
check(not near(endPose[1],a[1]),"one-shot endpoint differs from start")
local loop=animation.sample(prepared,"walk",1.5,pose,1)[1].vertices[1]
check(near(loop[1],b[1]) and near(loop[3],b[3]),"clip loops by duration")
check(asset.primitives[1].vertices[1][1]==1 and pose.x==10,"posing never mutates asset or gameplay")
pose.facingX,pose.facingY=1,0
local right=animation.sample(prepared,"idle",0,pose,1)[1].vertices[1]
check(near(right[1],9.5) and near(right[2],20.5),"heading rotates actual geometry")
local ok=pcall(animation.sample,prepared,"missing",0,pose,1)
check(not ok,"unknown clip fails loud")
asset.nodes[1].parent=2
check(not pcall(animation.prepare,asset),"hierarchy cycle fails")
asset.nodes[1].parent=nil
asset.primitives[1].vertices[1][13]=.2
check(not pcall(animation.prepare,asset),"bad weights fail")
asset.primitives[1].vertices[1][13]=.5
asset.clips.walk.channels[1].interpolation="CUBICSPLINE"
check(not pcall(animation.prepare,asset),"unsupported interpolation fails")
asset.clips.walk.channels[1].interpolation="LINEAR"
asset.primitives[1].indices[1]=0
check(not pcall(animation.prepare,asset),"bad indices fail")
asset.primitives[1].indices[1]=1
asset.nodes[2].scale={1,2,1}
check(not pcall(animation.prepare,asset),"nonuniform joint scale fails")
asset.nodes[2].scale={1,1,1}
asset.primitives[1].vertices[1][8]=0
check(not pcall(animation.prepare,asset),"empty source normal fails before rendering")
asset.primitives[1].vertices[1][8]=1
asset.clips.walk.channels[1].values[2]={0,0,0,-1}
local shortest=animation.sample(animation.prepare(asset),"walk",.5,pose,1)[1].vertices[1]
check(near(shortest[1],right[1]),"antipodal quaternions follow shortest path")
print("CHARACTER ANIMATION TESTS OK "..passed)
return true
