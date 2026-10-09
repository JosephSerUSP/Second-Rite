'use strict';

const fs = require('node:fs');
const assert = require('node:assert/strict');
const net = require('node:net');
const path = require('node:path');
const { _electron: electron } = require('playwright');
const electronExecutable = require('electron');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const STUDIO_ROOT = path.resolve(__dirname, '..');
const PROJECT_ROOT = path.join(REPO_ROOT, 'projects', 'experiments', 'continuous-surface-gauntlet');
const OUTPUT_ROOT = path.resolve(process.env.CONTINUOUS_SURFACE_VISUAL_OUT
    || path.join(REPO_ROOT, 'out', 'continuous-surface-studio'));
const TIMEOUT = 45000;

function freePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.unref();
        server.once('error', reject);
        server.listen(0, '127.0.0.1', () => {
            const address = server.address();
            server.close(error => error ? reject(error) : resolve(address.port));
        });
    });
}

async function waitFor(description, probe, predicate = value => !!value, timeout = TIMEOUT) {
    const deadline = Date.now() + timeout;
    let last;
    while (Date.now() < deadline) {
        try {
            last = await probe();
            if (predicate(last)) return last;
        } catch (_) {}
        await new Promise(resolve => setTimeout(resolve, 75));
    }
    throw new Error(`Timed out waiting for ${description}; last=${JSON.stringify(last)}`);
}

async function capture(page, name) {
    const output = path.join(OUTPUT_ROOT, name);
    await page.screenshot({ path: output, animations: 'disabled' });
    console.log(`[continuous-surface-proof] ${output}`);
}

function expectedLegacyCanvasDiagnostic(line) {
    return line.includes("InvalidStateError: Failed to execute 'drawImage'")
        && line.includes('map-editor.js');
}

function relevantDiagnostic(line) {
    if (expectedLegacyCanvasDiagnostic(line)) return false;
    if (line.includes('ERR_CONNECTION_REFUSED')
            && !/walk[- ]surface|renderable/i.test(line)) return false;
    if (/walk[- ]surface|renderable/i.test(line)) return true;
    return line.startsWith('pageerror:');
}

async function authoritySnapshot(page) {
    return page.evaluate(() => {
        const host = window.ThestraEditorHost;
        const viewport = window.ThestraRuntimeCameraViewport;
        const failure = document.getElementById('thestra-map-runtime-failure');
        return {
            mapIndex: host?.getMapIndex?.(),
            status: document.getElementById('thestra-map-view-status')?.textContent || '',
            failureVisible: !!failure && getComputedStyle(failure).display !== 'none',
            failureText: failure?.textContent || '',
            walkSurface: viewport?.getWalkSurfaceInfo?.() || null,
            inspector: document.getElementById('thestra-map-inspector-body')?.textContent || '',
            renderableUrl: globalThis.THESTRA_RENDERABLE_URL || null,
        };
    });
}

async function selectMap(page, index, packageFragment, expectedTitle) {
    // This original-content gauntlet intentionally has no legacy tileset art.
    // The retired hidden 2D canvas still attempts to draw that absent image
    // during map selection; suppress only its InvalidStateError in this proof
    // harness. The live Three/runtime path remains untouched and is gated below.
    await page.evaluate(expectedIndex => {
        const proto = CanvasRenderingContext2D.prototype;
        const nativeDrawImage = proto.drawImage;
        proto.drawImage = function (...args) {
            try {
                return nativeDrawImage.apply(this, args);
            } catch (error) {
                if (error && error.name === 'InvalidStateError') return undefined;
                throw error;
            }
        };
        try {
            currentMapIndex = expectedIndex;
            loadActiveMap();
            window.ThestraEditorHost?.selectSemantic?.(null);
        } finally {
            proto.drawImage = nativeDrawImage;
        }
    }, index);

    try {
        await page.waitForFunction(({ expectedIndex, fragment }) => {
            const host = window.ThestraEditorHost;
            const viewport = window.ThestraRuntimeCameraViewport;
            const status = document.getElementById('thestra-map-view-status')?.textContent || '';
            const failure = document.getElementById('thestra-map-runtime-failure');
            const failed = failure && getComputedStyle(failure).display !== 'none';
            const info = viewport?.getWalkSurfaceInfo?.();
            return !!host && host.getMapIndex() === expectedIndex
                && !!info?.available
                && String(info.manifestPath || '').includes(fragment)
                && !failed
                && /runtime geometry/i.test(status);
        }, { expectedIndex: index, fragment: packageFragment }, { timeout: TIMEOUT });
    } catch (error) {
        const snapshot = await authoritySnapshot(page);
        throw new Error(`runtime authority did not settle for ${expectedTitle}: ${JSON.stringify(snapshot)}`);
    }

    // Force the Inspector through its public selection boundary after the map
    // has settled. It is visual context, not an engine gate.
    await page.evaluate(() => {
        window.ThestraEditorHost?.selectSemantic?.(null);
        const viewport = window.ThestraRuntimeCameraViewport;
        viewport.setCollisionVisible?.(false);
        viewport.setWalkSurfaceVisible?.(true);
        viewport.frameScene?.();
    });
    await page.waitForTimeout(400);
}

