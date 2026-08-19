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
// #701 keeps that authority bound to the explicit runtime root rather than the
// repository/install container. The generic worker stays injectable for tests;
// this production wrapper supplies the semantic roots it owns.

const path = require('path');
const semanticRoots = require('../../tools/semantic-roots');
const projectRootAuthority = require('./project-root');
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
    return mapId;
}

function requestWithKind(request, kind) {
    const copy = Object.assign({}, request || {});
    Object.defineProperty(copy, ROUTE_KIND, { value: kind, enumerable: false });
    return copy;
}

function routeKind(request) {
    return request && request[ROUTE_KIND] === INSPECTION_KIND ? INSPECTION_KIND : RENDERABLE_KIND;
}

function defaultRequestArgs(request, staged, route) {
    const kind = routeKind(request);
    return [staged.stageDir, kind, String(validateMapId(request))];
}

function defaultParseResponse(payload, request) {
    const kind = routeKind(request);
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
        throw new Error(`Map ${kind} authority returned a non-object payload`);
    }
    return payload;
}

function createRuntimeMapAuthorityWorker(options = {}) {
    const installRoot = path.resolve(options.installRoot || projectRootAuthority.INSTALL_ROOT);
    const roots = semanticRoots.resolveInstallationRoots({
        installRoot,
        runtimeRoot: options.runtimeRoot,
        rtpRoot: options.rtpRoot,
        env: options.env || process.env,
    });
    const projectRoot = path.resolve(options.projectRoot || projectRootAuthority.PROJECT_ROOT);
    const createWorker = options.createWorker || createRuntimeRenderableWorker;
    const worker = createWorker(Object.assign({}, options, {
        installRoot: roots.installRoot,
        runtimeRoot: roots.runtimeRoot,
        rtpRoot: roots.rtpRoot,
        projectRoot,
        workerMain: options.workerMain || MAP_AUTHORITY_MAIN,
        requestArgs: options.requestArgs || defaultRequestArgs,
        parseResponse: options.parseResponse || defaultParseResponse,
        maxOutputBytes: options.maxOutputBytes || Math.max(
            Number(options.renderableMaxOutputBytes) || 0,
            Number(options.inspectionMaxOutputBytes) || DEFAULT_INSPECTION_MAX_BYTES,
        ),
    }));

    return {
        renderable(request) {
            return worker.compile(requestWithKind(request, RENDERABLE_KIND));
        },
        inspection(request) {
            return worker.compile(requestWithKind(request, INSPECTION_KIND));
        },
        close() {
            return worker.close();
        },
        getState() {
            return worker.getState();
        },
        _worker: worker,
    };
}

module.exports = {
    DEFAULT_INSPECTION_MAX_BYTES,
    INSPECTION_KIND,
    MAP_AUTHORITY_MAIN,
    RENDERABLE_KIND,
    createRuntimeMapAuthorityWorker,
    defaultParseResponse,
    defaultRequestArgs,
    requestWithKind,
    routeKind,
};
