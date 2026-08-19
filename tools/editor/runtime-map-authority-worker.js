'use strict';

// Unified persistent Map authority for Thestra Studio.
//
// #754 established the revision-scoped staged LÖVE worker for compact Map
// renderables. #739 found that Map Inspection still cold-staged/cold-booted a
// separate LÖVE process and could cross the bridge's 60s budget during G6 even
// while renderable authority was healthy. Both operations are runtime-owned
// Map facts over the same Project/runtime/RTP revision, so they share one
// generation here instead of maintaining two process lifecycles.
//
// The generic worker remains unchanged. This wrapper supplies a typed route and
// parses each operation's existing cold-process envelope after the worker has
// completed the request. A Symbol carries the internal route kind so the
// transient JSON request seen by the runtime is byte-for-byte the ordinary
// authored request shape rather than a Studio-private protocol object.

const path = require('path');
const { createRuntimeRenderableWorker } = require('./runtime-renderable-worker');

const MAP_AUTHORITY_MAIN = path.join(__dirname, 'runtime-map-authority-worker-main.lua');
const ROUTE_KIND = Symbol('thestraMapAuthorityRouteKind');
const RENDERABLE_KIND = 'renderable';
const INSPECTION_KIND = 'inspection';
const DEFAULT_INSPECTION_MAX_BYTES = 16 * 1024 * 1024;

function validateMapId(request) {
    const mapId = request && request.map && request.map.id;
    if (mapId === undefined || mapId === null || mapId === '') {
        throw new Error('Map authority request needs a map id');
    }
    const text = String(mapId);
    if (Buffer.byteLength(text, 'utf8') > 256) {
        throw new Error('Map authority map id is too large for the worker protocol');
    }
    if (/[\t\r\n]/.test(text)) {
        throw new Error('Map authority map id cannot contain framing characters');
    }
    return text;
}

function routedRequest(request, kind) {
    const value = Object.assign({}, request);
    Object.defineProperty(value, ROUTE_KIND, {
        value: kind,
        enumerable: false,
        configurable: false,
        writable: false,
    });
    return value;
}

function createRuntimeMapAuthorityWorker(options = {}) {
    const parseRenderableOutput = options.parseRenderableOutput;
    const parseInspectionOutput = options.parseInspectionOutput;
    if (typeof parseRenderableOutput !== 'function') {
        throw new Error('Map authority worker requires parseRenderableOutput');
    }
    if (typeof parseInspectionOutput !== 'function') {
        throw new Error('Map authority worker requires parseInspectionOutput');
    }
    const inspectionMaxBytes = options.inspectionMaxBytes || DEFAULT_INSPECTION_MAX_BYTES;

    const worker = createRuntimeRenderableWorker(Object.assign({}, options, {
        workerMain: options.workerMain || MAP_AUTHORITY_MAIN,
        // Route-specific parsing happens after compile(), because the generic
        // worker deliberately has one parser per generation owner.
        parseOutput: text => text,
        routeOf: request => {
            const kind = request && request[ROUTE_KIND];
            if (kind !== RENDERABLE_KIND && kind !== INSPECTION_KIND) {
                throw new Error('Map authority request is missing its route kind');
            }
            return `${kind}:${validateMapId(request)}`;
        },
    }));

    async function compileKind(kind, request) {
        const routed = routedRequest(request, kind);
        const text = await worker.compile(routed);
        if (kind === INSPECTION_KIND && Buffer.byteLength(String(text || ''), 'utf8') > inspectionMaxBytes) {
            worker.invalidate('Map inspection exceeded its response contract');
            throw new Error(
                `Map inspection produced more than ${(inspectionMaxBytes / (1024 * 1024)).toFixed(1)} MiB of output`
            );
        }
        try {
            return kind === INSPECTION_KIND
                ? parseInspectionOutput(text)
                : parseRenderableOutput(text);
        } catch (error) {
            // A complete worker frame with a malformed/missing semantic envelope
            // is not a reusable authority generation. Rebuild before answering
            // another request rather than allowing hidden process state to mask
            // a protocol/runtime corruption.
            worker.invalidate(`Map ${kind} output parser rejected the runtime response`);
            throw error;
        }
    }

    return {
        // Keep compile() as the renderable-facing API so existing server/test
        // injection contracts do not need a new name.
        compile(request) {
            return compileKind(RENDERABLE_KIND, request);
        },
        compileInspection(request) {
            return compileKind(INSPECTION_KIND, request);
        },
        invalidate: reason => worker.invalidate(reason),
        shutdown: () => worker.shutdown(),
        shutdownSync: () => worker.shutdownSync(),
        state: () => worker.state(),
    };
}

module.exports = {
    MAP_AUTHORITY_MAIN,
    RENDERABLE_KIND,
    INSPECTION_KIND,
    DEFAULT_INSPECTION_MAX_BYTES,
    createRuntimeMapAuthorityWorker,
};