async function main() {
    fs.mkdirSync(OUTPUT_ROOT, { recursive: true });
    const [editorPort, bridgePort] = await Promise.all([freePort(), freePort()]);
    const diagnostics = [];
    let app;
    try {
        app = await electron.launch({
            executablePath: electronExecutable,
            args: [STUDIO_ROOT, '--project', PROJECT_ROOT],
            cwd: REPO_ROOT,
            env: {
                ...process.env,
                PORT: String(editorPort),
                EDITOR_PORT: String(editorPort),
                RUNTIME_BRIDGE_PORT: String(bridgePort),
                ELECTRON_DISABLE_GPU: '1',
            },
            timeout: TIMEOUT,
        });
        const page = await waitFor('main Studio renderer', () => app.windows().find(candidate =>
            /^http:\/\/127\.0\.0\.1:\d+\/(?:\?.*)?$/.test(candidate.url())) || null);
        // Publish the isolated bridge before any authoring script requests a
        // bundle. Setting it after boot races the adapter's default port.
        const mainUrl = page.url();
        await page.goto('about:blank');
        await page.addInitScript(url => { globalThis.THESTRA_RENDERABLE_URL = url; },
            `http://127.0.0.1:${bridgePort}/api/map-renderable`);
        page.on('pageerror', error => diagnostics.push(`pageerror: ${error.stack || error.message}`));
        page.on('response', response => { if(response.status()>=400) diagnostics.push(`http: ${response.status()} ${response.url()}`); });
        page.on('console', message => {
            if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
        });
        await page.goto(mainUrl);
        await page.waitForFunction(() => {
            const boot = window.thestraDatabaseBootState;
            return !!window.thestraStudio && !!boot && boot.done === true;
        }, null, { timeout: TIMEOUT });

        // Exactly the same isolation contract as G6: the CI host owns a random
        // bridge port and publishes it to the browser adapter before requesting
        // an authoritative bundle.
        await page.evaluate(url => { globalThis.THESTRA_RENDERABLE_URL = url; },
            `http://127.0.0.1:${bridgePort}/api/map-renderable`);

        await app.evaluate(({ BrowserWindow }) => {
            const win = BrowserWindow.getAllWindows().find(candidate =>
                !candidate.webContents.getURL().includes('surface='));
            if (win) win.setSize(1440, 900);
            return true;
        });
        await page.waitForTimeout(250);
        await page.waitForFunction(() => !!window.ThestraRuntimeCameraViewport?.getWalkSurfaceInfo,
            null, { timeout: TIMEOUT });

        await selectMap(page, 0, 'archive_antechamber', 'Archive Antechamber');
        await page.evaluate(() => {
            const viewport = window.ThestraRuntimeCameraViewport;
            viewport.setMode?.('perspective');
            viewport.frameScene?.();
        });
        await page.waitForTimeout(300);
        await capture(page, '01-archive-perspective-walk-surface.png');

        await page.evaluate(() => {
            const viewport = window.ThestraRuntimeCameraViewport;
            viewport.setMode?.('top');
            viewport.setAxisView?.('top');
            viewport.frameScene?.();
        });
        await page.waitForTimeout(300);
        await capture(page, '02-archive-top-walk-surface.png');

        await selectMap(page, 1, 'service_annex', 'Service Annex');
        await page.evaluate(() => {
            const viewport = window.ThestraRuntimeCameraViewport;
            viewport.setMode?.('top');
            viewport.setAxisView?.('top');
            viewport.frameScene?.();
        });
        await page.waitForTimeout(300);
        await capture(page, '03-service-annex-top-walk-surface.png');

        await page.evaluate(() => {
            const viewport = window.ThestraRuntimeCameraViewport;
            viewport.setMode?.('perspective');
            viewport.setAxisView?.('front');
            viewport.setCollisionVisible?.(true);
            viewport.setWalkSurfaceVisible?.(true);
            viewport.frameScene?.();
        });
        await page.waitForTimeout(300);
        await capture(page, '04-service-annex-walk-vs-collision.png');

        // Inspect actual Three meshes at the renderer boundary, without adding
        // a test-only production API or evaluating a second skin implementation.
        await page.evaluate(async () => {
            const THREE=await import('three');
            const add=THREE.Object3D.prototype.add;
            window.__eventCharacterMeshes=[];
            THREE.Object3D.prototype.add=function(...objects) {
                for (const object of objects) {
                    if (object.userData.thestraEventCharacter) window.__eventCharacterMeshes.push(object);
                }
                return add.apply(this,objects);
            };
        });
        await selectMap(page,0,'archive_antechamber','Archive Antechamber');
        const cameraBefore=await page.evaluate(()=>JSON.stringify(window.ThestraRuntimeCameraViewport.captureCameraState()));
        await page.getByRole('button',{name:'Runtime Camera',exact:true}).click();
        await page.waitForTimeout(350);
        const cameraProof=await page.evaluate(() => {
            const scene=dbPayload.scenes.find(value=>value.id==='map');
            const resolved=ThestraWorldPresentation.resolveCamera(scene.worldPresentation.camera,{});
            const actual=ThestraRuntimeCameraViewport.captureCameraState().perspective;
            return {expected:ThestraViewportContract.runtimePositionToThestra([resolved.x,resolved.y,resolved.z]),
                actual:actual.position,selectedScene:document.querySelector('[data-toolbar-owner="world-presentation"]')?.textContent,
                toolbar:document.getElementById('thestra-map-view-toolbar').textContent};
        });
        cameraProof.actual.forEach((value,index)=>assert.ok(Math.abs(value-cameraProof.expected[index])<1e-7));
        assert.doesNotMatch(cameraProof.toolbar,/No Map world Scene|Cannot read properties/);
        await capture(page,'05-archive-runtime-camera.png');
        await page.getByRole('button',{name:'Free Authoring',exact:true}).click();
        assert.equal(await page.evaluate(()=>JSON.stringify(ThestraRuntimeCameraViewport.captureCameraState())),cameraBefore,
            'Runtime Camera must restore the exact free authoring camera');

        const movementProof=await page.evaluate(async () => {
            const THREE=await import('three');
            const event=dbPayload.maps[0].events.find(value=>value.id===101);
            const original=event.worldPosition.slice();
            const mesh=window.__eventCharacterMeshes.findLast(value=>value.parent);
            if (!mesh) throw Error('Actual compiled Event mesh missing from Studio');
            const vertex=()=>{
                mesh.updateWorldMatrix(true,false);
                return new THREE.Vector3().fromBufferAttribute(mesh.geometry.getAttribute('position'),0)
                    .applyMatrix4(mesh.matrixWorld).toArray();
            };
            const before=vertex();
            SecondRiteEditorCommands.moveWorldEvent(dbPayload,0,101,[original[0]+0.4,original[1]+0.3,original[2]]);
            await ThestraRuntimeCameraViewport.setSceneModel(ThestraEditorScene.buildScene(dbPayload,dbPayload.maps[0]));
            const moved=vertex();
            if (!mesh.parent) throw Error('Semantic refresh dropped the retained character');
            SecondRiteEditorCommands.moveWorldEvent(dbPayload,0,101,original);
            await ThestraRuntimeCameraViewport.setSceneModel(ThestraEditorScene.buildScene(dbPayload,dbPayload.maps[0]));
            return {before,moved,restored:vertex(),source:mesh.userData.thestraSource};
        });
        [0.4,0,0.3].forEach((delta,index)=>assert.ok(Math.abs(movementProof.moved[index]-movementProof.before[index]-delta)<1e-7));
        movementProof.restored.forEach((value,index)=>assert.ok(Math.abs(value-movementProof.before[index])<1e-7));

        const originalEvent=await page.evaluate(()=>JSON.stringify(dbPayload.maps[0].events.find(value=>value.id===101)));
        await page.evaluate(()=>openEventModal(0,0,101));
        await page.locator('#field-event-character-height').fill('1.8');
        await capture(page,'06-attendant-character-controls.png');
        await page.evaluate(()=>applyEventProperties());
        assert.equal(await page.evaluate(()=>dbPayload.maps[0].events.find(value=>value.id===101).actorAppearance.height),1.8);
        await page.evaluate(()=>openEventModal(0,0,101));
        await page.locator('#field-event-character-height').fill('2');
        await page.evaluate(()=>closeEventModal(true));
        assert.equal(await page.evaluate(()=>dbPayload.maps[0].events.find(value=>value.id===101).actorAppearance.height),1.8,
            'closing the modal must not commit its working appearance');
        await page.evaluate(original => {
            const event=dbPayload.maps[0].events.find(value=>value.id===101);
            for (const key of Object.keys(event)) delete event[key];
            Object.assign(event,JSON.parse(original));
        },originalEvent);

        const sceneBefore=await page.evaluate(()=>JSON.stringify(dbPayload.scenes.find(value=>value.id==='map')));
        const mapsBefore=await page.evaluate(()=>JSON.stringify(dbPayload.maps));
        await page.evaluate(()=>openEngineModal());
        const enginePage=await waitFor('native Engine surface', async()=>app.windows().find(value=>new URL(value.url()).searchParams.get('surface')==='engine'));
        await enginePage.waitForFunction(()=>typeof dbPayload !== 'undefined' && Array.isArray(dbPayload.scenes));
        await enginePage.evaluate(()=>{activeSceneId='map';setEngineTab('flows');});
        await enginePage.locator('#field-scene-camera-yawDegrees').fill('15');
        await enginePage.locator('#field-scene-camera-distance').fill('0');
        assert.equal(await enginePage.evaluate(()=>dbPayload.scenes.find(value=>value.id==='map').worldPresentation.camera.distance),11.5);
        assert.equal(await enginePage.locator('#field-scene-camera-distance').evaluate(input=>input.checkValidity()),false);
        await enginePage.locator('#field-scene-camera-distance').fill('12');
        await capture(enginePage,'07-scene-camera-controls.png');
        assert.equal(await enginePage.evaluate(()=>JSON.stringify(dbPayload.maps)),mapsBefore,'camera controls mutated Map data');
        await enginePage.evaluate(original=>{
            const scene=dbPayload.scenes.find(value=>value.id==='map');
            for (const key of Object.keys(scene)) delete scene[key];
            Object.assign(scene,JSON.parse(original));closeEngineModal(true);
        },sceneBefore);

        await selectMap(page,1,'service_annex','Service Annex');
        const arenaEventBefore=await page.evaluate(()=>JSON.stringify(dbPayload.maps[1].events.find(value=>value.id===203)));
        await page.evaluate(()=>{
            const event=dbPayload.maps[1].events.find(value=>value.id===203);
            openCommandModalForEdit(event.commands,0,()=>{}, {context:'map'});
        });
        assert.equal(await page.locator('#cmd-dyn-enemyUnitId').inputValue(),'sentinel');
        assert.equal(await page.locator('#cmd-dyn-range').inputValue(),'2.6');
        assert.equal(await page.locator('#cmd-dyn-readySeconds').inputValue(),'2.5');
        await capture(page,'08-arena-command-authoring.png');
        await page.evaluate(()=>closeCmdDialog(true));
        assert.equal(await page.evaluate(()=>JSON.stringify(dbPayload.maps[1].events.find(value=>value.id===203))),arenaEventBefore,
            'opening arena command fields mutated authored data');

        const summary = await authoritySnapshot(page);
        summary.collisionVisible = await page.evaluate(() =>
            window.ThestraRuntimeCameraViewport?.getCollisionVisible?.());
        const fatalDiagnostics = diagnostics.filter(relevantDiagnostic);
        fs.writeFileSync(path.join(OUTPUT_ROOT, 'proof.json'), JSON.stringify({
            summary,
            cameraProof,
            movementProof,
            diagnostics,
            fatalDiagnostics,
        }, null, 2) + '\n');
        if (fatalDiagnostics.length) {
            throw new Error(`Studio emitted relevant visual-proof diagnostics:\n${fatalDiagnostics.join('\n')}`);
        }
    } finally {
        if (app) {
            try { await app.evaluate(({ app: electronApp }) => electronApp.exit(0)); } catch (_) {}
            try { await app.close(); } catch (_) {}
        }
    }
}

main().catch(error => {
    console.error(error.stack || error.message || String(error));
    process.exitCode = 1;
});
