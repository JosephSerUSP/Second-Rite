-- Actual adopted assets through the public Event presentation/actor owners.
return function(game)
    local view=require("presentation.viewport_3d")
    local animation=require("presentation.animated_actor")
    local owner=require("engine.event_actor")
    local json=require("engine.data.json")
    local bundle=require("presentation.map_renderable_bundle")
    local event
    for _,candidate in ipairs(game.currentMapData.events) do
        if candidate.actorAppearance then event=candidate;break end
    end
    assert(event,"room needs an authored compiled Event")
    local original=json.encode(event)
    local before=game.eventActorRuntime and json.encode(game.eventActorRuntime)
    local presentation=view.resolveEventPresentation(event,game)
    local idle=animation.resolveEvent(game,event,presentation,1.25)
    assert(idle.clip=="idle" and idle.pose.facingX==-1 and idle.pose.facingY==0)
    assert(idle.pose.x==event.worldPosition[1] and idle.pose.y==event.worldPosition[2] and idle.pose.z==event.worldPosition[3])
    assert(json.encode(event)==original and (game.eventActorRuntime and json.encode(game.eventActorRuntime))==before,
        "posing allocated or mutated gameplay state")
    assert(json.encode(idle.groups)~=json.encode(animation.resolveEvent(game,event,presentation,2.75).groups),"Event idle is static")
    local found=0
    for _,surface in ipairs(bundle.collect(game,"authoring",{includeActor=true}).surfaces) do
        if surface.source.kind=="event" and surface.source.surface=="character" then
            found=found+1
            assert(surface.source.id==event.id and #surface.positions==(event.id==101 and 677 or 684)*9)
            assert(surface.source.rootPosition[1]==event.worldPosition[1])
        end
    end
    assert(found==1,"collector lost or duplicated Event character")
    owner.setMotion(game,event,1,0)
    local walk=animation.resolveEvent(game,event,presentation,1.25)
    assert(walk.clip=="walk" and walk.pose.facingX==1 and walk.pose.facingY==0)
    assert(walk.pose.x==idle.pose.x and walk.pose.y==idle.pose.y,"animation moved gameplay root")
    owner.holdPose(game,event,"walk")
    assert(json.encode(animation.resolveEvent(game,event,presentation,1).groups)
        ==json.encode(animation.resolveEvent(game,event,presentation,2).groups),"held pose advanced")
    owner.holdPose(game,event,"missing")
    assert(not pcall(animation.resolveEvent,game,event,presentation,1),"missing semantic clip silently ignored")
    owner.playOneShot(game,event,"walk",1)
    assert(not pcall(animation.resolveEvent,game,event,presentation,1),"unsupported one-shot silently looped")
    owner.reset(game)
    local spec=event.actorAppearance
    local previousPages=event.pages
    event.pages={{actorAppearance=false}}
    assert(view.resolveEventPresentation(event,game).visual==nil,"page suppression ignored")
    event.pages={{actorAppearance=spec,facing="N"}}
    local page=animation.resolveEvent(game,event,view.resolveEventPresentation(event,game),1)
    assert(page.pose.facingY==-1,"authored page facing ignored")
    event.pages=previousPages
    local previousId=event.scriptId
    local common=game.loader.commonEvents
    local previousCommon=common.character_proof
    common.character_proof={actorAppearance=spec}
    event.actorAppearance=nil;event.scriptId="character_proof"
    assert(view.resolveEventPresentation(event,game).visual=="character","Common Event appearance not inherited")
    event.actorAppearance=false
    assert(view.resolveEventPresentation(event,game).visual==nil,"explicit suppression did not beat Common Event")
    event.actorAppearance=spec;event.scriptId=previousId;common.character_proof=previousCommon
    assert(json.encode(event)==original,"proof did not restore authored Event")
    print("EVENT CHARACTER PROOF OK map "..game.currentMapData.id)
end
