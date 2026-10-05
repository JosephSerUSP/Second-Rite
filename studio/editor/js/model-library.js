(function(root) {
    'use strict';

    let modal, form, list, status, summary, canvas, saveButton, preview;
    let records = {}, version, draft, originalId = null, review = null;
    let dirty = false, prepared = false, generation = 0, busy = false;
    const clone = value => JSON.parse(JSON.stringify(value));

    async function api(action, value) {
        const response = await fetch('/api/model-library' + (action ? '/' + action : ''), action
            ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) }
            : { cache: 'no-store' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Model Library request failed');
        return result;
    }
    function button(label, action, parent) {
        const el = document.createElement('button');
        el.className = 'win98-btn'; el.textContent = label;
        el.onclick = action; parent.appendChild(el); return el;
    }
    function message(value) { status.textContent = value; }
    function setBusy(value) {
        busy=value;
        form.inert=value;
        modal.querySelectorAll('button').forEach(el => {
            if(value) { el.dataset.wasDisabled=el.disabled?'1':'0'; el.disabled=true; }
            else if(el.dataset.wasDisabled!==undefined) { el.disabled=el.dataset.wasDisabled==='1'; delete el.dataset.wasDisabled; }
        });
        if(!value) saveButton.disabled=!review;
    }
    function edited() {
        dirty = true; review = null; generation++;
        saveButton.disabled = true;
        message('Changes need preview before they can be saved.');
        canvas.removeAttribute('data-preview-ready');
    }
    function schema(fields, value) {
        return { resolve: () => value, fields, onChange: edited, rerender: renderForm };
    }
    function renderForm() {
        form.replaceChildren();
        if (!draft) return;
        buildEntityForm(form, draft, schema([
            { kind: 'text', key: 'id', label: 'Model identity', readOnly: !!originalId },
            { kind: 'text', label: 'Source path', get: data => data.source.path, set: (data,value) => { data.source.path=value; } },
            { kind: 'select', label: 'Source kind', get: data => data.source.kind,
                set: (data,value) => { data.source.kind=value; },
                options: [{value:'obj',label:'OBJ (Z-up source)'},{value:'gltf',label:'glTF / GLB (normalized to Z-up)'}] },
            { kind: 'number', key: 'sourceUnitsToMapCells', label: 'Map cells per source unit', step: 'any', parse: Number },
            { kind: 'select', key: 'appearance', label: 'Appearance binding', rerender: true,
                options: [{value:'obj-mtl',label:'Source MTL appearance (OBJ)'},{value:'',label:'Geometry / semantic Surface references'}],
                set: (data,value) => { if(value) data.appearance=value; else delete data.appearance; } },
            { kind: 'text', key: 'defaultMaterialSlot', label: 'Slot for faces with no source material', deleteIfEmpty: true },
        ], draft));
        const note=document.createElement('p');
        note.textContent='Source scale is physical world size. The item viewer fits that same model to its window. Source coordinates and geometry remain owned by the importer.';
        form.appendChild(note);
        for (const [id, slot] of Object.entries(draft.materialSlots)) {
            const group=document.createElement('fieldset');
            const title=document.createElement('legend'); title.textContent='Material slot: '+id;
            group.appendChild(title); form.appendChild(group);
            buildEntityForm(group, slot, schema([
                { kind:'textarea', label:'Source materials for '+id+' (one per line)',
                    get: data => data.sourceMaterials.join('\n'),
                    set: (data,value) => { data.sourceMaterials=value.split('\n').filter(name=>name.length>0); } },
                { kind:'text', key:'surface', label:'Surface reference for '+id, deleteIfEmpty:true,
                    readOnly: draft.appearance==='obj-mtl' },
            ], slot));
            button('Remove slot '+id, () => { delete draft.materialSlots[id]; edited(); renderForm(); }, group);
        }
        const add={id:''};
        buildEntityForm(form, add, { ...schema([{kind:'text',key:'id',label:'New material slot identity'}], add), onChange: () => {} });
        button('Add material slot', () => {
            if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(add.id) || Object.hasOwn(draft.materialSlots,add.id)) {
                message('Choose a unique slot identity using letters, numbers, dots, underscores or hyphens.'); return;
            }
            draft.materialSlots[add.id]={sourceMaterials:[]}; edited(); renderForm();
        }, form);
    }
    function choose(id) {
        if (busy) return;
        if (dirty && !root.confirm('Discard unsaved Model edits?')) return;
        generation++; originalId=id; draft=clone(records[id]);
        if(preview) { preview.destroy(); preview=null; }
        review=null; dirty=false; prepared=true; summary.textContent='';
        delete summary.dataset.sourceHash;
        saveButton.disabled=true; renderForm(); message('Preview / Reimport reads the current source without saving.');
    }
    function renderList() {
        list.replaceChildren();
        for(const id of Object.keys(records).sort()) button(id,()=>choose(id),list);
    }
    function create() {
        if (busy) return;
        if (dirty && !root.confirm('Discard unsaved Model edits?')) return;
        originalId=null; prepared=false; generation++; review=null; dirty=false;
        if(preview) { preview.destroy(); preview=null; }
        delete summary.dataset.sourceHash;
        draft={id:'',source:{kind:'obj',path:''},sourceUnitsToMapCells:1,materialSlots:{}};
        renderForm(); summary.textContent=''; saveButton.disabled=true;
        message('Choose an existing Project source. First preview discovers its material slots.');
    }
    async function inspect() {
        if (busy || !draft) return;
        setBusy(true); const request=++generation; review=null; saveButton.disabled=true;
        message('Compiling current Model source…');
        try {
            if (!prepared) {
                const result=await api('prepare',{id:draft.id,source:clone(draft.source)});
                if(request!==generation) return;
                const scale=draft.sourceUnitsToMapCells;
                draft=result.recipe; draft.sourceUnitsToMapCells=scale; prepared=true;
                renderForm();
            }
            const result=await api('preview',{recipe:clone(draft),originalId,version});
            if(request!==generation) return;
            const previous=summary.dataset.sourceHash;
            summary.dataset.sourceHash=result.summary.sourceSha256;
            summary.textContent=`${result.summary.vertices} vertices / ${result.summary.triangles} triangles\n`
                + `World bounds: ${JSON.stringify(result.summary.bounds)}\n`
                + `Source revision: ${result.summary.sourceSha256}\n`
                + `Source materials: ${result.sourceMaterials.join(', ') || '(none)'}\n`
                + (previous ? (previous===result.summary.sourceSha256 ? 'Source bytes unchanged since the previous preview.\n' : 'Source revision changed; authored slot mappings retained.\n') : '')
                + (result.unusedMappings.length ? `Unused authored mappings retained: ${JSON.stringify(result.unusedMappings)}\n` : '')
                + result.bundle.diagnostics.map(value=>value.code+': '+(value.detail?.toString() || '')).join('\n');
            if(!preview) preview=new root.SecondRiteModelPreview.ModelPreview(canvas,{interactive:true,autoRotate:false});
            let visualMessage='Preview ready. Save registers this reviewed recipe.';
            if(result.renderable) {
                try { await preview.setBundle(result.bundle); }
                catch(error) { visualMessage='Compilation ready; authoring preview unavailable: '+error.message; }
            } else {
                preview.model=null; preview.path=''; preview.render();
                visualMessage='Geometry compiled. Surface realization is unavailable; this recipe will not replace existing source visuals.';
            }
            if(request!==generation) return;
            review=result; saveButton.disabled=false; message(visualMessage);
        } catch(error) { if(request===generation) message(error.message); }
        finally { setBusy(false); }
    }
    async function save() {
        if(busy || !review) return;
        setBusy(true); saveButton.disabled=true;
        try {
            const result=await api('save',{recipe:clone(draft),originalId,version,token:review.token});
            records=result.records; version=result.version; originalId=result.id;
            dirty=false; review=null; renderList(); renderForm();
            message('Model recipe saved. Item and world consumers use it on their next acquisition / Test Play.');
        } catch(error) { review=null; message(error.message); }
        finally { setBusy(false); }
    }
    function close() {
        if(busy) return;
        if(dirty && !root.confirm('Discard unsaved Model edits?')) return;
        generation++; preview?.destroy(); preview=null;
        dirty=false; review=null; draft=null; prepared=false;
        modal?.remove(); modal=null;
    }
    async function open() {
        if(modal) return;
        modal=document.createElement('div'); modal.id='model-library-modal';
        modal.setAttribute('role','dialog'); modal.setAttribute('aria-label','Model Library');
        modal.style.cssText='position:fixed;inset:0;background:#0008;z-index:10030;display:flex;align-items:center;justify-content:center';
        const window=document.createElement('div'); window.className='outset-bevel';
        window.style.cssText='background:var(--win-gray,#c0c0c0);width:min(1100px,96vw);height:min(730px,94vh);display:flex;flex-direction:column;padding:4px';
        const title=document.createElement('div'); title.className='title-bar'; title.textContent='Model Library';
        window.appendChild(title); modal.appendChild(window); document.body.appendChild(modal);
        const tools=document.createElement('div'); tools.style.cssText='display:flex;gap:6px;padding:6px'; window.appendChild(tools);
        button('New Model',create,tools);
        button('Choose source…',()=>root.openModelPicker(draft?.source.path || '',value=>{
            if(!draft) return; draft.source.path=value; draft.source.kind=/\.obj$/i.test(value)?'obj':'gltf'; edited(); renderForm();
        },{root:'models',zIndex:10050,includeStatic:true}),tools);
        button('Preview / Reimport',inspect,tools);
        saveButton=button('Save reviewed Model',save,tools); saveButton.disabled=true;
        button('Close',close,tools);
        const body=document.createElement('div'); body.style.cssText='display:grid;grid-template-columns:180px minmax(240px,1fr) minmax(260px,1fr);gap:8px;flex:1;min-height:0;padding:6px'; window.appendChild(body);
        list=document.createElement('div'); list.style.cssText='display:flex;flex-direction:column;gap:4px;overflow:auto'; body.appendChild(list);
        form=document.createElement('div'); form.style.cssText='overflow:auto;padding:4px'; body.appendChild(form);
        const right=document.createElement('div'); right.style.cssText='display:flex;flex-direction:column;min-height:0'; body.appendChild(right);
        const label=document.createElement('div'); label.textContent='Authoring preview — final rendering uses LÖVE'; right.appendChild(label);
        const wrap=document.createElement('div'); wrap.style.cssText='position:relative;min-height:230px;height:45%;background:repeating-conic-gradient(#333 0% 25%,#444 0% 50%) 0/24px 24px'; right.appendChild(wrap);
        canvas=document.createElement('canvas'); canvas.id='model-library-preview'; canvas.style.cssText='width:100%;height:100%;display:block'; wrap.appendChild(canvas);
        summary=document.createElement('pre'); summary.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;overflow:auto;font:11px monospace'; right.appendChild(summary);
        status=document.createElement('div'); status.id='model-library-status'; status.setAttribute('role','status');
        status.style.cssText='padding:8px;border-top:1px solid #888'; window.appendChild(status);
        message('Loading Project Models…');
        try {
            const loaded=await api(); records=loaded.records; version=loaded.version;
            renderList(); const first=Object.keys(records).sort()[0];
            if(first) choose(first); else create();
        } catch(error) { message(error.message); }
    }
    root.openModelLibrary=open;
    root.closeModelLibrary=close;
})(window);
