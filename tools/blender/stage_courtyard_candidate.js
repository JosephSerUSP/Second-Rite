#!/usr/bin/env node
'use strict';
// Review the promoted courtyard through the canonical exporter. Optional package
// controls affect only the stage; topology and authored maps come from Project.
const fs=require('node:fs'), path=require('node:path');
const {stageProjectGates}=require('../ci/stage-project-gates');
const View=require('../../studio/editor/js/generated/world-view');
const root=path.resolve(__dirname,'../..'), shipping=path.join(root,'projects/hichaukitoden-game');
function stage(output,packageDir) {
    output=path.resolve(output);
    if (!output.startsWith(path.join(root,'out')+path.sep)) throw new Error('Review stages must stay inside repository out/');
    if (fs.existsSync(output)) throw new Error('Refusing to overwrite an existing review stage');
    const readMap=id=>JSON.parse(fs.readFileSync(path.join(shipping,`data/maps/${id}.json`)));
    const court=readMap(32), cortico=readMap(26), lodging=readMap(25);
    const door=cortico.events.find(e=>e.instanceId==='st-maria-cortico-lodging_door');
    const back=lodging.events.find(e=>e.instanceId==='st-maria-lodging-exit_door');
    if (!door || door.commands[0].mapId!==32 || !back || back.commands[0].mapId!==32) throw new Error('Shipping courtyard connections changed');
    const floor=View.groundHeight(cortico.traversal.lane.groundProfile,cortico.traversal.lane.groundZ,door.worldPosition[1]);
    const datum={corticoDoorY:door.worldPosition[1],corticoDatum:0,courtyardDatum:floor,courtyardEntryLocalZ:0,courtyardUpperLocalZ:0.3,lodgingDatum:floor+0.3,lodgingLocalFloorZ:0};
    const staged=stageProjectGates({projectDir:shipping,outputDir:path.join(output,'game')});
    if (packageDir) fs.cpSync(packageDir,path.dirname(path.join(staged.stageDir,court.traversal.environmentPackage)),{recursive:true});
    fs.copyFileSync(path.join(__dirname,'tests/courtyard_frames.lua'),path.join(staged.stageDir,'tests/courtyard_frames.lua'));
    fs.writeFileSync(path.join(output,'datum.json'),JSON.stringify(datum,null,2)+'\n');
    console.log(JSON.stringify({...staged,datum},null,2));
    return {...staged,datum,project:shipping};
}
if (require.main===module) {
    const args=process.argv.slice(2), value=flag=>args[args.indexOf(flag)+1];
    if (!args.includes('--output')) throw new Error('Use --output out/<new-directory> [--package <review-control-package>]');
    stage(value('--output'),args.includes('--package')?path.resolve(value('--package')):null);
}
module.exports={stage};
