
        // #299: old Studio markup still contains the retired Campaign selector
        // while #369 migrates the generator UI. Remove that chrome rather than
        // leaving a dead selector that suggests Project data can be redirected.
        document.addEventListener('DOMContentLoaded', () => {
            const picker = document.getElementById('campaign-picker');
            if (picker) {
                const label = document.querySelector('label[for="campaign-picker"]');
                if (label) label.remove();
                picker.remove();
            }
        });

        // #521: the opened Project's committed authority remains the editor
        // server/authored-storage boundary. Each renderer owns only a working
        // transaction. Keep a baseline of what THIS renderer loaded/committed so
        // save can send only resources it actually changed; /save already
        // version-checks and writes only resources present in the request.
        // This is what lets future Map/Database/Animation renderer windows edit
        // unrelated resources without overwriting or falsely conflicting with
        // one another.
        let dbSaveBaseline = {};

        // Native EditorSurfaces need a semantic readiness boundary, not the
        // browser's global loading spinner. This state means the real /data boot
        // attempt has completed and Studio has either initialized its editors or
        // surfaced the terminal offline state. The event + sticky state avoid a
        // race whether the Electron surface adapter arrives before or after the
        // async fetch completes.
        window.thestraDatabaseBootState = Object.freeze({ done: false, ok: false });

        function publishDatabaseBootReady(ok) {
            const state = Object.freeze({ done: true, ok: !!ok });
            window.thestraDatabaseBootState = state;
            window.dispatchEvent(new CustomEvent('thestra-database-boot-ready', { detail: state }));
        }

        function currentEditorSurface() {
            try {
                return new URLSearchParams(window.location.search || '').get('surface') || 'main';
            } catch (_) {
                return 'main';
            }
        }

        function cloneDbResource(value) {
            if (value === undefined) return undefined;
            return JSON.parse(JSON.stringify(value));
        }

        function dbEditableResourceNames(payload = dbPayload) {
            return Object.keys(payload || {}).filter(name => !name.startsWith('_'));
        }

        function dbResourcesEqual(a, b) {
            return JSON.stringify(a) === JSON.stringify(b);
        }

        function captureDbSaveBaseline(names) {
            const resourceNames = names || dbEditableResourceNames();
            resourceNames.forEach(name => {
                dbSaveBaseline[name] = cloneDbResource(dbPayload[name]);
            });
            // A fresh database load defines a new transaction universe. Drop
            // baselines for resources no longer exposed by authored storage.
            if (!names) {
                Object.keys(dbSaveBaseline).forEach(name => {
                    if (!resourceNames.includes(name)) delete dbSaveBaseline[name];
                });
            }
        }

        function changedDbResourceNames() {
            return dbEditableResourceNames().filter(name =>
                !dbResourcesEqual(dbPayload[name], dbSaveBaseline[name])
            );
        }

        function buildDbSavePayload(resourceNames) {
            const names = resourceNames || changedDbResourceNames();
            const payload = { _fileVersions: {} };
            names.forEach(name => {
                payload[name] = cloneDbResource(dbPayload[name]);
                const version = dbPayload._fileVersions && dbPayload._fileVersions[name];
                if (version === undefined || version === null) {
                    throw new Error(`Cannot save ${name}: missing authored-storage version. Reload Studio and try again.`);
                }
                payload._fileVersions[name] = version;
            });
            return payload;
        }

        function acceptDbSaveResult(sentPayload, result) {
            const committed = dbEditableResourceNames(sentPayload);
            committed.forEach(name => {
                // Baseline must advance to exactly what was sent, not whatever
                // the live form contains now: the user may have edited again
                // while the async save was in flight.
                dbSaveBaseline[name] = cloneDbResource(sentPayload[name]);
                if (result.versions && result.versions[name] !== undefined) {
                    if (!dbPayload._fileVersions) dbPayload._fileVersions = {};
                    // Do not adopt tokens for untouched resources. Another
                    // renderer may have committed one since our load; keeping
                    // our old token ensures a later edit conflicts instead of
                    // blessing a stale local value.
                    dbPayload._fileVersions[name] = result.versions[name];
                }
            });
            return changedDbResourceNames();
        }

        let databaseBootPromise = null;

        async function fetchDatabaseAttempt(retries = 3) {
            let dataLoaded = false;
            try {
                const res = await fetch(`${API_URL}/data`);
                if (!res.ok) throw new Error('Database server offline');
                dbPayload = await res.json();
                dataLoaded = true;
            } catch (err) {
                if (retries > 0) {
                    await new Promise(r => setTimeout(r, 600));
                    return fetchDatabaseAttempt(retries - 1);
                }
                console.error('Database fetch error:', err);
                document.getElementById('status-db').textContent = 'Database: Offline';
                showToast('Failed to connect to Second Rite dev server!\n\nVerify that the editor server is running.');
                publishDatabaseBootReady(false);
                return false;
            }

            if (dataLoaded) {
                try {
                    // A native Database EditorSurface is not a hidden copy of
                    // the Map workspace. Give it only the editor initialization
                    // it actually owns; the main Studio renderer keeps the full
                    // Map + Database + System boot.
                    if (currentEditorSurface() !== 'database') initMapEditor();
                    initDatabaseEditor();
                    initSystemTab();
                    document.getElementById('status-db').textContent = 'Database: Connected';
                } catch (guiErr) {
                    console.error('Error initializing editor UI after fetch:', guiErr);
                    document.getElementById('status-db').textContent = 'Database: Connected (UI Warning)';
                } finally {
                    // UI initialization is a view concern. If an editor helper
                    // materializes transient handles/defaults while mounting,
                    // they belong to this renderer's starting working copy and
                    // must not become an authored change merely because another
                    // resource is later saved.
                    captureDbSaveBaseline();
                    setDirty(false);
                    publishDatabaseBootReady(true);
                }
            }
            return true;
        }

        function fetchDatabase(retries = 3) {
            if (!databaseBootPromise) {
                databaseBootPromise = fetchDatabaseAttempt(retries);
            }
            return databaseBootPromise;
        }

        // Core authored data belongs to Studio boot, not to events.js reaching
        // the bottom of its top-level script. DOM readiness is guaranteed even
        // when an unrelated editor module throws while parsing/initializing, so
        // this keeps Database independently bootable. The historical events.js
        // call remains compatible and simply receives this same promise.
        document.addEventListener('DOMContentLoaded', () => {
            fetchDatabase();
        });

        function showToast(message) {
            document.getElementById('toast-text').textContent = message;
            document.getElementById('toast-modal').classList.add('active');
        }

        function closeToast() {
            document.getElementById('toast-modal').classList.remove('active');
        }

        function stripEmptyMeta(obj) {
            if (!obj || typeof obj !== 'object') return;
            if (Array.isArray(obj)) {
                obj.forEach(stripEmptyMeta);
                return;
            }
            if (obj.meta && typeof obj.meta === 'object' && Object.keys(obj.meta).length === 0) {
                delete obj.meta;
            }
            if (Array.isArray(obj.names) && obj.names.length === 0) {
                delete obj.names;
            }
            // Event pages (engine resolvePage): an empty list means "no pages",
            // so drop the key rather than churning maps.json with `pages: []`.
            if (Array.isArray(obj.pages) && obj.pages.length === 0) {
                delete obj.pages;
            }
            for (const key in obj) {
                if (Object.prototype.hasOwnProperty.call(obj, key) && typeof obj[key] === 'object' && obj[key] !== null) {
                    stripEmptyMeta(obj[key]);
                }
            }
        }

        // Track IDs (trk_xxx) are editor-only UI handles assigned in-memory by
        // the animation editor. They only need to persist when another track's
        // `parent` references them; otherwise they're random per-session noise
        // that churns the JSON on every save. Strip the unreferenced ones so the
        // on-disk file stays stable (no spurious GitHub diffs) while keeping
        // follow-track relationships intact.
        function stripOrphanTrackIds() {
            const anims = dbPayload && dbPayload.animations;
            if (!anims || typeof anims !== 'object') return;
            for (const key in anims) {
                const anim = anims[key];
                if (!anim || !Array.isArray(anim.tracks)) continue;
                const referenced = new Set();
                anim.tracks.forEach(t => {
                    if (t && typeof t.parent === 'string' && t.parent) referenced.add(t.parent);
                });
                anim.tracks.forEach(t => {
                    if (t && typeof t.id === 'string' && t.id.indexOf('trk_') === 0 && !referenced.has(t.id)) {
                        delete t.id;
                    }
                });
            }
        }

        async function saveData() {
            try {
                // Normalize only resources already diverged from this
                // renderer's baseline. Cleaning unrelated resources would turn
                // a scoped transaction back into a whole-Project write.
                let changed = changedDbResourceNames();
                changed.forEach(name => stripEmptyMeta(dbPayload[name]));
                if (changed.includes('animations')) stripOrphanTrackIds();
                changed = changedDbResourceNames();

                if (changed.length === 0) {
                    setDirty(false);
                    if (window.dbModalSnapshotHelper && typeof window.dbModalSnapshotHelper.capture === 'function') {
                        window.dbModalSnapshotHelper.capture();
                    }
                    return true;
                }

                const savePayload = buildDbSavePayload(changed);
                const res = await fetch(`${API_URL}/save`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(savePayload)
                });
                const result = await res.json();
                if (result.success) {
                    const stillChanged = acceptDbSaveResult(savePayload, result);
                    setDirty(stillChanged.length > 0);
                    validateSavedData();
                    // Fields inside the Database modal are live-bound. Refresh
                    // its discard snapshot only when no newer edit happened
                    // while the save request was in flight.
                    if (stillChanged.length === 0
                            && window.dbModalSnapshotHelper
                            && typeof window.dbModalSnapshotHelper.capture === 'function') {
                        window.dbModalSnapshotHelper.capture();
                    }
                    return stillChanged.length === 0;
                }

                showToast('Failed to save data: ' + result.message);
                return false;
            } catch (err) {
                console.error('saveData error:', err);
                showToast('Save failed: ' + (err.message || 'server offline'));
                return false;
            }
        }

        // Post-save integrity sweep: asks the server to run the engine's own
        // validator (`lovec . validate`) against what was just written and
        // surfaces any cross-reference/schema problems. Fire-and-forget so
        // saving never blocks on the ~2s engine boot; the save itself has
        // already succeeded when this runs.
        async function validateSavedData() {
            try {
                const res = await fetch(`${API_URL}/validate`);
                const result = await res.json();
                if (!result.ok) {
                    const problems = result.problems || ['unknown validation failure'];
                    document.getElementById('status-db').textContent =
                        `Database: Saved — ${problems.length} validation problem${problems.length === 1 ? '' : 's'}`;
                    showToast('Saved, but the engine validator found problems:\n\n' + problems.join('\n'));
                } else {
                    document.getElementById('status-db').textContent = 'Database: Saved ✓ validated';
                }
            } catch (err) {
                // Server went away between save and validate — the next
                // interaction will surface the offline state; stay quiet here.
            }
        }

        async function testPlay() {
            if (isDirty && confirm('Save database changes before starting Test Play?')) {
                await saveData();
            }
            try {
                const res = await fetch(`${API_URL}/play`, { method: 'POST' });
                const result = await res.json();
                if (!result.success) {
                    showToast('Failed to launch game: ' + result.message);
                }
            } catch (err) {
                showToast('Failed to start Test Play: ' + err.message);
            }
        }

        async function generateScreenshots() {
            const button = document.getElementById('tool-screenshot-btn');
            if (button) button.disabled = true;
            document.getElementById('status-db').textContent = 'Generating screenshots...';
            try {
                const res = await fetch(`${API_URL}/screenshots`, { method: 'POST' });
                const result = await res.json();
                if (!result.success) throw new Error(result.message || 'capture failed');
                document.getElementById('status-db').textContent =
                    `Screenshots: ${result.count} at ${result.width}x${result.height}`;
                showToast(`Generated ${result.count} screenshots in:\n${result.directory}`);
            } catch (err) {
                document.getElementById('status-db').textContent = 'Screenshot generation failed';
                showToast('Failed to generate screenshots: ' + err.message);
            } finally {
                if (button) button.disabled = false;
            }
        }

        window.addEventListener('keydown', (e) => {
            if (e.key === 'F5') {
                e.preventDefault();
                testPlay();
            }
        });
