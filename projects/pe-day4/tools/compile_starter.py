#!/usr/bin/env python3
"""Compile the bounded traversal starter from the reference snapshot and route.

Generated data is consumed by the ordinary runtime; this is not a simulation.
Geometry/appearance bindings and explicitly prototype stats live in starter.json.
"""
from pathlib import Path
import argparse
import json

PROJECT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((PROJECT / path).read_text(encoding='utf8'))


def compile_data():
    spec = load('starter.json')
    snapshot = load('reference/canonical-start.json')
    route = load('reference/route.json')
    nodes = {node['id']: node for node in route['nodes']}
    bindings = {entry['node']: entry for entry in spec['maps']}
    assert len(bindings) == len(spec['maps']), 'duplicate node binding'
    assert len({b['mapId'] for b in bindings.values()}) == len(bindings), 'duplicate Map id'
    assert snapshot['entry']['scene'] == route['start'] in bindings
    assert spec['actor']['status'] == spec['equipment']['status'] == spec['geometry']['status'] == 'prototype'
    assert snapshot['world']['flags'] == [], 'starter must begin before Hospital state'
    assert snapshot['equipment']['transferredParameters']['value'] == {}, 'tuning needs M3 support'
    assert snapshot['actor']['resources'] == 'full_for_level'
    assert snapshot['equipment']['weapon']['loadedRounds']['value'] is None, 'resolved magazines need M3 binding, not silent omission'
    edges = {edge['id']: edge for edge in route['edges']}
    outgoing = {node: [] for node in bindings}
    for edge_id in spec['edgeIds']:
        edge = edges[edge_id]
        assert edge['from'] in bindings and edge['to'] in bindings, edge_id
        outgoing[edge['from']].append((edge, edge['to']))
        if edge.get('bidirectional'):
            outgoing[edge['to']].append((edge, edge['from']))
    result = {}
    def literal(value):
        if value is None: return 'nil'
        if isinstance(value, bool): return 'true' if value else 'false'
        return json.dumps(value)
    def state_command(flag, clear=False):
        owner = spec['stateBindings'][flag]
        if 'item' in owner:
            return {'cmd': 'CHANGE_ITEM', 'item': owner['item'], 'count': -1 if clear else 1}
        return {'cmd': 'SET_GAME_VARIABLE', 'name': owner['variable'], 'value': literal(None if clear else owner['value'])}
    def state_condition(flag):
        owner = spec['stateBindings'][flag]
        if 'item' in owner: return 'hasItem:' + owner['item']
        return f"variables.{owner['variable']} == {literal(owner['value'])}"
    def guarded(conditions, commands, refusal, otherwise=None):
        for condition in reversed(conditions):
            commands = [{'cmd':'CONDITIONAL_BRANCH','condition':condition,'commands':commands,'elseCommands':otherwise if otherwise is not None else [{'cmd':'TEXT','text':refusal}]}]
        return commands
    def choice(options):
        return [{'cmd':'CHOICE','options':options + [{'label':'Leave','commands':[]}], 'cancelOption':len(options)+1}]
    for node, binding in bindings.items():
        package = f"assets/environments/{binding['environment']}/environment.json"
        environment = load(package)
        anchors = environment['anchors']
        assert binding['arrival'] in anchors and binding['spawn'] in anchors
        options = []
        alternatives = {}
        for edge, destination in outgoing[node]:
            commands = [state_command(flag, clear=True) for flag in edge.get('clears', [])]
            commands += [state_command(flag) for flag in edge.get('grants', [])]
            commands.append({'cmd': 'LOAD_MAP', 'mapId': bindings[destination]['mapId'], 'arrival': bindings[destination]['arrival']})
            conditions = [state_condition(flag) for flag in edge.get('requiresAll', [])]
            if edge.get('oneShot'):
                assert edge.get('grants'), 'one-shot edge needs a persistent marker'
                conditions.append("not (" + state_condition(edge['grants'][0]) + ")")
            alternatives.setdefault(destination, []).append((conditions, commands))
        for destination, paths in alternatives.items():
            program = [{'cmd':'TEXT','text':'This route is unavailable in the current power/key state.'}]
            for conditions, commands in reversed(paths):
                program = guarded(conditions, commands, '', otherwise=program)
            options.append({'label':nodes[destination]['area'],'commands':program})
        if node == 'elevators_1f':
            options.append({'label':'Ward route / unit boundary','commands':guarded([state_condition('ward_route_open')],[{'cmd':'TEXT','text':spec['boundaryText']}],'Restore basement power and return in the elevator first.')})
        program = options[0]['commands'] if len(options) == 1 else choice(options) if options else [{'cmd': 'TEXT', 'text': spec['boundaryText']}]
        result[f"data/maps/{binding['mapId']}.json"] = {
            'id': binding['mapId'], 'title': nodes[node]['area'] + ' (proxy)', 'category': 'experiment', 'depth': 0,
            'safe': True, 'layout': ['.'], 'spawn': {'x': 0, 'y': 0, 'dir': 'N'},
            'events': [{'id': binding['mapId'] * 100 + 1, 'instanceId': node + '-route-door',
                        'name': 'Blue route door', 'x': 0, 'y': 0,
                        'worldPosition': anchors[binding['door']]['position'], 'interactionRadius': 1.15,
                        'trigger': 'interact', 'commands': program}],
            'traversal': {'provider': 'continuous_surface', 'actorAppearance': spec['actor']['appearance'],
                          'environmentPackage': package, 'spawnAnchor': binding['spawn'], 'interactionRadius': 1.15,
                          'surface': {'speed': 2.65, 'maxStep': 0.08}},
        }
        interactions = nodes[node].get('interactions', [])
        if interactions:
            assert binding.get('interaction') in anchors, 'interaction subject needs a package-owned anchor'
            actions = []
            for interaction in interactions:
                iid = interaction['id']
                marker = 'collected_' + iid if iid.startswith('take_') else interaction['grants'][0]
                conditions = [state_condition(flag) for flag in interaction.get('requiresAll', [])]
                # Success is one-shot for pickups, repairs and installation alike.
                conditions.append('not (' + ('variables.' + marker + ' == true' if iid.startswith('take_') else state_condition(interaction['grants'][0])) + ')')
                commands = [state_command(flag, clear=True) for flag in interaction.get('clears', [])]
                commands += [state_command(flag) for flag in interaction.get('grants', [])]
                if iid.startswith('take_'):
                    commands.append({'cmd':'SET_GAME_VARIABLE','name':marker,'value':'true'})
                commands.append({'cmd':'TEXT','text':iid.replace('_',' ').capitalize() + ' complete.'})
                actions.append({'label':iid.replace('_',' ').capitalize(),'commands':guarded(conditions,commands,'Already completed, or a required item/repair is missing.')})
            result[f"data/maps/{binding['mapId']}.json"]['events'].append({
                'id':binding['mapId']*100+2,'instanceId':node+'-workstation','name':'Orange interaction workstation',
                'x':0,'y':0,'worldPosition':anchors[binding['interaction']]['position'],'interactionRadius':1.0,
                'trigger':'interact','commands':actions[0]['commands'] if len(actions)==1 else choice(actions)})
    actor_id = snapshot['actor']['id']
    result['data/units/index.json'] = {'files': [actor_id + '.json']}
    result[f'data/units/{actor_id}.json'] = {'id': actor_id, 'name': 'Traversal actor', 'level': snapshot['actor']['level'],
                                          'skills': [], 'baseParams': spec['actor']['baseParams'], 'growthBands': [], 'defaultGrowthSeed': 12345}
    inventory = snapshot['inventory']
    assert len({i['id'] for i in inventory}) == len(inventory)
    items = [{'id': entry['id'], 'name': entry['id'].replace('_', ' ').title(), 'type': 'key', 'cost': 0,
              'description': 'Snapshot inventory identity; no use behavior in this traversal starter.'} for entry in inventory]
    for flag, owner in spec['stateBindings'].items():
        if 'item' in owner:
            items.append({'id':owner['item'],'name':flag.replace('_',' ').title(),'type':'key','cost':0,'description':'Hospital route item; retained after installation/use under explicit prototype policy.'})
    bonus = [entry['id'] for entry in inventory for _ in range(entry['quantity'])]
    equip_commands = []
    for field, slot, kind in [('weapon', 1, 'Weapon'), ('armor', 2, 'Armor')]:
        item_id = snapshot['equipment'][field]['id']
        items.append({'id': item_id, 'name': item_id.replace('_', ' ').title(), 'type': 'equipment', 'equipType': kind,
                      'cost': 0, 'traits': [], 'description': 'Snapshot equipment identity only; prototype parameters. No mechanical acceptance.'})
        bonus.append(item_id)
        equip_commands.append({'cmd': 'EQUIP_ITEM', 'slot': slot, 'target': 1, 'itemIndex': 2})
    result['data/items.json'] = items
    result['data/maps/index.json'] = {'files': [str(b['mapId']) + '.json' for b in spec['maps']]}
    result['data/system.json'] = {
        'ui': {'activeFont': 'monogram-extended', 'fontSize': 16, 'fontOffsetY': -4, 'fontNormalize': True,
               'autoRepeatInitial': 0.3, 'autoRepeatInterval': 0.06},
        'spawn': {'mapId': bindings[route['start']]['mapId'], 'x': 0, 'y': 0, 'dir': 'N'},
        'newGame': {'goldMin': 0, 'goldMax': 0, 'bonusItems': bonus, 'party': {'fixedMembers': [
            {'id': actor_id, 'name': 'Traversal actor', 'level': snapshot['actor']['level'], 'slot': 1}]}},
        'rtp': {'revision': '1.0'}, 'dungeon': {'psxRendering': {'affineTextures': False}},
    }
    start = [{'cmd': 'RESET_SESSION'}, *equip_commands,
             {'cmd': 'SET_GAME_VARIABLE', 'name': 'bonusPoints', 'value': snapshot['progression']['bonusPoints']['value']},
             {'cmd': 'LOAD_MAP', 'mapId': bindings[route['start']]['mapId']},
             {'cmd': 'SCENE_EVENT', 'kind': 'goto', 'scene': 'map'}]
    result['data/scenes/title.json'] = {
        'id': 'title', 'name': 'Hospital Slice Starter', 'kind': 'menu', 'draw': 'windows', 'config': {},
        'windows': [
            {'id': 'project_title', 'rect': {'x': 3, 'y': 5, 'w': 26, 'h': 7}, 'style': 'frame', 'content': [
                {'type': 'text', 'text': 'Hospital Slice Starter\nOriginal proxy rooms/character\nTraversal only - combat not calibrated'}]},
            {'id': 'title_menu', 'rect': {'x': 5, 'y': 15, 'w': 22, 'h': 5}, 'style': 'list', 'visibleRows': 2,
             'content': [{'type': 'list', 'listId': 'term:title.options', 'cursor': 'sceneState.idx'}]},
        ],
        'hooks': {'on_enter': [{'cmd': 'SET_SCENE_STATE', 'name': 'idx', 'value': 1}],
                  'on_up': [{'cmd': 'SET_SCENE_STATE', 'name': 'idx', 'value': 'sceneState.idx == 1 and 2 or 1'}],
                  'on_down': [{'cmd': 'SET_SCENE_STATE', 'name': 'idx', 'value': 'sceneState.idx == 1 and 2 or 1'}],
                  'on_select': [{'cmd': 'IF', 'condition': 'sceneState.idx == 1', 'then': start},
                                {'cmd': 'IF', 'condition': 'sceneState.idx == 2', 'then': [{'cmd': 'QUIT_GAME'}]}]},
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, data in compile_data().items():
        path = PROJECT / name
        payload = (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode('utf8')
        if args.check:
            assert path.is_file() and path.read_bytes().replace(b'\r\n', b'\n') == payload, f'stale generated data: {name}'
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    print('HOSPITAL STARTER DATA OK (traversal/proxy only)')


if __name__ == '__main__':
    main()
