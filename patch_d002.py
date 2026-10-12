import json

with open('projects/labs/scene-benchmarks/data/scenes/d002_sokoban.json', 'r') as f:
    scene = json.load(f)

# Remove the function reference from the state
init_script = scene['scripts']['init']

init_script = init_script.replace('sceneState.redraw = redraw\nsceneState.redraw()\n', '')
scene['scripts']['init'] = init_script

# Move redraw logic to on_frame using formulas/SCRIPT or just do it inside move and init directly without storing function
new_redraw = """
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

scene['scripts']['init'] += new_redraw

move_script = scene['scripts']['move']
move_script = move_script.replace('sceneState.redraw()\n', new_redraw)
scene['scripts']['move'] = move_script

with open('projects/labs/scene-benchmarks/data/scenes/d002_sokoban.json', 'w') as f:
    json.dump(scene, f, indent=2)
