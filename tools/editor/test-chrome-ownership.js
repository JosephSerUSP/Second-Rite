'use strict';

// #237: the editor's own chrome must come from the editor, and authored game
// content must come from the opened project. Both halves matter:
//
//   * chrome resolving through the project means opening a project that
//     happens not to ship an icon sheet costs you the editor's toolbar;
//   * the editor substituting its own copy for a MISSING game asset is worse
//     -- the author is then looking at a picture their game cannot draw, and
//     the gap only surfaces after export.
//
// The audit behind this gate found the chrome already clean, which is exactly
// when a gate is worth writing: it costs nothing today and catches the first
// url('/assets/...') someone adds to the editor's stylesheet.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const test = require('node:test');

// Model presentation is another editor-side asset boundary. Keep parser,
// HTTP inventory/serving, and shell-integration contracts inside an editor
// suite CI already executes; standalone tests that are never invoked are not
// protection.
require('./tests/test-model-picker.js');
require('./tests/test-model-server.js');
require('./tests/test-model-picker-integration.js');

const EDITOR_DIR = __dirname;
const INDEX = path.join(EDITOR_DIR, 'index.html');

function readEditorSources() {
    const files = [INDEX];
    const jsDir = path.join(EDITOR_DIR, 'js');
    for (const name of fs.readdirSync(jsDir)) {
        if (name.endsWith('.js')) files.push(path.join(jsDir, name));
    }
    return files.map(file => ({ file: path.relative(EDITOR_DIR, file), source: fs.readFileSync(file, 'utf8') }));
}

test('editor chrome is served from the editor, never the opened project', () => {
    const violations = [];
    for (const { file, source } of readEditorSources()) {
        // CSS backgrounds and <img src> in the editor's own shell are chrome.
        // A project path here is the coupling this gate exists to stop.
        for (const match of source.matchAll(/url\(\s*['"]?([^'")]+)['"]?\s*\)/g)) {
            const ref = match[1];
            if (/^(data:|https?:|#)/.test(ref)) continue;
            // Template literals build project-content previews at runtime;
            // those are legitimate and are covered by the next test.
            if (ref.includes('${')) continue;
            if (/(^|\/)assets\//.test(ref) || ref.startsWith('/assets')) {
                violations.push(`${file}: url(${ref})`);
            }
        }
    }
    assert.deepEqual(violations, [],
        'editor chrome resolved through the opened project:\n    ' + violations.join('\n    '));
});

test('the editor ships the chrome resources it references', () => {
    const source = fs.readFileSync(INDEX, 'utf8');
    const refs = new Set();
    for (const match of source.matchAll(/url\(\s*['"]?([^'")]+)['"]?\s*\)/g)) {
        const ref = match[1];
        if (/^(data:|https?:|#)/.test(ref) || ref.includes('${')) continue;
        refs.add(ref);
    }
    assert.ok(refs.size > 0, 'found no chrome resources at all -- the scanner is not looking where it thinks');
    for (const ref of refs) {
        const resolved = path.resolve(EDITOR_DIR, ref.replace(/^\//, ''));
        assert.ok(fs.existsSync(resolved), `editor chrome resource is missing from the editor: ${ref}`);
        assert.ok(resolved.startsWith(EDITOR_DIR + path.sep),
            `editor chrome resource resolves outside the editor: ${ref}`);
    }
});

// The other direction. A missing project asset must stay missing rather than
// borrowing an editor copy, so the renderer needs a distinct failed state --
// not just "not loaded yet", which would wait forever on an image that is
// never coming.
test('a missing project iconset is a visible state, not a silent one', () => {
    const source = fs.readFileSync(path.join(EDITOR_DIR, 'js', 'icon-renderer.js'), 'utf8');
    assert.ok(/iconsetFailed/.test(source), 'renderer has no failed state distinct from "still loading"');

    // Assert against the extracted handler rather than a character window into
    // the whole file: a window silently depends on comment length, and a
    // whole-file assertion prints the whole file when it fails.
    const onerror = /img\.onerror\s*=\s*\([^)]*\)\s*=>\s*\{([\s\S]*?)\n {4}\};/.exec(source);
    assert.ok(onerror, 'could not find the iconset onerror handler');
    const handler = onerror[1];
    assert.ok(/iconsetFailed = true/.test(handler), 'a failed iconset load must record the failure');
    assert.ok(/pendingCallbacks\.splice/.test(handler),
        'callers waiting on readiness must be released when the load fails');
    assert.ok(/drawMissingIconset/.test(source), 'no missing-state rendering exists');
    // ...and it must not be an editor-owned picture standing in for game art.
    const missing = /function drawMissingIconset[\s\S]*?\n}/.exec(source);
    assert.ok(missing, 'drawMissingIconset not found');
    assert.doesNotMatch(missing[0], /Assets\/|iconset\.png|drawImage/,
        'the missing state must be drawn, not substituted from an editor image');
});

// Negative control: the chrome scanner must actually flag a project reference,
// or it would pass just as happily on a real violation.
test('the chrome scanner flags a planted project reference (negative control)', () => {
    const planted = "body { background-image: url('/assets/system/iconset.png'); }";
    const hits = [];
    for (const match of planted.matchAll(/url\(\s*['"]?([^'")]+)['"]?\s*\)/g)) {
        const ref = match[1];
        if (/(^|\/)assets\//.test(ref) || ref.startsWith('/assets')) hits.push(ref);
    }
    assert.deepEqual(hits, ['/assets/system/iconset.png']);
});
