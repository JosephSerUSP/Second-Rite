'use strict';
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const crypto = require('node:crypto');
const r = require('./resolve');
const root = path.resolve(__dirname, '../../..');
const read = name => JSON.parse(fs.readFileSync(path.join(__dirname, name), 'utf8'));
const write = (name, value) => { fs.mkdirSync(path.dirname(path.join(__dirname, name)), {recursive: true}); fs.writeFileSync(path.join(__dirname, name), r.dump(value)); };
// Git may check text fixtures out as CRLF on Windows while the deterministic
// resolver deliberately emits its canonical LF JSON. Compare that canonical
// byte sequence, not the local checkout's transport newline choice.
const readCanonical = name => fs.readFileSync(path.join(__dirname, name), 'utf8').replace(/\r\n/g, '\n');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const project = 'projects/hichaukitoden-game/';
const revision = '2fe51c223807fda0930799084d0ba2da5d143ad7';
function capture() {
    const sources = [];
    function blob(p) {
        const bytes = cp.execFileSync('git', ['show', `${revision}:${p}`], {cwd: root, maxBuffer: 32 * 1024 * 1024});
        sources.push({path: p, sha256: hash(bytes)}); return bytes;
    }
    const json = p => JSON.parse(blob(project + p));
    const map = json('data/maps/2.json'), system = json('data/system.json');
    // Exercise real carving/thresholds, excluding campaign event population and art injection.
    write('dungeon/source.json', {seed: 97531, map: {width: map.width, height: map.height,
        generationProfile: map.generationProfile, anchors: map.anchors, generateOpenings: true,
        tileset: 'spatial_probe_no_art', events: []}, dungeonPolicy: system.dungeon});
    const praca = json('data/maps/17.json');
    const env = 'assets/environments/st_maria_town/praca/';
    const metadata = json(env + 'environment.json');
    const mesh = name => {const p = project + env + name; return {path: p, sha256: hash(blob(p))};};
    const render = mesh(metadata.renderMesh), collision = mesh(metadata.collisionMesh);
    const obj = blob(project + env + metadata.collisionMesh).toString('utf8');
    blob(project + 'assets/authoring/environments/st_maria_praca_modelled.blend');
    write('st_maria/source.json', {render, collision, collisionObj: obj});
    const child = praca.events.find(e => e.instanceId === 'st-maria-praca-child');
    write('st_maria/gameplay.json', {events: [{id: child.instanceId, position: child.worldPosition, commands: child.commands || [], scriptId: child.scriptId}],
        camera: praca.traversal.camera, traversal: praca.traversal.lane,
        transfers: praca.events.filter(e => e.trigger === 'bump')});
    write('provenance.json', {revision, sources: [...new Map(sources.map(s => [s.path, s])).values()],
        note: 'Committed HEAD snapshot; pre-existing dirty town changes excluded. Source blend is hash-bound, never opened or modified. Runtime probe dependencies are separately hashed.'});
}
function probe(check = false) {
    const stageDir = path.join(root, 'out/spatial-1088-stage');
    require('../../../tools/ci/stage-project-gates').stageProjectGates({outputDir: stageDir});
    const input = read('dungeon/source.json');
    input.collisionObj = read('st_maria/source.json').collisionObj;
    input.output = path.join(stageDir, 'spatial-output.json').replaceAll('\\', '/');
    fs.writeFileSync(path.join(stageDir, 'spatial-input.json'), r.dump(input));
    fs.copyFileSync(path.join(__dirname, 'runtime-probe.lua'), path.join(stageDir, 'main.lua'));
    cp.execFileSync(process.env.LOVEC || 'C:/Program Files/LOVE/lovec.exe', [stageDir], {cwd: root, stdio: 'inherit', timeout: 120000});
    const result = JSON.parse(fs.readFileSync(input.output));
    if (check) require('node:assert/strict').equal(r.dump(result), r.dump(read('runtime-evidence.json')), 'live runtime evidence drift');
    else write('runtime-evidence.json', result);
    const dependencies = ['runtime/engine/exploration.lua', 'runtime/engine/tileset_resolver.lua',
        'runtime/engine/geometry/model.lua', 'runtime/presentation/obj_model.lua', 'runtime/presentation/world_camera.lua'];
    const provenance = {dependencies: dependencies.map(p => ({path: p, sha256: hash(fs.readFileSync(path.join(root, p)))})),
        note: 'Real LOVE generator, OBJ parser, and WorldCamera; minimal no-art dungeon source. Not a rendered/playable proof.'};
    if (check) require('node:assert/strict').deepEqual(provenance, read('runtime-provenance.json'), 'runtime dependency drift');
    else write('runtime-provenance.json', provenance);
}
function products() {
    const evidence = read('runtime-evidence.json');
    const result = {
        dungeon: r.dungeon(evidence.dungeon),
        st_maria: r.stMaria({...read('st_maria/source.json'), collisionVertices: evidence.collisionVertices}),
        tactics: r.tactics(read('tactics/source.json')),
        metroidvania: r.metroidvania(read('metroidvania/source.json')),
    };
    const files = {};
    for (const [name, value] of Object.entries(result)) {
        r.validate(value.physical);
        files[`${name}/resolved_spatial.json`] = value.physical;
        if (value.structure) files[`${name}/resolved_structure.json`] = value.structure;
        const gameplay = read(`${name}/gameplay.json`);
        if (name === 'metroidvania') require('node:assert/strict').equal(gameplay.camera.profile, evidence.camera.profile, 'camera policy needs a matching runtime probe');
        files[`${name}/resolved_view.json`] = {events: r.placeEvents(value.physical, gameplay.events || []),
            ...(name === 'metroidvania' ? {camera: evidence.camera} : {})};
    }
    files['tactics/resolved_moves.json'] = r.tacticalMoves(result.tactics.structure, read('tactics/gameplay.json').movement);
    return files;
}
if (require.main === module) {
    const args = process.argv.slice(2);
    for (const a of args) if (!['--capture', '--probe', '--check'].includes(a)) throw Error(`Unknown argument ${a}`);
    if (args.includes('--capture') && args.includes('--check')) throw Error('--capture cannot be combined with --check');
    if (args.includes('--capture')) capture();
    if (args.includes('--probe')) probe(args.includes('--check'));
    for (const [name, value] of Object.entries(products())) {
        if (args.includes('--check')) require('node:assert/strict').equal(readCanonical(name), r.dump(value), `${name} drift`);
        else write(name, value);
    }
    console.log('SPATIAL FIXTURES OK');
}
module.exports = {products, read};
