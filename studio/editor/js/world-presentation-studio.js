(function (root) {
    'use strict';

    const WorldPresentation = root.ThestraWorldPresentation;
    if (!WorldPresentation || typeof document === 'undefined') return;

    const previewState = WorldPresentation.createPreviewStateMachine();
    let runtimeSceneId = null;
    let runtimeViewportInset = null;
    let runtimeControls = null;

    function markSceneChanged(scene) {
        if (typeof root.setDirty === 'function') root.setDirty(true);
        root.dispatchEvent(new CustomEvent('thestra-world-presentation-changed', {
            detail: { sceneId: scene && scene.id }
        }));
    }

    function smallNote(text) {
        const note = document.createElement('div');
        note.style.cssText = 'font-size:10px;color:var(--win-dark-shadow);line-height:1.35;margin:3px 0 6px;';
        note.textContent = text;
        return note;
    }

    function fieldRow(labelText, control, hint) {
        const row = document.createElement('label');
        row.style.cssText = 'display:flex;align-items:center;gap:6px;margin:4px 0;font-size:10px;';
        const label = document.createElement('span');
        label.style.cssText = 'width:92px;flex:0 0 92px;';
        label.textContent = labelText;
        row.append(label, control);
        if (hint) {
            const help = document.createElement('span');
            help.style.cssText = 'color:var(--win-dark-shadow);font-size:9px;';
            help.textContent = hint;
            row.appendChild(help);
        }
        return row;
    }

    function installWorldPresentationPanel(container, scene) {
        if (!scene || scene.draw !== 'world' || scene.world !== 'map') return;

        const fieldset = document.createElement('fieldset');
        fieldset.dataset.thestraWorldPresentation = 'true';
        fieldset.style.cssText = 'padding:6px;margin-bottom:6px;';
        const legend = document.createElement('legend');
        legend.textContent = 'World Presentation';
        fieldset.appendChild(legend);

        const body = document.createElement('div');
        fieldset.appendChild(body);
        let measuredImage = null;

        function cameraObject() {
            const presentation = scene.worldPresentation;
            return presentation && presentation.camera && typeof presentation.camera === 'object'
                ? presentation.camera : null;
        }

        function pixelsPerTile() {
            const presentation = scene.worldPresentation;
            return presentation && Number.isFinite(presentation.pixelsPerTile)
                ? presentation.pixelsPerTile : null;
        }

        function renderMeasurement(output) {
            if (!measuredImage) {
                output.textContent = 'Choose an image to inspect its authored design size in world-tile units.';
                return;
            }
            const density = pixelsPerTile();
            if (!density) {
                output.textContent = `${measuredImage.name}: ${measuredImage.width}×${measuredImage.height} design px · pixelsPerTile is using the engine/default fallback.`;
                return;
            }
            const tiles = WorldPresentation.imageSizeInTiles(
                measuredImage.width, measuredImage.height, density
            );
            output.textContent = `${measuredImage.name}: ${measuredImage.width}×${measuredImage.height} design px → ${tiles.width.toFixed(3)}×${tiles.height.toFixed(3)} world tiles @ ${density} px/tile.`;
        }

        function renderBody() {
            body.innerHTML = '';
            body.appendChild(smallNote(
                `Owner: Scene ${scene.id}. These are runtime presentation semantics; Map topology/collision is not copied or rewritten here.`
            ));

            const validation = document.createElement('div');
            validation.style.cssText = 'font-size:9px;color:#a00000;min-height:12px;margin-bottom:2px;';
            body.appendChild(validation);
            const showError = (error) => { validation.textContent = error ? error.message || String(error) : ''; };

            const densityEnabled = document.createElement('input');
            densityEnabled.type = 'checkbox';
            densityEnabled.checked = !!(scene.worldPresentation
                && WorldPresentation.own(scene.worldPresentation, 'pixelsPerTile'));
            const densityLabel = document.createElement('span');
            densityLabel.textContent = ' Author pixels-per-tile';
            const densityToggle = document.createElement('span');
            densityToggle.append(densityEnabled, densityLabel);
            body.appendChild(fieldRow('Density:', densityToggle, 'unchecked = engine/default fallback'));

            const densityInput = document.createElement('input');
            densityInput.type = 'number';
            densityInput.className = 'win98-input';
            densityInput.min = '0.0001';
            densityInput.step = '1';
            densityInput.style.width = '110px';
            densityInput.disabled = !densityEnabled.checked;
            densityInput.value = pixelsPerTile() == null ? '24' : String(pixelsPerTile());
            body.appendChild(fieldRow('Pixels / tile:', densityInput, 'design density, not monitor pixels'));

            densityEnabled.addEventListener('change', () => {
                try {
                    if (densityEnabled.checked) {
                        WorldPresentation.setPixelsPerTile(scene, pixelsPerTile() == null ? 24 : pixelsPerTile());
                    } else {
                        WorldPresentation.setPixelsPerTile(scene, null);
                    }
                    showError(null);
                    markSceneChanged(scene);
                    renderBody();
                } catch (error) { showError(error); }
            });
            densityInput.addEventListener('input', () => {
                try {
                    if (densityInput.value === '') throw new Error('worldPresentation.pixelsPerTile must be a positive finite number');
                    WorldPresentation.setPixelsPerTile(scene, densityInput.value);
                    densityInput.style.background = '';
                    showError(null);
                    markSceneChanged(scene);
                    renderMeasurement(measureOutput);
                } catch (error) {
                    densityInput.style.background = '#ffcccc';
                    showError(error);
                }
            });

            const measureRow = document.createElement('div');
            measureRow.style.cssText = 'display:flex;align-items:center;gap:6px;margin:6px 0 8px;';
            const chooseImage = document.createElement('button');
            chooseImage.type = 'button';
            chooseImage.className = 'win98-btn';
            chooseImage.style.cssText = 'font-size:10px;padding:2px 6px;';
            chooseImage.textContent = 'Measure image…';
            chooseImage.title = 'Select an image asset/file and report its natural design-pixel size in world tiles.';
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = 'image/*';
            fileInput.style.display = 'none';
            const measureOutput = document.createElement('span');
            measureOutput.style.cssText = 'font-size:9px;color:var(--win-dark-shadow);line-height:1.3;';
            chooseImage.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', () => {
                const file = fileInput.files && fileInput.files[0];
                if (!file) return;
                const url = URL.createObjectURL(file);
                const image = new Image();
                image.onload = () => {
                    measuredImage = { name: file.name, width: image.naturalWidth, height: image.naturalHeight };
                    URL.revokeObjectURL(url);
                    renderMeasurement(measureOutput);
                };
                image.onerror = () => {
                    URL.revokeObjectURL(url);
                    measureOutput.textContent = `Could not read image dimensions for ${file.name}.`;
                };
                image.src = url;
            });
            measureRow.append(chooseImage, fileInput, measureOutput);
            body.appendChild(measureRow);
            renderMeasurement(measureOutput);

            const camera = cameraObject();
            const cameraEnabled = document.createElement('input');
            cameraEnabled.type = 'checkbox';
            cameraEnabled.checked = !!camera;
            const cameraToggle = document.createElement('span');
            cameraToggle.append(cameraEnabled, document.createTextNode(' Author runtime camera'));
            body.appendChild(fieldRow('Camera:', cameraToggle, 'unchecked = engine/default first_person'));

            cameraEnabled.addEventListener('change', () => {
                try {
                    if (cameraEnabled.checked) WorldPresentation.setCameraField(scene, 'profile', 'first_person');
                    else WorldPresentation.clearCamera(scene);
                    showError(null);
                    markSceneChanged(scene);
                    renderBody();
                } catch (error) { showError(error); }
            });

            if (camera) {
                const profileSelect = document.createElement('select');
                profileSelect.className = 'win98-input';
                profileSelect.style.width = '180px';
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Default — first_person';
                profileSelect.appendChild(defaultOption);
                WorldPresentation.PROFILE_IDS.forEach(id => {
                    const option = document.createElement('option');
                    option.value = id;
                    option.textContent = id;
                    profileSelect.appendChild(option);
                });
                profileSelect.value = camera.profile || '';
                body.appendChild(fieldRow('Profile:', profileSelect, 'existing runtime profile'));
                profileSelect.addEventListener('change', () => {
                    try {
                        WorldPresentation.setCameraField(scene, 'profile', profileSelect.value || null);
                        showError(null);
                        markSceneChanged(scene);
                        renderBody();
                    } catch (error) { showError(error); }
                });

                const effectiveProfile = camera.profile || 'first_person';
                const profileSpec = WorldPresentation.PROFILE_SPECS[effectiveProfile];
                const addNumericCameraField = (label, key, hint, attrs) => {
                    const input = document.createElement('input');
                    input.type = 'number';
                    input.className = 'win98-input';
                    input.style.width = '110px';
                    input.placeholder = 'default';
                    Object.keys(attrs || {}).forEach(name => input.setAttribute(name, attrs[name]));
                    input.value = camera[key] == null ? '' : String(camera[key]);
                    input.addEventListener('input', () => {
                        try {
                            WorldPresentation.setCameraField(scene, key, input.value === '' ? null : input.value);
                            input.style.background = '';
                            showError(null);
                            markSceneChanged(scene);
                        } catch (error) {
                            input.style.background = '#ffcccc';
                            showError(error);
                        }
                    });
                    body.appendChild(fieldRow(label, input, hint));
                };

                if (effectiveProfile !== 'first_person') {
                    addNumericCameraField('Pitch:', 'pitchDegrees', 'degrees; default 45', { min: '0.001', max: '89.999', step: '1' });
                    addNumericCameraField('Yaw:', 'yawDegrees', 'degrees; default -90 / north', { step: '1' });
                }
                if (profileSpec && profileSpec.projection === 'perspective' && effectiveProfile !== 'first_person') {
                    addNumericCameraField('FOV:', 'fovDegrees', `horizontal degrees; default ${profileSpec.fovDegrees || 26}`, { min: '0.001', max: '178.999', step: '1' });
                    addNumericCameraField('Tiles across:', 'tilesAcross', `framing; default ${profileSpec.tilesAcross || 18}`, { min: '0.001', step: '1' });
                }
            }

            const provenance = document.createElement('div');
            provenance.style.cssText = 'font-size:9px;color:var(--win-dark-shadow);margin-top:5px;';
            provenance.textContent = camera
                ? 'Camera source: authored Scene.worldPresentation.camera.'
                : 'Camera source: engine/default fallback → first_person. No Map-local camera override exists.';
            body.appendChild(provenance);
        }

        renderBody();
        const visualPreview = Array.from(container.children).find(child => child.tagName === 'FIELDSET'
            && child.querySelector('legend') && child.querySelector('legend').textContent === 'Visual Preview');
        container.insertBefore(fieldset, visualPreview || null);
    }

    function installSceneEditorHook() {
        if (root.__thestraWorldPresentationSceneEditorInstalled) return true;
        const original = root.renderCustomSceneEditor;
        if (typeof original !== 'function') return false;
        root.renderCustomSceneEditor = function (container, header, scene) {
            const result = original.apply(this, arguments);
            installWorldPresentationPanel(container, scene);
            return result;
        };
        root.__thestraWorldPresentationSceneEditorInstalled = true;
        return true;
    }

    function payload() {
        const host = root.ThestraEditorHost;
        return host && host.getPayload ? host.getPayload() : root.dbPayload;
    }

    function mapIndex() {
        const host = root.ThestraEditorHost;
        return host && host.getMapIndex ? host.getMapIndex() : root.currentMapIndex;
    }

    function worldScenes() {
        return WorldPresentation.mapWorldScenes(payload());
    }

    function selectedWorldScene() {
        const scenes = worldScenes();
        if (!scenes.length) return null;
        let scene = scenes.find(candidate => String(candidate.id) === String(runtimeSceneId));
        if (!scene) {
            scene = scenes[0];
            runtimeSceneId = scene.id;
        }
        return scene;
    }

    function viewportApi() {
        return root.ThestraRuntimeCameraViewport || null;
    }

    // The game has a fixed presentation frame; Studio does not.  Constraining
    // the editor host to 256:144 created a dead lower band whenever the Map
    // workspace had another aspect.  The runtime projection remains exact;
    // its authoring surface fills the available workspace.
    function fillRuntimeViewport() {
        const viewport = document.getElementById('thestra-map-viewport');
        if (viewport) viewport.style.inset = '0px';
    }

    function updateRuntimeControls() {
        if (!runtimeControls) return;
        runtimeControls.syncWalkMesh?.();
        runtimeControls.syncWalkProfile?.();
        const runtime = previewState.mode() === 'runtime';
        const plate = viewportApi()?.getCompositionPreview?.();
        runtimeControls.runtime.textContent = plate ? 'Plate Composition' : 'Runtime Camera';
        runtimeControls.free.textContent = plate ? '3D View' : 'Free Authoring';
        runtimeControls.free.disabled = !runtime;
        runtimeControls.runtime.disabled = runtime || !worldScenes().length;
        if (runtime) {
            runtimeControls.projectionButtons.forEach(button => { button.disabled = true; });
        } else if (runtimeControls.projectionDisabled) {
            runtimeControls.projectionButtons.forEach((button, index) => {
                button.disabled = !!runtimeControls.projectionDisabled[index];
            });
            runtimeControls.projectionDisabled = null;
        }
        const scene = selectedWorldScene();
        runtimeControls.sceneSelect.innerHTML = '';
        worldScenes().forEach(candidate => {
            const option = document.createElement('option');
            option.value = String(candidate.id);
            option.textContent = candidate.name || candidate.id;
            runtimeControls.sceneSelect.appendChild(option);
        });
        if (scene) runtimeControls.sceneSelect.value = String(scene.id);
        runtimeControls.sceneSelect.style.display = worldScenes().length > 1 ? '' : 'none';
        if (!scene) runtimeControls.info.textContent = 'No Scene with draw: world / world: map.';
        else if (!runtime) runtimeControls.info.textContent = `Runtime source: Scene ${scene.id}; free camera is editor-only.`;
    }

    function applyRuntimePreview() {
        const viewport = viewportApi();
        const scene = selectedWorldScene();
        if (!viewport || !scene) return false;
        const focus = WorldPresentation.previewFocus(
            payload(), mapIndex(), viewport.getSelection ? viewport.getSelection() : null
        );
        const authoredCamera = scene.worldPresentation && scene.worldPresentation.camera;
        const spatialCamera = viewport.getSpatialCamera && viewport.getSpatialCamera();
        const composition = viewport.getCompositionPreview && viewport.getCompositionPreview();
        const map = payload().maps[mapIndex()];
        if (map && map.traversal && map.traversal.environmentPackage && !spatialCamera && !composition) {
            if (runtimeControls) runtimeControls.info.textContent = 'Waiting for current Map camera compilation.';
            return false;
        }
        if (composition) {
            viewport.showComposition('authoring/map');
            fillRuntimeViewport();
            if (runtimeControls) runtimeControls.info.textContent = 'Select Event boxes · drag gizmo · background drag pans · wheel zooms';
            return true;
        }
        const resolved = spatialCamera || WorldPresentation.resolveCamera(authoredCamera, focus);
        viewport.applyRuntimeCamera(resolved);
        fillRuntimeViewport();
        if (runtimeControls) {
            runtimeControls.info.textContent = spatialCamera
                ? `Map traversal · ${resolved.profile} · drag shifts camera · wheel zooms`
                : `Scene ${scene.id} · ${resolved.provenance} · ${resolved.profile} · focus: ${focus.source}`;
        }
        return true;
    }

    function enterRuntimePreview() {
        const viewport = viewportApi();
        if (!viewport || !selectedWorldScene()) return;
        const viewportElement = document.getElementById('thestra-map-viewport');
        if (previewState.mode() !== 'runtime') {
            runtimeViewportInset = viewportElement ? viewportElement.style.inset : null;
        }
        if (previewState.mode() !== 'runtime' && runtimeControls) {
            runtimeControls.projectionDisabled = runtimeControls.projectionButtons.map(button => button.disabled);
        }
        previewState.enter(() => viewport.captureCameraState());
        applyRuntimePreview();
        updateRuntimeControls();
    }

    function leaveRuntimePreview() {
        const viewport = viewportApi();
        if (!viewport) return;
        previewState.leave(snapshot => viewport.restoreCameraState(snapshot));
        const viewportElement = document.getElementById('thestra-map-viewport');
        if (viewportElement) viewportElement.style.inset = runtimeViewportInset == null ? '0px' : runtimeViewportInset;
        runtimeViewportInset = null;
        updateRuntimeControls();
    }

    function installRuntimeToolbar() {
        if (runtimeControls) return true;
        const toolbar = root.ThestraMapWorkspaceToolbar;
        if (!toolbar || typeof toolbar.mount !== 'function'
            || typeof toolbar.projectionButtons !== 'function') return false;
        const projectionButtons = toolbar.projectionButtons();
        const free = document.createElement('button');
        free.type = 'button';
        free.className = 'win98-btn';
        free.style.cssText = 'font-size:10px;padding:2px 6px;white-space:nowrap;flex-shrink:0;';
        free.textContent = 'Free Authoring';
        free.title = 'Restore the exact editor camera pose used before Runtime Camera preview.';
        const runtime = document.createElement('button');
        runtime.type = 'button';
        runtime.className = 'win98-btn';
        runtime.style.cssText = 'font-size:10px;padding:2px 6px;white-space:nowrap;flex-shrink:0;';
        runtime.textContent = 'Runtime Camera';
        runtime.title = 'Preview the selected world Scene through the real #617 runtime camera semantics.';
        const walkMesh = document.createElement('button');
        walkMesh.type = 'button';
        walkMesh.className = 'win98-btn';
        walkMesh.style.cssText = 'font-size:10px;padding:2px 6px;white-space:nowrap;flex-shrink:0;';
        walkMesh.title = 'Show the runtime collision mesh for 3D environments or the authored traversal lane for plates. Inspection only.';
        function syncWalkMesh() {
            const viewport = viewportApi();
            walkMesh.textContent = viewport?.getWalkMeshVisible?.() ? 'Walk Mesh: On' : 'Walk Mesh';
        }
        const walkProfile = document.createElement('button');
        walkProfile.type = 'button';
        walkProfile.className = 'win98-btn';
        walkProfile.style.cssText = 'font-size:10px;padding:2px 6px;white-space:nowrap;flex-shrink:0;display:none;';
        walkProfile.title = 'Edit Map-owned bounded-lane groundProfile control points. This never edits collision mesh geometry.';
        walkProfile.textContent = 'Walk Profile';

        const createProfile = document.createElement('button');
        createProfile.type = 'button';
        createProfile.className = 'win98-btn';
        createProfile.style.cssText = 'font-size:10px;padding:2px 6px;white-space:nowrap;flex-shrink:0;display:none;';
        createProfile.title = 'Explicitly create a flat two-point groundProfile from the current lane bounds and groundZ.';
        createProfile.textContent = 'Create Profile';

        const splitProfile = document.createElement('button');
        splitProfile.type = 'button';
        splitProfile.className = 'win98-btn';
        splitProfile.style.cssText = 'font-size:10px;padding:2px 6px;white-space:nowrap;flex-shrink:0;display:none;';
        splitProfile.title = 'Select a Walk Profile segment, then split it at its interpolated midpoint.';
        splitProfile.textContent = 'Split Segment';

        const deleteProfile = document.createElement('button');
        deleteProfile.type = 'button';
        deleteProfile.className = 'win98-btn';
        deleteProfile.style.cssText = 'font-size:10px;padding:2px 6px;white-space:nowrap;flex-shrink:0;display:none;';
        deleteProfile.title = 'Select an interior Walk Profile point to remove it. Endpoints are protected.';
        deleteProfile.textContent = 'Delete Point';

        function syncWalkProfile() {
            const viewport = viewportApi();
            const status = viewport?.getWalkProfileStatus?.();
            const show = !!status?.available;
            for (const control of [walkProfile, createProfile, splitProfile, deleteProfile]) {
                control.style.display = show ? '' : 'none';
            }
            if (!show) return;
            walkProfile.classList.toggle('active', !!status.editing);
            walkProfile.textContent = status.editing ? 'Walk Profile: Editing' : 'Walk Profile';
            createProfile.disabled = !!status.authored;
            splitProfile.disabled = !status.editing || !status.authored
                || status.selection?.kind !== 'walk-profile-segment';
            const endpoint = status.selection?.kind === 'walk-profile-point'
                && (status.selection.index === 0 || status.selection.index === status.pointCount - 1);
            deleteProfile.disabled = !status.editing || !status.authored
                || status.selection?.kind !== 'walk-profile-point' || endpoint;
        }

        const sceneSelect = document.createElement('select');
        sceneSelect.className = 'win98-input';
        sceneSelect.style.cssText = 'font-size:9px;max-width:120px;height:20px;';
        sceneSelect.title = 'World Scene whose Scene-owned worldPresentation is being previewed.';
        const info = document.createElement('span');
        info.style.cssText = 'font-size:9px;color:var(--win-dark-shadow);max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';

        free.addEventListener('click', leaveRuntimePreview);
        runtime.addEventListener('click', enterRuntimePreview);
        walkMesh.addEventListener('click', () => {
            const viewport = viewportApi();
            if (!viewport?.setWalkMeshVisible) return;
            viewport.setWalkMeshVisible(!viewport.getWalkMeshVisible());
            syncWalkMesh();
        });
        walkProfile.addEventListener('click', () => {
            const viewport = viewportApi();
            if (!viewport?.setWalkProfileEditing) return;
            viewport.setWalkProfileEditing(!viewport.getWalkProfileEditing());
            syncWalkProfile();
        });
        createProfile.addEventListener('click', () => {
            const viewport = viewportApi();
            const result = viewport?.createGroundProfile?.();
            if (result?.ok) viewport.setWalkProfileEditing(true);
            syncWalkProfile();
        });
        splitProfile.addEventListener('click', () => {
            viewportApi()?.splitSelectedGroundProfileSegment?.(0.5);
            syncWalkProfile();
        });
        deleteProfile.addEventListener('click', () => {
            viewportApi()?.deleteSelectedGroundProfilePoint?.();
            syncWalkProfile();
        });
        sceneSelect.addEventListener('change', () => {
            runtimeSceneId = sceneSelect.value;
            if (previewState.mode() === 'runtime') applyRuntimePreview();
            updateRuntimeControls();
        });

        toolbar.mount('world-presentation', [
            free, runtime, walkMesh,
            walkProfile, createProfile, splitProfile, deleteProfile,
            sceneSelect, info
        ]);
        runtimeControls = {
            free, runtime, walkMesh, syncWalkMesh,
            walkProfile, createProfile, splitProfile, deleteProfile, syncWalkProfile,
            sceneSelect, info, projectionButtons, projectionDisabled: null
        };
        updateRuntimeControls();
        return true;
    }

    installSceneEditorHook();
    installRuntimeToolbar();
    root.addEventListener('load', () => {
        installSceneEditorHook();
        installRuntimeToolbar();
    }, { once: true });
    root.addEventListener('thestra-runtime-camera-viewport-ready', () => updateRuntimeControls());
    let initialCompositionMap = null;
    root.addEventListener('thestra-composition-preview-ready', () => {
        const composition = viewportApi()?.getCompositionPreview?.();
        if (!composition) { updateRuntimeControls(); return; }
        if (initialCompositionMap !== composition.mapId) {
            initialCompositionMap = composition.mapId;
            enterRuntimePreview();
        } else if (previewState.mode() === 'runtime') applyRuntimePreview();
        updateRuntimeControls();
    });
    root.addEventListener('thestra-world-presentation-changed', event => {
        updateRuntimeControls();
        if (previewState.mode() !== 'runtime') return;
        if (!event.detail || String(event.detail.sceneId) === String(runtimeSceneId)) applyRuntimePreview();
    });
    root.addEventListener('resize', fillRuntimeViewport);

    if (typeof root.loadActiveMap === 'function' && !root.__thestraWorldPresentationMapLoadWrapped) {
        const loadActiveMap = root.loadActiveMap;
        root.loadActiveMap = function () {
            if (previewState.mode() === 'runtime') leaveRuntimePreview();
            const result = loadActiveMap.apply(this, arguments);
            if (payload()?.maps?.[mapIndex()]?.id !== initialCompositionMap) initialCompositionMap = null;
            updateRuntimeControls();
            return result;
        };
        root.__thestraWorldPresentationMapLoadWrapped = true;
    }
}(typeof globalThis !== 'undefined' ? globalThis : this));
