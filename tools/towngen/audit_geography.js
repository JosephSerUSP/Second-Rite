#!/usr/bin/env node
'use strict';
// Extract authored possibilities; this is not a reachability or physical-datum solver.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
function audit(project=path.join(root,'projects/hichaukitoden-game')) {
 const data=path.join(project,'data');
 const index=JSON.parse(fs.readFileSync(path.join(data,'maps/index.json')));
 const maps=new Map(index.files.map(file=>{const map=JSON.parse(fs.readFileSync(path.join(data,'maps',file)));return [map.id,map];}));
 const common=JSON.parse(fs.readFileSync(path.join(data,'commonEvents.json')));
 const edges=[];
 function anchors(map) {
  const file=map?.traversal?.environmentPackage;
  return file?JSON.parse(fs.readFileSync(path.join(project,file))).anchors??{}:{};
 }
 function walk(value,from,event,location,stack=[]) {
  if(!value || typeof value!=='object')return;
  if(Array.isArray(value)){value.forEach((item,i)=>walk(item,from,event,`${location}/${i}`,stack));return;}
  if(value.cmd==='LOAD_MAP') {
   const target=maps.get(value.mapId);
   const door=target?.traversal?.doorways?.find(door=>door.anchor===value.arrival);
   const arrivalEvent=target?.events?.find(item=>item.instanceId===door?.eventInstanceId);
   const arrivalName=value.arrival??target?.traversal?.spawnAnchor;
   const anchor=anchors(target)[arrivalName];
   edges.push({from,event:event?.instanceId??event?.id??null,position:event?.worldPosition??null,
    to:value.mapId,arrival:value.arrival??null,arrivalPosition:anchor?.position??null,arrivalEventPosition:arrivalEvent?.worldPosition??null,
    arrivalKind:door?'doorway':anchor&&arrivalName===target?.traversal?.spawnAnchor?'spawn':'unresolved-or-grid-default',location});
  }
  if(value.cmd==='CALL_COMMON_EVENT') {
   const id=value.commonEventId??value.id;
   if(stack.includes(id))throw new Error(`Recursive common event at ${location}`);
   if(!common[id])throw new Error(`Unresolved common event ${id} at ${location}`);
   walk(common[id],from,event,`${location}/common:${id}`,[...stack,id]);
  }
  for(const [key,item] of Object.entries(value))if(key!=='cmd')walk(item,from,event,`${location}/${key}`,stack);
 }
 const town=[...maps.values()].filter(map=>map.category==='town'&&map.id>=16&&map.id!==30);
 for(const map of town)for(const event of map.events??[])walk(event.commands,map.id,event,`map:${map.id}/event:${event.id}`);
 return {semantics:'Authored possible transfers, including nested command lists. Conditions are not evaluated. Profiles are local datums; no global height is inferred.',
  maps:town.map(map=>({id:map.id,title:map.title,lane:map.traversal?.lane??null,spawnAnchor:map.traversal?.spawnAnchor??null,environmentAnchors:anchors(map),doorways:map.traversal?.doorways??[]})),edges};
}
if(require.main===module){const args=process.argv.slice(2),output=args.includes('--output')?args[args.indexOf('--output')+1]:null;const result=JSON.stringify(audit(),null,2)+'\n';if(output){fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,result);}else process.stdout.write(result);}
module.exports={audit};
