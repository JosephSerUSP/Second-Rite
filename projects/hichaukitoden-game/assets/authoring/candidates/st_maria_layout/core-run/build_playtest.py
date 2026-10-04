"""Export the saved B12 candidate into an isolated, playable native Project."""
import json
import subprocess
import sys
import argparse
import zipfile
from pathlib import Path

CANDIDATE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[7]
STAGE = ROOT / 'out/st-maria-playtest/game'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

def text(value):
    return dict(cmd='TEXT', text=value)

parser = argparse.ArgumentParser()
parser.add_argument('--from-love', type=Path)
args = parser.parse_args()
if args.from_love:
    STAGE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.from_love) as archive:
        archive.extractall(STAGE)
else:
    subprocess.run(['node', 'tools/ci/stage-project-gates.js', '--output', str(STAGE)], cwd=ROOT, check=True)
subprocess.run([sys.executable, str(CANDIDATE / 'install_navigation.py'), str(STAGE)], cwd=ROOT, check=True)
maps = read(STAGE / 'data/maps.json')
by_id = {m['id']: m for m in maps}
common = read(STAGE / 'data/commonEvents.json')
rest_event_id = max(int(key) for key in common) + 1
common[str(rest_event_id)] = dict(name='Passage House rest', commands=[dict(cmd='RECOVER_PARTY')])
home = by_id[25]['events'][0]
home['name'] = 'Passage House caretaker'
home['commands'] = [text('Your room is ready. Registration is at the Passage Office in the Praca: leave the house, take the right-hand street, then enter the Registry.'),
    dict(cmd='CHOICE', options=[
        dict(label='Rest in Room 3.', commands=[dict(cmd='CALL_COMMON_EVENT', commonEventId=rest_event_id), text('You and your companions rest. HP, MP and spell charges are restored.')]),
        dict(label='Ask for directions.', commands=[text('The bakery street is left of the Cortico. Follow it down to the pub and forge. The workers stair from the port brings you back here. From the Praca, take the uphill stairs toward the churchyard; the Labyrinth is beyond it.')]),
        dict(label='Leave.', commands=[])])]
registry = by_id[33]['events'][0]
registry['commands'].append(text('From the Praca, take the stairs uphill to the churchyard, then follow the path to the Labyrinth forecourt. Supplies are downhill: bakery, pub and forge. Return here whenever you need directions.'))

def visit(value, fn):
    if isinstance(value, dict):
        fn(value)
        for child in list(value.values()):
            visit(child, fn)
    elif isinstance(value, list):
        for child in value:
            visit(child, fn)

# The churchyard guard orients the player toward the physical gate, rather
# than offering a second invisible descent before the forecourt is reached.
def orient_guard(command):
    if command.get('cmd') == 'CALL_COMMON_EVENT' and command.get('commonEventId') == 33:
        command.clear()
        command.update(text('Your writ is in order. Follow the path onward to the Labyrinth forecourt; the iron gate is there.'))
visit(by_id[1006]['events'], orient_guard)

def town_return(command):
    if command.get('cmd') in ['LOAD_MAP', 'SET_MAP_PRESENTATION'] and str(command.get('mapId')) == '1':
        command['mapId'] = 1007
        if command['cmd'] == 'LOAD_MAP':
            command['arrival'] = 'labyrinth-gate'
visit(common['40'], town_return)
def portal_return(command):
    if command.get('cmd') == 'PORTAL_TO_TOWN':
        command['mapId'] = 1007
visit(common['41'], portal_return)
common['42']['commands'].append(text('When you are ready, leave the Passage House. The Registry is in the Praca, along the right-hand street outside.'))
system = read(STAGE / 'data/system.json')
system['spawn']['mapId'] = 25
write(STAGE / 'data/system.json', system)
write(STAGE / 'data/maps.json', maps)
write(STAGE / 'data/commonEvents.json', common)
# Saves from the shipping Project cannot accidentally resume the old town.
conf = STAGE / 'conf.lua'
conf.write_text(conf.read_text(encoding='utf-8').replace('t.identity = "SecondRite"', 't.identity = "hichaukitoden-st-maria-playtest"'), encoding='utf-8')
write(STAGE.parent / 'manifest.json', dict(source='st_maria_B12.blend',
    sourceSHA256=read(CANDIDATE / 'screen-contract.json')['sourceSHA256'],
    spawnMap=25, dungeonReturnMap=1007, registryMap=33,
    scope='Isolated native playtest. Existing expedition economy and battle behavior retained.'))
print('PLAYTEST BUILT:', STAGE)
if args.from_love:
    package = args.from_love.resolve()
    replacement = package.with_suffix('.playtest-love')
    with zipfile.ZipFile(replacement, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(STAGE.rglob('*')):
            relative = path.relative_to(STAGE)
            authoring = relative.parts[:2] == ('assets', 'authoring')
            if path.is_file() and relative.parts[0] not in ['tests'] and not authoring:
                archive.write(path, relative.as_posix())
    replacement.replace(package)
    print('PLAYTEST LOVE PACKAGED:', package, package.stat().st_size, 'bytes; authoring sources excluded')
