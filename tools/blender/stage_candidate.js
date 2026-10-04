'use strict';
// Stage a candidate 3D room package onto an existing map, in a fresh runtime
// stage under out/ only. Nothing in the Project changes.
//
//   node tools/blender/stage_candidate.js --output out/<new-stage> \
//       --package out/<review>/<name> --map-id 22 \
//       [--template 28] [--npc <eventInstanceId>=<anchor>]...
//       [--lane <minY> <maxY>] [--track <centreY> <maxOffsetPx>]
//       [--camera '<json merged into the camera, e.g. {"yawDegrees":-14}>']
//       [--exit-direction away|toward|left|right]
//
// The target map keeps its own events and text; it borrows the template map's
// real-3D presentation -- traversal block (camera, lane), ceilingStyle and
// fog -- because a map that currently shows a 2D plate is tuned for that
// plate (map 22's "sky" ceiling paints a night sky around an interior). Template 28 is a
// Classic-width interior baked by export_room_environment.py, so its lane is
// the walkable span of any room built at interior.base_half_width_at().
//
// A room longer than the Classic width (exported with --span) scrolls: pass
// --lane for its walkable engine Y range and --track for the camera centre
// and how far, in projection pixels, the camera may move from it. For the
// map 28 camera that is (halfLength - 4.96 m) * 25.8 px/m; 16 m -> 78.
//
// --camera tries a different view of the same room: the JSON is merged into
// the template camera (nested objects merge key by key), so yaw, pitch, target
// or distance can be explored in the real runtime before any map data changes.
//
// The map's exit (its bump event with LOAD_MAP) moves to the package's
// exit_door anchor; each --npc event moves to its anchor. Other events are
// dropped from the staged map and listed in candidate.json.
//
// Then capture: python tools/blender/capture_environment.py
//   --game-root <stageDir printed below> --output out/<frames> --map-id <id>
//   --positions <engine lane Y...>
const fs = require('node:fs');
const path = require('node:path');
const {stageProjectGates} = require('../ci/stage-project-gates');

const root = path.resolve(__dirname, '../..');
const project = path.join(root, 'projects/hichaukitoden-game');

// Map fields that belong to the representation, not to the place.
const PRESENTATION = ['ceilingStyle', 'fog'];

function merge(target, patch) {
    for (const [key, value] of Object.entries(patch)) {
        if (value && typeof value === 'object' && !Array.isArray(value)
                && target[key] && typeof target[key] === 'object') merge(target[key], value);
        else target[key] = value;
    }
    return target;
}

function readMap(id) {
    return JSON.parse(fs.readFileSync(path.join(project, `data/maps/${id}.json`), 'utf8'));
}

function isExit(event) {
    return event.trigger === 'bump'
        && (event.commands || []).some(command => command.cmd === 'LOAD_MAP');
}

const DIRECTIONS = ['away', 'toward', 'left', 'right'];

function candidateMap({mapId, templateId, manifest, packagePath, npcs, lane, track, camera, exitDirection}) {
    const target = readMap(mapId);
    const template = readMap(templateId);
    const point = name => {
        const anchor = manifest.anchors && manifest.anchors[name];
        if (!anchor) throw new Error(`package has no ${name} anchor; pass it to the exporter`);
        return anchor.position;
    };
    const map = structuredClone(target);
    map.traversal = structuredClone(template.traversal);
    map.traversal.environmentPackage = packagePath;
    if (lane) Object.assign(map.traversal.lane, {minY: lane[0], maxY: lane[1]});
    if (track) {
        const [centre, offset] = track;
        map.traversal.camera.target.y = centre;
        Object.assign(map.traversal.camera.tracking, {center: centre, minOffsetX: -offset, maxOffsetX: offset});
    }
    if (camera) merge(map.traversal.camera, camera);
    for (const key of PRESENTATION) {
        if (key in template) map[key] = structuredClone(template[key]);
        else delete map[key];
    }

    const exits = target.events.filter(isExit);
    if (exits.length !== 1) throw new Error(`map ${mapId} has ${exits.length} exit events; expected 1`);
    const exit = exits[0];
    exit.worldPosition = point('exit_door');
    // A door in a hall's end wall leads off the side of the screen, not away;
    // the staged event says so when the package moved the door.
    if (exitDirection) {
        if (!DIRECTIONS.includes(exitDirection)) throw new Error(`--exit-direction must be one of ${DIRECTIONS.join(', ')}`);
        exit.direction = exitDirection;
    }
    const radius = (template.traversal.doorways || [{}])[0].radius || 0.9;
    map.traversal.doorways = [{anchor: 'exit_door', eventInstanceId: exit.instanceId, radius}];

    const kept = [];
    for (const [instanceId, anchor] of npcs) {
        const event = target.events.find(e => e.instanceId === instanceId);
        if (!event) throw new Error(`map ${mapId} has no event ${instanceId}`);
        event.worldPosition = point(anchor);
        kept.push(event);
    }
    map.events = [...kept, exit];
    const dropped = target.events.filter(e => !map.events.includes(e)).map(e => e.instanceId);
    return {map, dropped};
}

