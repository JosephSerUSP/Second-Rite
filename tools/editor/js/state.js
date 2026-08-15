
        // Same-origin when served by the editor server (works with the PORT
        // env override / autoPort — talking to a hardcoded 8080 can hit a
        // stale second instance); the fixed default only remains for file://.
        const API_URL = location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:8080';
        // The semantic Map inspector is an engine-owned host capability, kept
        // beside the existing authoritative renderable bridge. It receives a
        // transient snapshot and never writes authored data.
        const RUNTIME_API_URL = location.protocol.startsWith('http') ? '' : 'http://127.0.0.1:8080';
        let dbPayload = {};
        let isDirty = false;

        function setDirty(dirty) {
            isDirty = dirty;
            const saveBtns = [
                document.getElementById('tool-save-btn'),
                document.getElementById('status-save-btn'),
                document.getElementById('db-apply-btn')
            ];
            saveBtns.forEach(btn => {
                if (btn) btn.disabled = !dirty;
            });
        }

        // Project switching is an Electron-only host operation, but the
        // authoritative unsaved-data state lives here in the renderer. Expose
        // one read-only predicate so New/Open Project can warn before a relaunch
        // discards authored changes. Do not expose the mutable flag itself.
        window.thestraHasUnsavedProjectChanges = function() {
            return isDirty;
        };

        // --- GENERIC MODAL DIRTY-TRACKING / ESCAPE HANDLING ---
        // Each staged-edit modal (fields only commit to dbPayload on OK) sets its
        // own `*Dirty` flag to true via a delegated input/change listener, and
        // resets it to false when the modal opens. Close handlers accept an
        // optional `force` flag so the OK button can close without prompting.
        function confirmDiscard(message) {
            return confirm(message || 'You have unsaved changes. Discard them?');
        }

        function wireModalDirtyTracking(modalId, setDirtyFn) {
            const el = document.getElementById(modalId);
            if (!el) return;
            el.addEventListener('input', setDirtyFn);
            el.addEventListener('change', setDirtyFn);
        }

        // Closes whichever staged-edit modal is topmost (by declared z-index).
        // Registered once; each entry's close function already knows how to
        // prompt-and-discard if that modal has unsaved staged changes.
        const ESCAPE_MODAL_CLOSERS = [
            ['icon-picker-modal', () => typeof closeIconPicker === 'function' && closeIconPicker()],
            ['asset-picker-modal', () => typeof closeAssetPicker === 'function' && closeAssetPicker()],
            ['model-picker-modal', () => typeof closeModelPicker === 'function' && closeModelPicker()],
            ['cmd-modal', () => typeof closeCmdDialog === 'function' && closeCmdDialog()],
            ['cmd-selector-modal', () => typeof closeCmdSelectorModal === 'function' && closeCmdSelectorModal()],
            ['damage-popup-modal', () => typeof closeDamagePopupModal === 'function' && closeDamagePopupModal()],
            ['max-modal', () => typeof closeChangeMaxDialog === 'function' && closeChangeMaxDialog()],
            ['map-properties-modal', () => typeof closeMapPropertiesModal === 'function' && closeMapPropertiesModal()],
            ['event-modal', () => typeof closeEventModal === 'function' && closeEventModal()],
            ['tileset-studio-modal', () => typeof closeTilesetStudioModal === 'function' && closeTilesetStudioModal()],
            ['campaign-gen-modal', () => typeof closeCampaignGenModal === 'function' && closeCampaignGenModal()],
            ['studio-modal', () => typeof closeStudioModal === 'function' && closeStudioModal()],
            ['db-modal', () => typeof closeDatabaseModal === 'function' && closeDatabaseModal()],
            ['engine-modal', () => typeof closeEngineModal === 'function' && closeEngineModal()],
            ['toast-modal', () => typeof closeToast === 'function' && closeToast()]
        ];

        function modalIsVisible(el) {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            return el.classList.contains('active')
                || (style.display !== 'none' && style.visibility !== 'hidden');
        }

        // #521: interaction ownership is a Studio/editor concept, not a CSS
        // selector convention. Legacy DOM dialogs are adapted here through the
        // exact existing close registry; consumers such as the Map/3D surface
        // subscribe to semantic state instead of scanning `.modal*` topology.
        // New/docked/native hosts can participate explicitly through setBlocked
        // without adding any CSS vocabulary to renderer backends.
        const LEGACY_BLOCKING_INTERACTIONS = ESCAPE_MODAL_CLOSERS.map(([id]) => id);
        const explicitInteractionOwners = new Set();
        const interactionSubscribers = new Set();
        let interactionSnapshot = Object.freeze({ blocked: false, owners: Object.freeze([]) });

        function visibleLegacyInteractionOwners() {
            const owners = [];
            for (const id of LEGACY_BLOCKING_INTERACTIONS) {
                const el = document.getElementById(id);
                if (modalIsVisible(el)) owners.push(`dialog:${id}`);
            }
            return owners;
        }

        function computeInteractionSnapshot() {
            const owners = visibleLegacyInteractionOwners();
            explicitInteractionOwners.forEach(owner => owners.push(owner));
            owners.sort();
            return Object.freeze({
                blocked: owners.length > 0,
                owners: Object.freeze(owners),
            });
        }

        function interactionSnapshotsEqual(a, b) {
            if (!a || !b || a.blocked !== b.blocked || a.owners.length !== b.owners.length) return false;
            return a.owners.every((owner, index) => owner === b.owners[index]);
        }

        function refreshInteractionState() {
            const next = computeInteractionSnapshot();
            if (interactionSnapshotsEqual(interactionSnapshot, next)) return interactionSnapshot;
            interactionSnapshot = next;
            interactionSubscribers.forEach(listener => {
                try { listener(interactionSnapshot); } catch (error) { console.error(error); }
            });
            window.dispatchEvent(new CustomEvent('thestra-interaction-state-changed', {
                detail: interactionSnapshot,
            }));
            return interactionSnapshot;
        }

        window.ThestraInteractionState = Object.freeze({
            snapshot() { return interactionSnapshot; },
            isMapBlocked() { return interactionSnapshot.blocked; },
            subscribe(listener) {
                if (typeof listener !== 'function') return function () {};
                interactionSubscribers.add(listener);
                listener(interactionSnapshot);
                return function () { interactionSubscribers.delete(listener); };
            },
            setBlocked(ownerId, blocked) {
                const owner = String(ownerId || '').trim();
                if (!owner) throw new Error('Interaction owner id is required');
                if (blocked) explicitInteractionOwners.add(owner);
                else explicitInteractionOwners.delete(owner);
                return refreshInteractionState();
            },
            refresh: refreshInteractionState,
        });

        // This is a migration adapter for the existing DOM dialogs, not the
        // semantic API itself. It observes only the exact registered interaction
        // elements. The Map renderer no longer observes document.body or knows
        // how dialogs are styled/hosted.
        if (typeof MutationObserver === 'function') {
            const legacyInteractionObserver = new MutationObserver(refreshInteractionState);
            for (const id of LEGACY_BLOCKING_INTERACTIONS) {
                const el = document.getElementById(id);
                if (!el) continue;
                legacyInteractionObserver.observe(el, {
                    attributes: true,
                    attributeFilter: ['class', 'style', 'hidden'],
                });
            }
        }
        refreshInteractionState();

        function nativeHostModalId() {
            if (window.thestraSurfaceKind === 'database') return 'db-modal';
            return null;
        }

        // A Project relaunch must not silently bypass staged modal edits. Reuse
        // each modal's existing close contract: clean modals close immediately;
        // dirty staged modals prompt through their own local dirty flag. If the
        // user declines that prompt the modal remains visible and the Project
        // transition is canceled before the main Project dirty check runs.
        window.thestraPrepareForProjectSwitch = function() {
            for (const [id, closeFn] of ESCAPE_MODAL_CLOSERS) {
                const el = document.getElementById(id);
                if (!modalIsVisible(el)) continue;
                closeFn();
                if (modalIsVisible(el)) return false;
            }
            refreshInteractionState();
            return true;
        };

        // Native EditorSurfaces still host lightweight DOM interactions such as
        // pickers and command dialogs. Before the OS closes the host window,
        // give those interactions their ordinary close/discard contract while
        // exempting the host modal itself (e.g. #db-modal in Database surface
        // mode). A canceled child interaction cancels the native close too.
        window.thestraPrepareForSurfaceClose = function(hostModalId) {
            for (const [id, closeFn] of ESCAPE_MODAL_CLOSERS) {
                if (id === hostModalId) continue;
                const el = document.getElementById(id);
                if (!modalIsVisible(el)) continue;
                closeFn();
                if (modalIsVisible(el)) return false;
            }
            refreshInteractionState();
            return true;
        };

        window.addEventListener('keydown', (e) => {
            if (e.key !== 'Escape') return;
            // Also close active context menus if open
            const contextMenu = document.getElementById('map-context-menu');
            if (contextMenu && contextMenu.style.display !== 'none') {
                contextMenu.style.display = 'none';
                return;
            }

            // Escape dismisses interactions, not native EditorSurface windows.
            // The surface host itself is therefore skipped; Alt+F4/title-bar X
            // and explicit Cancel own the native close intent.
            const hostModalId = nativeHostModalId();
            for (const [id, closeFn] of ESCAPE_MODAL_CLOSERS) {
                if (id === hostModalId) continue;
                const el = document.getElementById(id);
                if (modalIsVisible(el)) {
                    closeFn();
                    refreshInteractionState();
                    return;
                }
            }
        });

        let editingMode = 'event'; // 'map' or 'event' — Event mode is the default: it's what you use most
        let activePaintTool = 'wall';
        let currentMapIndex = 0;
        let isMouseDown = false;

        let contextMenuMapIdx = null;

        function showMapContextMenu(e, mapIdx) {
            e.preventDefault();
            e.stopPropagation();
            contextMenuMapIdx = mapIdx;

            currentMapIndex = mapIdx;
            loadActiveMap();

            const menu = document.getElementById('map-context-menu');
            menu.style.left = e.clientX + 'px';
            menu.style.top = e.clientY + 'px';
            menu.style.display = 'block';
        }

        window.addEventListener('click', () => {
            ['map-context-menu', 'canvas-context-menu'].forEach(id => {
                const menu = document.getElementById(id);
                if (menu) menu.style.display = 'none';
            });
        });

        function handleMapContextMenuAction(action) {
            if (contextMenuMapIdx === null) return;
            currentMapIndex = contextMenuMapIdx;

            if (action === 'properties') {
                openMapProperties();
            } else if (action === 'new') {
                createNewMap();
            } else if (action === 'delete') {
                deleteMap();
            }
        }

        // Coordinates selected for Event edit
        let selectedEventX = 0;
        let selectedEventY = 0;

        let activeDbTab = 'units';
        let activeDbItemId = '';

        window.addEventListener('mousedown', () => { isMouseDown = true; });
        window.addEventListener('mouseup', () => { isMouseDown = false; });
