'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');

const root = path.resolve(__dirname, '..');
const sourcePath = path.join(root, 'src', 'shared-semantics.ts');

function bin(name) {
    return path.join(root, 'node_modules', '.bin', process.platform === 'win32' ? `${name}.cmd` : name);
}

function timedRun(command, args) {
    const started = performance.now();
    const result = spawnSync(command, args, { cwd: root, encoding: 'utf8', shell: process.platform === 'win32' });
    const elapsed = performance.now() - started;
    if (result.status !== 0) {
        process.stdout.write(result.stdout || '');
        process.stderr.write(result.stderr || '');
        throw new Error(`${command} ${args.join(' ')} exited ${result.status}`);
    }
    return elapsed;
}

function hashTree(directory) {
    const hash = crypto.createHash('sha256');
    const files = [];
    function walk(current) {
        for (const entry of fs.readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
            const full = path.join(current, entry.name);
            if (entry.isDirectory()) walk(full);
            else files.push(full);
        }
    }
    walk(directory);
    for (const file of files) {
        hash.update(path.relative(directory, file).replaceAll('\\', '/'));
        hash.update(fs.readFileSync(file));
    }
    return hash.digest('hex');
}

function treeBytes(directory) {
    let bytes = 0;
    let files = 0;
    function walk(current) {
        for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
            const full = path.join(current, entry.name);
            if (entry.isDirectory()) walk(full);
            else { bytes += fs.statSync(full).size; files++; }
        }
    }
    walk(directory);
    return { bytes, files };
}

function packageCount(directory) {
    let count = 0;
    function walk(current) {
        for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
            if (!entry.isDirectory()) continue;
            const full = path.join(current, entry.name);
            if (fs.existsSync(path.join(full, 'package.json'))) count++;
            if (entry.name !== '.bin') walk(full);
        }
    }
    walk(directory);
    return count;
}

function watchMarker(name, args, label) {
    return new Promise(resolve => {
        const original = fs.readFileSync(sourcePath, 'utf8');
        const child = spawn(bin(name), args, {
            cwd: root,
            shell: process.platform === 'win32',
            stdio: ['ignore', 'pipe', 'pipe']
        });
        let text = '';
        let initialSeen = false;
        let rebuildStarted = 0;
        let settled = false;
        const timeout = setTimeout(() => finish({ error: `${label} watch marker timeout`, output: text.slice(-4000) }), 45000);

        function finish(value) {
            if (settled) return;
            settled = true;
            clearTimeout(timeout);
            try { fs.writeFileSync(sourcePath, original); } catch {}
            try { child.kill(); } catch {}
            resolve(value);
        }

        function consume(chunk) {
            text += chunk.toString();
            const marker = /Found 0 errors\. Watching for file changes\./g;
            const matches = text.match(marker) || [];
            if (!initialSeen && matches.length >= 1) {
                initialSeen = true;
                setTimeout(() => {
                    rebuildStarted = performance.now();
                    fs.writeFileSync(sourcePath, original + '\n');
                }, 150);
            } else if (initialSeen && matches.length >= 2 && rebuildStarted) {
                finish({ ms: performance.now() - rebuildStarted });
            }
        }
        child.stdout.on('data', consume);
        child.stderr.on('data', consume);
        child.on('exit', code => {
            if (!settled) finish({ error: `${label} watch exited ${code}`, output: text.slice(-4000) });
        });
    });
}

(async () => {
    fs.rmSync(path.join(root, 'generated'), { recursive: true, force: true });
    const jsColdMs = timedRun(bin('tsc'), ['-p', 'tsconfig.js.json']);
    const luaColdMs = timedRun(bin('tstl'), ['-p', 'tsconfig.lua.json']);
    const firstHash = hashTree(path.join(root, 'generated'));
    const jsWarmMs = timedRun(bin('tsc'), ['-p', 'tsconfig.js.json']);
    const luaWarmMs = timedRun(bin('tstl'), ['-p', 'tsconfig.lua.json']);
    const secondHash = hashTree(path.join(root, 'generated'));
    if (firstHash !== secondHash) throw new Error(`generated output is nondeterministic: ${firstHash} vs ${secondHash}`);

    const jsWatch = await watchMarker('tsc', ['-p', 'tsconfig.js.json', '--watch', '--preserveWatchOutput'], 'tsc');
    const luaWatch = await watchMarker('tstl', ['-p', 'tsconfig.lua.json', '--watch', '--preserveWatchOutput'], 'tstl');

    // Restore a clean build after the watch probes touched the source timestamp/content.
    timedRun(bin('tsc'), ['-p', 'tsconfig.js.json']);
    timedRun(bin('tstl'), ['-p', 'tsconfig.lua.json']);

    const generated = treeBytes(path.join(root, 'generated'));
    const nodeModules = treeBytes(path.join(root, 'node_modules'));
    const measurements = {
        js_cold_build_ms: jsColdMs,
        lua_cold_build_ms: luaColdMs,
        dual_cold_build_ms: jsColdMs + luaColdMs,
        js_repeat_build_ms: jsWarmMs,
        lua_repeat_build_ms: luaWarmMs,
        dual_repeat_build_ms: jsWarmMs + luaWarmMs,
        js_watch_rebuild: jsWatch,
        lua_watch_rebuild: luaWatch,
        deterministic_generated_sha256: secondHash,
        generated_bytes: generated.bytes,
        generated_files: generated.files,
        node_modules_bytes: nodeModules.bytes,
        node_modules_files: nodeModules.files,
        installed_package_directories: packageCount(path.join(root, 'node_modules')),
        source_bytes: fs.statSync(sourcePath).size
    };
    console.log('BUILD BENCH OK');
    console.log('MEASURE_BUILD ' + JSON.stringify(measurements));
})().catch(error => {
    console.error(error && error.stack || error);
    process.exitCode = 1;
});