function stage({output, packageDir, mapId, templateId = 28, npcs = [], lane, track, camera, exitDirection}) {
    output = path.resolve(output);
    if (!output.startsWith(path.join(root, 'out') + path.sep) || fs.existsSync(output))
        throw new Error('Use a new stage directory inside repository out/');
    const manifest = JSON.parse(fs.readFileSync(path.join(packageDir, 'environment.json'), 'utf8'));
    const name = path.basename(path.resolve(packageDir));
    const packagePath = `assets/environments/review/${name}/environment.json`;
    const {map, dropped} = candidateMap({mapId, templateId, manifest, packagePath, npcs, lane, track, camera, exitDirection});

    const result = stageProjectGates({projectDir: project, outputDir: path.join(output, 'game')});
    fs.cpSync(packageDir, path.dirname(path.join(result.stageDir, packagePath)), {recursive: true});
    const mapsPath = path.join(result.stageDir, 'data/maps.json');
    const maps = JSON.parse(fs.readFileSync(mapsPath, 'utf8'));
    const index = maps.findIndex(m => m.id === map.id);
    if (index < 0) throw new Error(`stage has no map ${map.id}`);
    maps[index] = map;
    fs.writeFileSync(mapsPath, JSON.stringify(maps, null, 2) + '\n');
    fs.copyFileSync(path.join(__dirname, 'tests/environment_frames.lua'),
                    path.join(result.stageDir, 'tests/environment_frames.lua'));
    fs.writeFileSync(path.join(output, 'map.json'), JSON.stringify(map, null, 2) + '\n');
    fs.writeFileSync(path.join(output, 'candidate.json'), JSON.stringify({
        mapId: map.id, templateId, package: packagePath,
        sourceBlend: manifest.provenance && manifest.provenance.sourceBlend,
        npcs: Object.fromEntries(npcs), droppedEvents: dropped, replacedOnlyInStage: true,
    }, null, 2) + '\n');
    console.log(JSON.stringify({stageDir: result.stageDir, mapId: map.id, package: packagePath, droppedEvents: dropped}, null, 2));
    return result;
}

function parse(argv) {
    const options = {npcs: []};
    for (let i = 0; i < argv.length; i += 1) {
        const flag = argv[i];
        const value = argv[i + 1];
        if (flag === '--output') options.output = value;
        else if (flag === '--package') options.packageDir = path.resolve(value);
        else if (flag === '--map-id') options.mapId = Number(value);
        else if (flag === '--template') options.templateId = Number(value);
        else if (flag === '--exit-direction') options.exitDirection = value;
        else if (flag === '--camera') {
            try { options.camera = JSON.parse(value); } catch (error) { throw new Error(`--camera takes JSON: ${error.message}`); }
        } else if (flag === '--lane' || flag === '--track') {
            const pair = [Number(value), Number(argv[i + 2])];
            if (!pair.every(Number.isFinite)) throw new Error(`${flag} takes two numbers`);
            options[flag.slice(2)] = pair;
            i += 1;
        }
        else if (flag === '--npc') {
            const [id, anchor] = String(value).split('=');
            if (!id || !anchor) throw new Error('--npc takes <eventInstanceId>=<anchor>');
            options.npcs.push([id, anchor]);
        } else throw new Error(`unknown argument ${flag}`);
        i += 1;
    }
    if (!options.output || !options.packageDir || !Number.isInteger(options.mapId))
        throw new Error('Use --output out/<new-stage> --package <dir> --map-id <id> [--template 28] [--npc id=anchor] [--lane min max] [--track centre px] [--camera json] [--exit-direction dir]');
    return options;
}

if (require.main === module) stage(parse(process.argv.slice(2)));
module.exports = {stage, candidateMap, parse};
