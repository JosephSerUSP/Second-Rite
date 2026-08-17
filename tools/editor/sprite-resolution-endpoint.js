'use strict';

const fs = require('fs');
const path = require('path');
const { SpriteResolutionCache } = require('./sprite-resolution-cache');

function createSpriteResolutionEndpoint(options) {
    options = options || {};
    const projectRoot = options.projectRoot && path.resolve(options.projectRoot);
    if (!projectRoot) throw new Error('projectRoot is required');
    if (typeof options.runtimeResolver !== 'function') throw new Error('runtimeResolver is required');

    const fsImpl = options.fs || fs;
    const cache = options.cache || new SpriteResolutionCache({
        projectRoot,
        fs: fsImpl,
        runtimeAuthorityPath: options.runtimeAuthorityPath,
    });

    const resolveWithinProject = (...segments) => {
        const target = path.resolve(projectRoot, ...segments);
        if (target !== projectRoot && !target.startsWith(projectRoot + path.sep)) {
            throw new Error('path outside project');
        }
        return target;
    };

    const handler = async (req, res) => {
        const respond = (status, payload) => {
            res.writeHead(status, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(payload));
        };

        try {
            const parsedUrl = new URL(req.url, 'http://127.0.0.1:8080');
            const spriteKey = parsedUrl.searchParams.get('key');
            const rawPath = parsedUrl.searchParams.get('path');
            let spec;

            if (spriteKey !== null) {
                if (spriteKey.length > 512) {
                    respond(400, { error: 'sprite key is too long' });
                    return;
                }
                spec = { key: spriteKey };
            } else if (rawPath !== null) {
                const normalized = rawPath.replace(/\\/g, '/');
                if (!/^assets\/(smallBattlers|sprites|system)\/[^/]+$/i.test(normalized)) {
                    respond(400, { error: 'sprite path must name one file in a runtime sprite directory' });
                    return;
                }
                let absolute;
                try { absolute = resolveWithinProject(...normalized.split('/')); } catch (e) { absolute = null; }
                if (!absolute || !fsImpl.existsSync(absolute) || !fsImpl.statSync(absolute).isFile()) {
                    respond(404, { error: 'sprite file no longer exists' });
                    return;
                }
                spec = { path: normalized };
            } else {
                respond(400, { error: 'sprite-resolution requires key or path' });
                return;
            }

            const payload = await cache.resolve(spec, options.runtimeResolver);
            respond(payload && payload.error ? 400 : 200, payload);
        } catch (error) {
            respond(500, { error: String(error && (error.message || error) || error) });
        }
    };

    handler.cache = cache;
    return handler;
}

module.exports = {
    createSpriteResolutionEndpoint,
};
