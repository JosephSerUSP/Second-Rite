'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const Commands=require('../../../studio/editor/js/second-rite-editor-commands');
const History=require('../../../studio/editor/js/studio-history');
const View=require('../../../studio/editor/js/generated/world-view');
const root=path.resolve(__dirname,'../../..');
const candidate=path.join(root,'tests/fixtures/walk_profile_courtyard_map.json');

test('candidate profile uses real Studio move, split, undo and redo commands',()=>{
    const map=JSON.parse(fs.readFileSync(candidate));
    const payload={maps:[map]};
    const snapshot=()=>History.clone(map.traversal.lane.groundProfile);
    const before=snapshot();
    const authority='maps:32';
    const history=History.create({getAuthority:()=>authority,apply(record,direction){
        map.traversal.lane.groundProfile=History.clone(direction==='undo'?record.before:record.after);return true;
    }});
    assert.equal(Commands.splitGroundProfileSegment(payload,0,1,.5).ok,true);
    assert.equal(Commands.moveGroundProfilePoint(payload,0,2,5,.25).ok,true);
    const after=snapshot();
    assert.equal(history.commit({authority,target:{kind:'walk-profile',key:authority},before,after}),true);
    assert.equal(View.groundHeight(after,0,5),.25);
    assert.equal(history.undo(),true);assert.deepEqual(snapshot(),before);
    assert.equal(View.groundHeight(snapshot(),0,5),.15);
    assert.equal(history.redo(),true);assert.deepEqual(snapshot(),after);
    assert.equal(Commands.moveGroundProfilePoint(payload,0,2,9,.25).ok,false,'out-of-order point rejected');
});

const {audit}=require('../../towngen/audit_geography');
test('town geography extraction preserves doorway identity and nested transfer provenance',()=>{
 const graph=audit();
 const hall=graph.edges.find(edge=>edge.from===1001&&edge.to===34);
 assert.equal(hall.event,'core-run-court-door-passage-house');
 assert.equal(hall.arrival,'exit_door');
 assert.ok(graph.edges.some(edge=>edge.from===34&&edge.to===1001));
 assert.ok(Array.isArray(hall.arrivalPosition));
 const roomDoor=graph.edges.find(edge=>edge.from===34&&edge.to===25);
 assert.equal(roomDoor.event,'st-maria-passage-hall-room3_door');
 assert.equal(roomDoor.arrival,'exit_door');
 assert.ok(graph.edges.some(edge=>edge.from===25&&edge.to===34));
 const room=graph.maps.find(map=>map.id===25);
 assert.equal(room.spawnAnchor,'spawn_player');
 assert.ok(room.environmentAnchors.spawn_player.position);
 assert.ok(graph.edges.some(edge=>edge.location.includes('/common:')));
 assert.ok(graph.maps.find(map=>map.id===1001).lane.groundProfile.length>2);
});
