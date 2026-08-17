(() => {
'use strict';

const ROLE_DEFS = [
  { key:'wall', label:'WALL', color:'#b88f4c' },
  { key:'floor', label:'FLOOR', color:'#8ca46e' },
  { key:'ceiling', label:'CEILING', color:'#718ca1' },
  { key:'door', label:'DOOR', color:'#9a756f' },
  { key:'features', label:'FEATURES', color:'#9b78a7' }
];
const $ = id => document.getElementById(id);
const clone = value => JSON.parse(JSON.stringify(value));
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp = (v,a,b) => Math.max(a, Math.min(b, v));
const state = { index:[], textureFiles:[], tileset:null, baseline:null, selected:null, pendingTarget:null, atlasImage:null, atlasScale:1, dirty:false, dataSnapshot:null };

function pool(role, doc=state.tileset) {
  if (!doc) return [];
  doc.base ||= {};
  if (role === 'wall') return doc.base.walls ||= [];
  if (role === 'floor') return doc.base.floors ||= [];
  if (role === 'ceiling') return doc.base.ceilings ||= [];
  if (role === 'door') return doc.doors ||= [];
  if (role === 'features') return doc.features ||= [];
  return [];
}
function record(){ return state.selected ? pool(state.selected.role)[state.selected.index] || null : null; }
function sourceCell(rec){
  if (!rec) return null;
  if (Array.isArray(rec.atlas)) return rec.atlas.slice(0,2);
  if (Array.isArray(rec.middle)) return rec.middle.slice(0,2);
  return null;
}
function markDirty(){ state.dirty=JSON.stringify(state.tileset)!==JSON.stringify(state.baseline); $('dirty').textContent=state.dirty?'● unsaved':''; }
function titleFor(rec,role,index){ return rec?.id || `${role}_${index+1}`; }
function friendlyPlacement(rec){
  const where=rec?.where;
  if (!where || !Object.keys(where).length) return 'Anywhere';
  if (where.adjacent==='floor') return 'Beside floor';
  if (where.adjacent==='wall') return 'Beside wall';
  if (where.zone) return `Zone: ${where.zone}`;
  return 'Advanced predicate';
}
function totalWeight(role){ return pool(role).reduce((sum,rec)=>sum+Math.max(0,Number(rec.weight ?? 100)||0),0); }
function weightShare(role,rec){ const total=totalWeight(role); return total?Math.round((Math.max(0,Number(rec.weight ?? 100)||0)/total)*100):0; }
function tileThumb(rec){
  const cell=sourceCell(rec);
  if (!cell || !state.tileset?.texture) return '<div class="thumb">model / no atlas</div>';
  const tw=Number(state.tileset.tileWidth)||64, th=Number(state.tileset.tileHeight)||64;
  const x=Number(cell[0])||0, y=Number(cell[1])||0;
  return `<div class="thumb" style="background-image:url('/${esc(state.tileset.texture)}');background-position:${-x*tw}px ${-y*th}px"></div>`;
}

function renderGroups(){
  $('groups').innerHTML=ROLE_DEFS.map(def=>{
    const entries=pool(def.key);
    const cards=entries.length?entries.map((rec,index)=>{
      const selected=state.selected?.role===def.key && state.selected?.index===index;
      const share=def.key==='features'?null:weightShare(def.key,rec);
      const secondary=def.key==='features'?`${Math.round((Number(rec.injectProbability??0)||0)*100)}% · ${friendlyPlacement(rec)}`:`${Number(rec.weight??100)} weight · ${share}%`;
      return `<article class="card${selected?' selected':''}" data-role="${def.key}" data-index="${index}">${tileThumb(rec)}<div class="name">${esc(titleFor(rec,def.key,index))}</div><div class="meta"><span>${esc(secondary)}</span></div>${share===null?'':`<div class="weightbar"><i style="width:${clamp(share,0,100)}%"></i></div>`}</article>`;
    }).join(''):`<div class="hint">No ${def.label.toLowerCase()} vocabulary yet. Add one visually from the source browser.</div>`;
    return `<section class="group"><div class="group-head"><h3 style="color:${def.color}">${def.label}</h3><span class="pill">${entries.length}</span><button data-add="${def.key}">+ Add ${def.key==='features'?'feature':'variant'}</button></div><div class="cards">${cards}</div></section>`;
  }).join('');
  $('groups').querySelectorAll('.card').forEach(card=>card.addEventListener('click',()=>{ state.selected={role:card.dataset.role,index:Number(card.dataset.index)}; state.pendingTarget=null; renderAll(); }));
  $('groups').querySelectorAll('[data-add]').forEach(btn=>btn.addEventListener('click',()=>beginAdd(btn.dataset.add)));
}
function beginAdd(role){ state.selected=null; state.pendingTarget={role,index:null,field:role==='wall'?'middle':'atlas',adding:true}; renderAll(); }
function defaultId(role){ const used=new Set(pool(role).map(v=>v.id)); let n=pool(role).length+1,id; do{id=`${state.tileset.id||'tileset'}_${role}_${n++}`;}while(used.has(id)); return id; }
function addAt(role,cell){
  const rec=role==='wall'
    ? {id:defaultId(role),role:'base_wall',middle:cell,leftEdge:[cell[0],cell[1],0],rightEdge:[cell[0],cell[1],32],weight:100}
    : role==='features'
      ? {id:defaultId(role),role:'wall',atlas:cell,injectProbability:0.12}
      : {id:defaultId(role),atlas:cell,weight:100};
  const p=pool(role); p.push(rec); state.selected={role,index:p.length-1}; state.pendingTarget=null; markDirty(); renderAll();
}
function setCell(cell){
  if (!state.pendingTarget) return;
  if (state.pendingTarget.adding) return addAt(state.pendingTarget.role,cell);
  const rec=pool(state.pendingTarget.role)[state.pendingTarget.index]; if(!rec) return;
  const field=state.pendingTarget.field;
  if(field==='leftEdge'||field==='rightEdge'){ const existing=Array.isArray(rec[field])?rec[field]:[]; rec[field]=[cell[0],cell[1],Number(existing[2]??(field==='rightEdge'?32:0))]; }
  else rec[field]=cell;
  state.pendingTarget=null; markDirty(); renderAll();
}
function coordText(value){ return Array.isArray(value)?`visual ${value[0]}, ${value[1]}`:'unassigned'; }
function exactSource(rec){ if(Array.isArray(rec.atlas))return `atlas ${JSON.stringify(rec.atlas)}`; if(Array.isArray(rec.middle))return `middle ${JSON.stringify(rec.middle)}`; return rec.model?`model ${rec.model}`:'none'; }
function mutate(rec,key,value){ if(value)rec[key]=value; else delete rec[key]; changed(); }
function changed(full=true){ markDirty(); if(full)renderAll(); else{renderGroups();renderTrustView();} }

function renderInspector(){
  const host=$('inspector'), rec=record();
  if(!rec){ host.innerHTML=`<div class="inspector-empty">${state.pendingTarget?'Choose a visual source to continue.':'Select an assigned visual card.'}</div>`; return; }
  const role=state.selected.role, probability=Number(rec.injectProbability??0), light=rec.light||null, whereText=JSON.stringify(rec.where||{},null,2), isFeature=role==='features';
  host.innerHTML=`
    <label>Semantic identity</label><input id="insId" type="text" value="${esc(rec.id||'')}">
    ${role==='wall'?`<fieldset><legend>Wall structure</legend><div class="structure"><button class="struct" data-source-field="leftEdge"><strong>LEFT JOIN</strong>${coordText(rec.leftEdge)}</button><button class="struct" data-source-field="middle"><strong>MAIN FACE</strong>${coordText(rec.middle)}</button><button class="struct" data-source-field="rightEdge"><strong>RIGHT JOIN</strong>${coordText(rec.rightEdge)}</button></div><div class="subtle">Pick the visual relationship first; exact <code>middle/leftEdge/rightEdge</code> representation stays below.</div></fieldset>`:`<button id="replaceVisual">Replace visual source</button>`}
    ${!isFeature?`<fieldset><legend>Variant mix</legend><label>Weight <b id="weightValue">${Number(rec.weight??100)}</b> · <span id="weightShare">${weightShare(role,rec)}%</span> of this role</label><input id="insWeight" type="range" min="0" max="300" step="1" value="${Number(rec.weight??100)}"></fieldset>`:`<fieldset><legend>Placement</legend><label>Chance <b id="probValue">${Math.round(probability*100)}%</b></label><input id="insProbability" type="range" min="0" max="1" step="0.01" value="${probability}"><label>Rule</label><select id="placementPreset"><option value="any"${!rec.where?' selected':''}>Anywhere</option><option value="floor"${rec.where?.adjacent==='floor'?' selected':''}>Beside floor</option><option value="wall"${rec.where?.adjacent==='wall'?' selected':''}>Beside wall</option><option value="advanced"${rec.where&&!['floor','wall'].includes(rec.where.adjacent)?' selected':''}>Advanced / exact predicate</option></select></fieldset><fieldset><legend>Light / emission</legend><div class="row"><button id="warmLight">Warm emission</button><button id="clearLight">No light</button></div><div class="subtle">${light?`RGB ${esc(JSON.stringify(light.color||[]))}, radius ${esc(light.radius??'')}, falloff ${esc(light.falloff??'')}`:'No authored light.'}</div></fieldset>`}
    <details><summary>Advanced exact values</summary><label>Role</label><input id="insRole" type="text" value="${esc(rec.role||'')}"><label>Model</label><input id="insModel" type="text" value="${esc(rec.model||'')}"><label>Exact source</label><input type="text" readonly value="${esc(exactSource(rec))}">${isFeature?`<label>Exact predicate JSON</label><textarea id="whereJson">${esc(whereText)}</textarea><button id="applyWhere">Apply exact predicate</button>`:''}<label>Exact record JSON (read-only truth)</label><textarea readonly>${esc(JSON.stringify(rec,null,2))}</textarea></details><div class="row" style="margin-top:12px"><button id="deleteVariant" class="danger">Remove</button></div>`;
  host.querySelectorAll('[data-source-field]').forEach(btn=>btn.addEventListener('click',()=>{state.pendingTarget={role,index:state.selected.index,field:btn.dataset.sourceField}; renderAll();}));
  $('replaceVisual')?.addEventListener('click',()=>{state.pendingTarget={role,index:state.selected.index,field:'atlas'}; renderAll();});
  $('insId')?.addEventListener('change',e=>mutate(rec,'id',e.target.value.trim()));
  $('insRole')?.addEventListener('change',e=>mutate(rec,'role',e.target.value.trim()));
  $('insModel')?.addEventListener('change',e=>{const value=e.target.value.trim();if(value)rec.model=value;else delete rec.model;changed();});
  $('insWeight')?.addEventListener('input',e=>{rec.weight=Number(e.target.value);$('weightValue').textContent=rec.weight;$('weightShare').textContent=`${weightShare(role,rec)}%`;changed(false);});
  $('insProbability')?.addEventListener('input',e=>{rec.injectProbability=Number(e.target.value);$('probValue').textContent=`${Math.round(rec.injectProbability*100)}%`;changed(false);});
  $('placementPreset')?.addEventListener('change',e=>{if(e.target.value==='any')delete rec.where;if(e.target.value==='floor')rec.where={adjacent:'floor'};if(e.target.value==='wall')rec.where={adjacent:'wall'};changed();});
  $('warmLight')?.addEventListener('click',()=>{rec.light={color:[1,0.58,0.22],radius:Number(rec.light?.radius??4),falloff:Number(rec.light?.falloff??2)};changed();});
  $('clearLight')?.addEventListener('click',()=>{delete rec.light;changed();});
  $('applyWhere')?.addEventListener('click',()=>{try{const value=JSON.parse($('whereJson').value||'{}');if(!value||Array.isArray(value)||typeof value!=='object')throw new Error('predicate must be an object');if(Object.keys(value).length)rec.where=value;else delete rec.where;changed();}catch(error){alert(`Predicate not applied: ${error.message}`);}});
  $('deleteVariant')?.addEventListener('click',()=>{if(!confirm(`Remove ${rec.id||'this record'} from the ${role} vocabulary?`))return;pool(role).splice(state.selected.index,1);state.selected=null;changed();});
}

function renderTrustView(){
  const items=[['Wall',pool('wall')[0]],['Floor',pool('floor')[0]],['Ceiling',pool('ceiling')[0]],['Door',pool('door')[0]],['Feature',pool('features')[0]],['Variant',pool('wall')[1]||pool('floor')[1]]];
  $('previewGrid').innerHTML=items.map(([label,rec])=>`<div class="preview-cell" title="${esc(label)}">${rec?tileThumb(rec):esc(label)}</div>`).join('');
}
async function loadIndex(){
  const response=await fetch('/api/tilesets'), payload=await response.json(); if(!response.ok)throw new Error(payload.error||'Could not load Tilesets');
  state.index=payload.tilesets||[]; state.textureFiles=payload.textures||[];
  $('tilesetSelect').innerHTML=state.index.map(t=>`<option value="${esc(t.id)}">${esc(t.name||t.id)}</option>`).join('');
  if(state.index.length)await loadTileset(state.index[0].id); else $('groups').innerHTML='<div class="hint">No Tilesets exist in this Project.</div>';
  try{state.dataSnapshot=await(await fetch('/data')).json();}catch(e){state.dataSnapshot=null;}
}
async function loadTileset(id){
  const found=state.index.find(t=>t.id===id); if(!found)return;
  state.tileset=clone(found); state.baseline=clone(found); state.selected=null; state.pendingTarget=null; state.dirty=false; $('tilesetSelect').value=id; await loadAtlas(); renderAll();
}
async function maybeSwitch(id){
  if(id===state.tileset?.id)return;
  if(state.dirty){
    const save=confirm(`Save changes to ${state.tileset.id} before switching?`);
    if(save){const ok=await saveTileset();if(!ok){$('tilesetSelect').value=state.tileset.id;return;}}
    else{const discard=confirm('Discard the unsaved changes? Cancel keeps this Tileset open.');if(!discard){$('tilesetSelect').value=state.tileset.id;return;}}
  }
  await loadTileset(id);
}
async function saveTileset(){
  if(!state.tileset)return false;
  try{
    const response=await fetch('/api/tilesets/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(state.tileset)}),payload=await response.json();
    if(!response.ok||!payload.success)throw new Error(payload.message||'Save failed');
    const refreshed=await fetch('/api/tilesets').then(r=>r.json()); state.index=refreshed.tilesets||state.index;
    const saved=state.index.find(t=>t.id===state.tileset.id); if(saved){state.tileset=clone(saved);state.baseline=clone(saved);}else state.baseline=clone(state.tileset);
    markDirty();renderAll();return true;
  }catch(error){alert(`Tileset was not saved: ${error.message}`);return false;}
}
function discard(){ if(!state.dirty)return;if(!confirm('Discard every unsaved change in this Tileset?'))return;state.tileset=clone(state.baseline);state.selected=null;state.pendingTarget=null;markDirty();loadAtlas();renderAll(); }
async function loadAtlas(){
  const canvas=$('atlas'),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);const path=state.tileset?.texture;if(!path){$('atlasStatus').textContent='This Tileset has no atlas texture.';return;}
  const img=new Image();img.onload=()=>{state.atlasImage=img;const maxWidth=Math.max(320,$('atlas').parentElement.clientWidth-2);state.atlasScale=Math.min(1,maxWidth/img.naturalWidth);canvas.width=Math.max(1,Math.round(img.naturalWidth*state.atlasScale));canvas.height=Math.max(1,Math.round(img.naturalHeight*state.atlasScale));drawAtlas();};img.onerror=()=>{$('atlasStatus').textContent=`Could not load ${path}`;};img.src=`/${path}`;
}
function drawAtlas(){
  const canvas=$('atlas'),ctx=canvas.getContext('2d'),img=state.atlasImage;if(!img||!state.tileset)return;const s=state.atlasScale,tw=(Number(state.tileset.tileWidth)||64)*s,th=(Number(state.tileset.tileHeight)||64)*s;ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);ctx.strokeStyle='rgba(255,220,145,.36)';ctx.lineWidth=1;for(let x=0;x<=canvas.width;x+=tw){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,canvas.height);ctx.stroke()}for(let y=0;y<=canvas.height;y+=th){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(canvas.width,y);ctx.stroke()}$('atlasStatus').textContent=`${state.tileset.tileWidth||64}×${state.tileset.tileHeight||64} visual cells · source: ${state.tileset.texture}`;
}
function renderSources(){
  const active=(state.tileset?.texture||'').replace(/^assets\/tilesets\//,'');
  $('sourceList').innerHTML=state.textureFiles.map(file=>{const path=`assets/tilesets/${file}`,selected=file===active;return `<div class="source${selected?' active':''}" data-source="${esc(path)}"><img src="/${esc(path)}"><small>${esc(file)}</small><small>${selected?'active atlas':'available PNG source'}</small></div>`;}).join('');
  $('sourceList').querySelectorAll('.source').forEach(el=>el.addEventListener('click',()=>{const path=el.dataset.source;if(path!==state.tileset.texture){alert('The current persisted Tileset record has one texture source. This experiment shows standalone PNGs beside atlas regions, but will not fake per-variant source ownership that the runtime record cannot save.');return;}loadAtlas();}));
}
function renderAll(){ markDirty();renderSources();renderGroups();renderInspector();renderTrustView();$('targetBanner').textContent=state.pendingTarget?(state.pendingTarget.adding?`Click a visual tile to add ${state.pendingTarget.role}.`:`Click a visual tile to replace ${state.pendingTarget.field}.`):''; }
function atlasClick(event){
  if(!state.tileset||!state.atlasImage)return;if(!state.pendingTarget){$('targetBanner').textContent='Select an assigned card and choose Replace, or use Add Variant, before picking a tile.';return;}
  const rect=$('atlas').getBoundingClientRect(),tw=(Number(state.tileset.tileWidth)||64)*state.atlasScale,th=(Number(state.tileset.tileHeight)||64)*state.atlasScale;setCell([Math.max(0,Math.floor((event.clientX-rect.left)/tw)),Math.max(0,Math.floor((event.clientY-rect.top)/th))]);
}
function findMapUsingTileset(){
  const data=state.dataSnapshot;if(!data)return null;const target=state.tileset?.id,candidates=[];
  const visit=value=>{if(!value||typeof value!=='object')return;if(!Array.isArray(value)&&value.id&&(value.tileset===target||value.tilesetId===target||value.tileset_id===target))candidates.push(value);Object.entries(value).forEach(([k,v])=>{if(k!=='_fileVersions')visit(v);});};visit(data.maps||data.map||data);return candidates[0]||null;
}
async function runtimeInspect(){
  const out=$('runtimeStatus');if(state.dirty){out.className='status runtime-bad';out.textContent='Save first. Runtime inspection reflects authoritative saved Project data, not a browser-only shadow model.';return;}
  const map=findMapUsingTileset();if(!map){out.className='status runtime-bad';out.textContent=`No loaded Project Map advertises Tileset '${state.tileset?.id}' in a recognizable field. The workbench will not synthesize a speculative #694 Map shape.`;return;}
  out.className='status';out.textContent=`Asking LÖVE to inspect real Map ${map.id} with deterministic seed 547…`;
  try{const response=await fetch('/api/map-inspection',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({map,seed:547})}),payload=await response.json();if(!response.ok||payload.error)throw new Error(payload.error||`HTTP ${response.status}`);out.className='status runtime-ok';out.textContent=JSON.stringify({map:map.id,tileset:state.tileset.id,seed:547,runtimeInspection:payload},null,2);}catch(error){out.className='status runtime-bad';out.textContent=`Runtime inspection unavailable: ${error.message}`;}
}

$('atlas').addEventListener('click',atlasClick);
$('tilesetSelect').addEventListener('change',e=>maybeSwitch(e.target.value).catch(err=>alert(err.message)));
$('saveBtn').addEventListener('click',()=>saveTileset());
$('discardBtn').addEventListener('click',discard);
$('runtimeBtn').addEventListener('click',runtimeInspect);
window.addEventListener('beforeunload',event=>{if(!state.dirty)return;event.preventDefault();event.returnValue='';});
loadIndex().catch(error=>{$('groups').innerHTML=`<div class="hint">Workbench could not start: ${esc(error.message)}</div>`;console.error(error);});
})();
