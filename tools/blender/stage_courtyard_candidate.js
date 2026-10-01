#!/usr/bin/env node
'use strict';
// Candidate authoring Project -> canonical runtime export; never modifies shipping data.
const fs = require('node:fs');
const path = require('node:path');
const {stageProjectGates} = require('../ci/stage-project-gates');
const View = require('../../studio/editor/js/generated/world-view');
const root = path.resolve(__dirname, '../..');
const shipping = path.join(root, 'projects/hichaukitoden-game');
const candidate = path.join(shipping, 'assets/authoring/candidates/passage_house_courtyard');

function stage(output, packageDir) {
    output = path.resolve(output);
    const allowed = path.join(root, 'out') + path.sep;
    if (!output.startsWith(allowed)) throw new Error('Candidate stages must stay inside repository out/');
    if (fs.existsSync(output)) throw new Error('Refusing to overwrite an existing candidate stage');
    const project = path.join(output, 'project');
    fs.mkdirSync(project, {recursive:true});
    fs.cpSync(shipping, project, {recursive:true});
    const map32 = JSON.parse(fs.readFileSync(path.join(candidate, '32.json')));
    const readMap = id => JSON.parse(fs.readFileSync(path.join(project, `data/maps/${id}.json`)));
    const saveMap = map => fs.writeFileSync(path.join(project, `data/maps/${map.id}.json`), JSON.stringify(map,null,2)+'\n');
    const cortico = readMap(26), lodging = readMap(25);
    const door = cortico.events.find(event => event.instanceId === 'st-maria-cortico-lodging_door');
    if (!door || door.commands.length !== 1 || door.commands[0].mapId !== 25) throw new Error('Cortico entrance contract changed');
    const returnDoor = lodging.events.find(event => event.instanceId === 'st-maria-lodging-exit_door');
    if (!returnDoor || returnDoor.commands[0].mapId !== 26) throw new Error('Lodging return contract changed');
    const floor = View.groundHeight(cortico.traversal.lane.groundProfile,
        cortico.traversal.lane.groundZ, door.worldPosition[1]);
    door.commands[0] = {cmd:'LOAD_MAP',mapId:32,arrival:'cortico_entry'};
    returnDoor.commands[0] = {cmd:'LOAD_MAP',mapId:32,arrival:'lodging_entry'};
    saveMap(cortico); saveMap(lodging); saveMap(map32);
    const indexPath = path.join(project,'data/maps/index.json');
    const index = JSON.parse(fs.readFileSync(indexPath));
    if (index.files.includes('32.json')) throw new Error('Map 32 already allocated');
    index.files.push('32.json'); fs.writeFileSync(indexPath,JSON.stringify(index,null,2)+'\n');
    fs.cpSync(packageDir,path.join(project,'assets/environments/st_maria_town/passage_house_courtyard'),{recursive:true});
    const datum = {corticoDoorY:door.worldPosition[1],corticoDatum:0,courtyardDatum:floor,
        courtyardEntryLocalZ:0,courtyardUpperLocalZ:0.3,lodgingDatum:floor+0.3,lodgingLocalFloorZ:0};
    fs.writeFileSync(path.join(output,'datum.json'),JSON.stringify(datum,null,2)+'\n');
    const staged = stageProjectGates({projectDir:project,outputDir:path.join(output,'game')});
    fs.copyFileSync(path.join(__dirname,'tests/courtyard_runtime.lua'),path.join(staged.stageDir,'tests/test_courtyard_candidate.lua'));
    fs.copyFileSync(path.join(__dirname,'tests/courtyard_frames.lua'),path.join(staged.stageDir,'tests/courtyard_frames.lua'));
    const laneTestPath=path.join(staged.stageDir,'tests/test_bounded_lane.lua');
    const laneTest=fs.readFileSync(laneTestPath,'utf8');
    const shippingAssertion='check(doorTargets(26)[25], "the backstreet is how a player returns to the rented room")';
    if(!laneTest.includes(shippingAssertion)) throw new Error('Shipping topology fixture boundary changed');
    fs.writeFileSync(laneTestPath,laneTest.replace(shippingAssertion,
        'check(doorTargets(26)[32] and doorTargets(32)[25], "the court connects the backstreet to the rented room")'));
    const mainPath = path.join(staged.stageDir,'main.lua');
    const main = fs.readFileSync(mainPath,'utf8');
    if (!main.includes('"test_bounded_lane",')) throw new Error('Runtime unit registration boundary changed');
    fs.writeFileSync(mainPath,main.replace('"test_bounded_lane",','"test_bounded_lane",\n            "test_courtyard_candidate",'));
    console.log(JSON.stringify({...staged,datum},null,2));
    return {...staged,datum,project};
}
if (require.main === module) {
    const args = process.argv.slice(2);
    const value = flag => args[args.indexOf(flag)+1];
    if (!args.includes('--output')) throw new Error('Use --output out/<new-directory> [--package <exported-package>]');
    stage(value('--output'),args.includes('--package')?path.resolve(value('--package')):path.join(candidate,'package'));
}
module.exports = {stage};
