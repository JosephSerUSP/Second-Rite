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

    function applyCommittedRefresh(resourceNames, freshPayload, sourceSurface) {
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
        publishRefreshResult(sourceSurface, refreshed, blocked);
        return { refreshed, blocked };
    }

    async function refreshCommittedResources(payload) {
        const requested = payload && Array.isArray(payload.resources) ? payload.resources : [];
        if (requested.length === 0) return { refreshed: [], blocked: [] };

        await databaseBootReady();
        const res = await fetch(`${API_URL}/data`);
        if (!res.ok) throw new Error('Could not refresh committed Studio resources');
        const freshPayload = await res.json();
        return applyCommittedRefresh(requested, freshPayload, payload.sourceSurface);
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
            studio.announceResourceCommit(committed).catch(error => {
                console.error('Studio committed-resource announcement failed:', error);
            });
        }
        return remaining;
    };

    studio.onResourceCommit(queueCommittedRefresh);

    // Small semantic/test seams. These expose no Project authority: callers can
    // only observe when queued invalidations have finished and which resources
    // were deliberately held back because this renderer has local edits.
    window.thestraResourceRefreshIdle = function () { return refreshQueue; };
    window.thestraExternallyChangedResources = function () {
        return Array.from(externallyChangedResources);
    };
}());
