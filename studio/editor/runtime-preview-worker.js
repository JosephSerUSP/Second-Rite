'use strict';

// Persistent preview authority for Thestra Studio.
//
// Scene, window, font, fog and animation previews each cost one cold LÖVE
// subprocess per request -- measured at 3-9 s. Unlike sprite metadata (#794),
// these cannot move to shared executable semantics: every one of them renders
// pixels through love.graphics and returns a base64 PNG. They are the
// runtime-bound class, and #754's report is explicit that persistence is the
// right answer for exactly that class.
//
// #701 binds the worker to the explicit Thestra runtime root; installation and
// Project roots remain separate inputs to staging.

const { createRuntimeRenderableWorker } = require('./runtime-renderable-worker');
const semanticRoots = require('../semantic-roots');
const projectRootAuthority = require('./project-root');
const path = require('path');

const PREVIEW_MAIN = path.join(__dirname, 'runtime-preview-worker-main.lua');

// Each command keeps the envelope its cold `lovec . <command>` run printed, so
// the Node-side parsers, the cold fallback and any reference capture all stay
// byte-comparable against the warm path.
const COMMANDS = Object.freeze({
    'preview-scene': { begin: 'PREVIEW BEGIN', end: 'PREVIEW END' },
    'preview-window': { begin: 'PREVIEW BEGIN', end: 'PREVIEW END' },
    'preview-font': { begin: 'PREVIEW BEGIN', end: 'PREVIEW END' },
    'preview-fog': { begin: 'PREVIEW BEGIN', end: 'PREVIEW END' },
    'preview-anim': { begin: 'PREVIEW BEGIN', end: 'PREVIEW END' },
});

function envelopeFor(command) {
    const envelope = COMMANDS[command];
    if (!envelope) throw new Error(`unknown preview command: ${command}`);
    return envelope;
}

function extractEnvelope(text, envelope) {
    const body = String(text || '');
    const begin = body.indexOf(envelope.begin);
    const end = body.indexOf(envelope.end);
    if (begin === -1 || end === -1 || end < begin) {
        throw new Error('preview produced no output');
    }
    return body.slice(begin + envelope.begin.length, end).trim();
}

function createRuntimePreviewWorker(options) {
    options = options || {};
    const roots = semanticRoots.resolveInstallationRoots({
        installRoot: options.installRoot || projectRootAuthority.INSTALL_ROOT,
        runtimeRoot: options.runtimeRoot,
        rtpRoot: options.rtpRoot,
        env: {},
    });

    // The worker prints whatever envelope the command uses; which one is known
    // per request, so parsing is deferred to the caller rather than fixed at
    // construction the way the renderable worker can afford to do.
    const worker = createRuntimeRenderableWorker(Object.assign({}, options, {
        installRoot: roots.installRoot,
        runtimeRoot: roots.runtimeRoot,
        rtpRoot: roots.rtpRoot,
        workerMain: options.workerMain || PREVIEW_MAIN,
        parseOutput: text => text,
        routeOf: request => {
            const command = request && request.command;
            if (!command || typeof command !== 'string') {
                throw new Error('preview worker request needs a command');
            }
            if (/[\t\r\n]/.test(command)) {
                throw new Error('preview command cannot contain framing characters');
            }
            envelopeFor(command);
            return command;
        },
    }));

    async function run(command, payload) {
        const envelope = envelopeFor(command);
        // `command` rides the protocol route field; the payload is the request
        // file the worker reads, so argument shapes stay JSON rather than
        // becoming positional command-line strings.
        const request = Object.assign({ command }, payload || {});
        const text = await worker.compile(request);
        const json = extractEnvelope(text, envelope);
        let parsed;
        try {
            parsed = JSON.parse(json);
        } catch (error) {
            throw new Error('preview output was not valid JSON: ' + error.message);
        }
        return parsed;
    }

    return {
        run,
        invalidate: reason => worker.invalidate(reason),
        shutdown: () => worker.shutdown(),
        shutdownSync: () => worker.shutdownSync(),
        state: () => worker.state(),
    };
}

module.exports = {
    createRuntimePreviewWorker,
    COMMANDS,
    PREVIEW_MAIN,
};
