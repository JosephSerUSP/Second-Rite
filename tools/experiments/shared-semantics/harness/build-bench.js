'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');

const root = path.resolve(__dirname, '..');
const sourcePath = path.join(root, 'src', 'shared-semantics.ts');

function compilerScript(name) {
    if (name === 'tsc') return path.join(root, 'node_modules', 'typescript', 'bin', 'tsc');
    if (name === 'tstl') return path.join(root, 'node_modules', 'typescript-to-lua', 'dist', 'tstl.js');
    throw new Error(`unknown compiler ${name}`);
}

function timedRun(name, args) {
    const started = performance.now();
    const result = spawnSync(process.execPath, [compilerScript(name), ...args], {
        cwd: root,
        encoding: 'utf8'
    });
    const elapsed = performance.now() - started;
    if (result.status !== 0) {
        process.stdout.write(result.stdout || '');
        process.stderr.write(result.stderr || '');
        throw new Error(`${name} ${args.join(' ')} exited ${result.status}`);
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

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForMtimeAfter(filename, previous, timeoutMs) {
    const started = performance.now();
    while (performance.now() - started < timeoutMs) {
        if (fs.existsSync(filename)) {
            const current = fs.statSync(filename).mtimeMs;
            if (current > previous) return current;
        }
        await sleep(20);
    }
    throw new Error(`watch output did not update: ${path.relative(root, filename)}`);
}

async function watchOutput(name, config, outputFile, label) {
    const original = fs.readFileSync(sourcePath, 'utf8');
    const outputPath = path.join(root, outputFile);
    const baseline = fs.existsSync(outputPath) ? fs.statSync(outputPath).mtimeMs : 0;
    const child = spawn(process.execPath, [compilerScript(name), '-p', config, '--watch', '--preserveWatchOutput'], {
        cwd: root,
        stdio: ['ignore', 'pipe', 'pipe']
    });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk.toString(); });
    child.stderr.on('data', chunk => { output += chunk.toString(); });

    try {
        const initialMtime = await waitForMtimeAfter(outputPath, baseline, 15000);
        await sleep(100);
        const rebuildStarted = performance.now();
        fs.writeFileSync(sourcePath, original + '\n');
        await waitForMtimeAfter(outputPath, initialMtime, 15000);
        return { ms: performance.now() - rebuildStarted };
    } catch (error) {
        return { error: `${label}: ${error.message}`, output: output.slice(-4000) };
    } finally {
        fs.writeFileSync(sourcePath, original);
        child.kill();
        await Promise.race([
            new Promise(resolve => child.once('exit', resolve)),
            sleep(1000)
        ]);
    }
}

(async () => {
    fs.rmSync(path.join(root, 'generated'), { recursive: true, force: true });
    const jsColdMs = timedRun('tsc', ['-p', 'tsconfig.js.json']);
    const luaColdMs = timedRun('tstl', ['-p', 'tsconfig.lua.json']);
    const firstHash = hashTree(path.join(root, 'generated'));
    const jsRepeatMs = timedRun('tsc', ['-p', 'tsconfig.js.json']);
    const luaRepeatMs = timedRun('tstl', ['-p', 'tsconfig.lua.json']);
    const secondHash = hashTree(path.join(root, 'generated'));
    if (firstHash !== secondHash) throw new Error(`generated output is nondeterministic: ${firstHash} vs ${secondHash}`);

    const jsWatch = await watchOutput(
        'tsc', 'tsconfig.js.json', 'generated/js/shared-semantics.js', 'tsc watch');
    const luaWatch = await watchOutput(
        'tstl', 'tsconfig.lua.json', 'generated/lua/shared-semantics.lua', 'tstl watch');

    // Restore a clean build after the watch probes touched the source.
    timedRun('tsc', ['-p', 'tsconfig.js.json']);
    timedRun('tstl', ['-p', 'tsconfig.lua.json']);

    const generated = treeBytes(path.join(root, 'generated'));
    const nodeModules = treeBytes(path.join(root, 'node_modules'));
    const measurements = {
        js_cold_build_ms: jsColdMs,
        lua_cold_build_ms: luaColdMs,
        dual_cold_build_ms: jsColdMs + luaColdMs,
        js_repeat_build_ms: jsRepeatMs,
        lua_repeat_build_ms: luaRepeatMs,
        dual_repeat_build_ms: jsRepeatMs + luaRepeatMs,
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
