import json

with open('projects/labs/scene-benchmarks/data/scenes/d002_sokoban.json', 'r') as f:
    scene = json.load(f)

init_script = scene['scripts']['init']
move_script = scene['scripts']['move']

# In d002_sokoban.json, it stores the 'redraw' function in sceneState.
# sceneState must be a serializable value tree without functions.
# Let's inline the redraw logic into the SCRIPT handlers and remove it from sceneState.

init_script_fixed = init_script.replace('sceneState.redraw = redraw\nsceneState.redraw()', 'redraw()')

# In move, we don't have access to redraw(), so let's paste the redraw implementation there too.
redraw_impl = """
local lines = {}
for y = 0, sceneState.h - 1 do
    local row = ""
    for x = 0, sceneState.w - 1 do
        local cell = sceneState.grid[y * sceneState.w + x + 1]
        if x == sceneState.px and y == sceneState.py then
            row = row .. "@"
        elseif cell == 'W' then
            row = row .. "#"
        elseif cell == 'C' then
            row = row .. "O"
        elseif cell == 'G' then
            row = row .. "."
        else
            row = row .. " "
        end
    end
    table.insert(lines, row)
end
sceneState.boardText = table.concat(lines, "\\n")
"""

move_script_fixed = move_script.replace('sceneState.redraw()', redraw_impl)

scene['scripts']['init'] = init_script_fixed
scene['scripts']['move'] = move_script_fixed

with open('projects/labs/scene-benchmarks/data/scenes/d002_sokoban.json', 'w') as f:
    json.dump(scene, f, indent=2)
