'use strict';
// Candidate map replacement exists only in the canonical export stage.
const fs = require('node:fs');
const path = require('node:path');
const {stageProjectGates} = require('../ci/stage-project-gates');
const root = path.resolve(__dirname, '../..');
function stage(output, packageDir) {
    output = path.resolve(output);
    if (!output.startsWith(path.join(root, 'out') + path.sep) || fs.existsSync(output))
        throw new Error('Use a new stage directory inside repository out/');
    const project = path.join(root, 'projects/hichaukitoden-game');
    const read = id => JSON.parse(fs.readFileSync(path.join(project, `data/maps/${id}.json`)));
    const map = read(28);
    const registrar = read(33).events.find(e => e.instanceId === 'st-maria-passage-office-registrar');
    if (!registrar) throw new Error('Authored Registrar event missing');
    const packagePath = 'assets/environments/review/passage_office/environment.json';
    const manifest = JSON.parse(fs.readFileSync(path.join(packageDir, 'environment.json')));
    const point = name => {
        const anchor = manifest.anchors[name];
        if (!anchor) throw new Error(`Missing anchor ${name}`);
        return anchor.position;
    };
    map.title = 'St. Maria - Passage Office (workflow candidate)';
    map.intro = 'A narrow ledger, a seal, and a place to wait.';
    map.traversal.environmentPackage = packagePath;
    const celina = structuredClone(registrar);
    celina.id = 2801;
    celina.instanceId = 'registry-review-registrar';
    celina.worldPosition = point('registrar');
    // Same authored Registrar commands and retained Celina artwork.
    celina.sprite = 'assets/character/npc_celina.png';
    celina.frameWidth = 24; celina.frameHeight = 48; celina.frameIndex = 0; celina.worldHeight = 1.75;
    const exit = map.events.find(e => e.instanceId === map.traversal.doorways[0].eventInstanceId);
    if (!exit) throw new Error('Interior exit fixture missing');
    exit.worldPosition = point('exit_door');
    map.events = [celina, exit];
    const result = stageProjectGates({projectDir: project, outputDir: path.join(output, 'game')});
    fs.cpSync(packageDir, path.dirname(path.join(result.stageDir, packagePath)), {recursive: true});
    const mapsPath = path.join(result.stageDir, 'data/maps.json');
    const maps = JSON.parse(fs.readFileSync(mapsPath));
    const index = maps.findIndex(m => m.id === map.id);
    if (index < 0) throw new Error('Stage map 28 missing');
    maps[index] = map;
    fs.writeFileSync(mapsPath, JSON.stringify(maps, null, 2) + '\n');
    fs.writeFileSync(path.join(output, 'map.json'), JSON.stringify(map, null, 2) + '\n');
    fs.copyFileSync(path.join(__dirname, 'tests/environment_frames.lua'), path.join(result.stageDir, 'tests/environment_frames.lua'));
    fs.writeFileSync(path.join(output, 'candidate.json'), JSON.stringify({mapId:28, package:packagePath,
        sourceBlend:manifest.provenance.sourceBlend, replacedOnlyInStage:true,
        registrarCommandsSource:'projects/hichaukitoden-game/data/maps/33.json',
        registrarSprite:celina.sprite}, null, 2)+'\n');
    console.log(JSON.stringify(result, null, 2));
    return result;
}
if (require.main === module) {
    const args = process.argv.slice(2);
    const value = flag => args[args.indexOf(flag) + 1];
    if (!args.includes('--output') || !args.includes('--package')) throw new Error('Use --output out/<new-stage> --package <package>');
    stage(value('--output'), path.resolve(value('--package')));
}
module.exports = {stage};
