(function () {
    'use strict';

    const studio = window.thestraStudio;
    if (!studio || typeof studio.onResourceCommit !== 'function'
            || typeof studio.announceResourceCommit !== 'function') return;

    const externallyChangedResources = new Set();
    let refreshQueue = Promise.resolve();

    function databaseBootReady() {
        const state = window.thestraDatabaseBootState;
        if (state && state.done) return Promise.resolve();
        return new Promise(resolve => {
            window.addEventListener('thestra-database-boot-ready', resolve, { once: true });
        });
    }

    function locallyClean(name) {
        return dbResourcesEqual(dbPayload[name], dbSaveBaseline[name]);
    }

    function publishRefreshResult(sourceSurface, refreshed, blocked) {
        window.dispatchEvent(new CustomEvent('thestra-resources-refreshed', {
            detail: {
                sourceSurface: sourceSurface || null,
                refreshed: refreshed.slice(),
                blocked: blocked.slice(),
            },
        }));

        if (blocked.length > 0) {
            const labels = blocked.join(', ');
            console.warn(`Studio kept local edits for externally changed resource(s): ${labels}`);
            if (typeof showToast === 'function') {
                showToast([
                    `Another Studio window saved newer ${labels} data.`,
                    '',
                    'Your local edits were kept and were not overwritten.',
                    'Saving the same resource will be blocked as stale until you resolve/reload it.',
                ].join('\n'));
            }
        }
    }

    function applyCommittedRefresh(resourceNames, freshPayload) {
        const refreshed = [];
        const blocked = [];
        const freshVersions = freshPayload && freshPayload._fileVersions;

        for (const name of resourceNames) {
            if (!Object.prototype.hasOwnProperty.call(freshPayload || {}, name)) continue;

            // This check intentionally happens at APPLY time, after the async
            // /data request. If the user started editing while the fetch was in
            // flight, their working copy wins and keeps its old version token.
            if (!locallyClean(name)) {
                externallyChangedResources.add(name);
                blocked.push(name);
                continue;
            }

            dbPayload[name] = cloneDbResource(freshPayload[name]);
            captureDbSaveBaseline([name]);
            if (freshVersions && freshVersions[name] !== undefined) {
                if (!dbPayload._fileVersions) dbPayload._fileVersions = {};
                dbPayload._fileVersions[name] = freshVersions[name];
            }
            externallyChangedResources.delete(name);
            refreshed.push(name);
        }

        // An unrelated local edit must remain dirty after adopting a clean
        // sibling resource. Conversely, refreshing the final clean resource may
        // legitimately leave this renderer clean.
        setDirty(changedDbResourceNames().length > 0);
        return { refreshed, blocked };
    }

    async function refreshBulkResources(resourceNames) {
        if (resourceNames.length === 0) return { refreshed: [], blocked: [] };
        const res = await fetch(`${API_URL}/data`);
        if (!res.ok) throw new Error('Could not refresh committed Studio resources');
        const freshPayload = await res.json();
        return applyCommittedRefresh(resourceNames, freshPayload);
    }

    async function refreshTilesetRegistry(sourceSurface) {
        const res = await fetch(`${API_URL}/api/tilesets`);
        if (!res.ok) throw new Error('Could not refresh committed Tileset registry');
        const snapshot = await res.json();

        // Record-managed resources do not live in dbPayload and deliberately do
        // not participate in the bulk /data save surface. Publish their fresh
        // server snapshot semantically so interested sibling views can update
        // without transporting authored values through Electron IPC.
        window.dispatchEvent(new CustomEvent('thestra-tilesets-refreshed', {
            detail: {
                sourceSurface: sourceSurface || null,
                tilesets: Array.isArray(snapshot.tilesets) ? snapshot.tilesets : [],
                textures: Array.isArray(snapshot.textures) ? snapshot.textures : [],
                storage: snapshot.storage || null,
            },
        }));
        return { refreshed: ['tilesets'], blocked: [] };
    }

    async function refreshCommittedResources(payload) {
        const requested = payload && Array.isArray(payload.resources)
            ? Array.from(new Set(payload.resources.filter(name => typeof name === 'string' && name)))
            : [];
        if (requested.length === 0) return { refreshed: [], blocked: [] };

        await databaseBootReady();

        const editable = new Set(dbEditableResourceNames(dbPayload));
        const bulkRequested = requested.filter(name => editable.has(name));
        const tilesetRequested = requested.includes('tilesets');
        const unsupported = requested.filter(name => !editable.has(name) && name !== 'tilesets');
        if (unsupported.length > 0) {
            throw new Error(`No Studio refresh adapter for committed resource(s): ${unsupported.join(', ')}`);
        }

        const result = { refreshed: [], blocked: [] };
        const bulk = await refreshBulkResources(bulkRequested);
        result.refreshed.push(...bulk.refreshed);
        result.blocked.push(...bulk.blocked);

        if (tilesetRequested) {
            const tilesets = await refreshTilesetRegistry(payload.sourceSurface);
            result.refreshed.push(...tilesets.refreshed);
            result.blocked.push(...tilesets.blocked);
        }

        publishRefreshResult(payload.sourceSurface, result.refreshed, result.blocked);
        return result;
    }

    function queueCommittedRefresh(payload) {
        refreshQueue = refreshQueue
            .then(() => refreshCommittedResources(payload))
            .catch(error => {
                console.error('Studio committed-resource refresh failed:', error);
            });
        return refreshQueue;
    }

    // Hook the precise post-commit transaction seam. This runs even when the
    // user edits again while the save is in flight: the sent revision really was
    // committed and sibling renderers should learn about it. The sender itself
    // already accepted the server result and is not echoed by Electron main.
    const acceptSaveResult = acceptDbSaveResult;
    acceptDbSaveResult = function (sentPayload, result) {
        const remaining = acceptSaveResult(sentPayload, result);
        const committed = dbEditableResourceNames(sentPayload);
        if (committed.length > 0) {
            const versions = {};
            const committedVersions = result && result.versions;
            if (committedVersions && typeof committedVersions === 'object') {
                for (const name of committed) {
                    if (typeof committedVersions[name] === 'string' && committedVersions[name]) {
                        versions[name] = committedVersions[name];
                    }
                }
            }
            studio.announceResourceCommit(committed, versions).catch(error => {
                console.error('Studio committed-resource announcement failed:', error);
            });
        }
        return remaining;
    };

    studio.onResourceCommit(queueCommittedRefresh);
    if (typeof studio.onAssetInvalidation === 'function') {
        studio.onAssetInvalidation(payload => {
            const assets = payload && Array.isArray(payload.assets)
                ? Array.from(new Set(payload.assets.filter(value => typeof value === 'string' && value))).sort()
                : [];
            if (assets.length === 0) return;
            // Asset consumers decide whether this means a thumbnail refresh,
            // viewport material refresh, or later runtime recompilation. The
            // watcher carries identity only; it never carries file bytes/objects.
            window.dispatchEvent(new CustomEvent('thestra-assets-invalidated', {
                detail: { sourceSurface: 'external', assets },
            }));
        });
    }

    window.thestraResourceRefreshIdle = function () { return refreshQueue; };
    window.thestraExternallyChangedResources = function () {
        return Array.from(externallyChangedResources);
    };
}());
