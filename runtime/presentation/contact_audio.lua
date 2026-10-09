-- At-most-once audio projection of published contact facts. Never called by draw.
local audio = {}
local seen=setmetatable({}, {__mode="k"})
local sources={}
function audio.present(fact)
    if not fact or seen[fact] then return false end
    seen[fact]=true
    if not fact.sound then return false end
    assert(type(fact.sound)=="string" and fact.sound:match("^assets/") and not fact.sound:find("..",1,true),"invalid contact sound")
    local source=sources[fact.sound]
    if not source then source=love.audio.newSource(fact.sound,"static");sources[fact.sound]=source end
    source:stop();source:play()
    return true
end
return audio
