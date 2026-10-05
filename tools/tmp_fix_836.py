from pathlib import Path

path = Path("runtime/presentation/viewport_3d.lua")
text = path.read_text(encoding="utf-8")
old = '''    local targetWidth, targetHeight = surface.renderSize()
    local targetCanvas = love.graphics.getCanvas()
    if targetCanvas then
        targetWidth, targetHeight = targetCanvas:getDimensions()
    end
'''
new = '''    local targetWidth, targetHeight = surface.renderSize()
    local targetCanvas = love.graphics.getCanvas()
    -- LÖVE returns the colour Canvas directly for ordinary single-target binds,
    -- but an attachment table when an explicit depth/stencil Canvas is bound.
    -- The selective-AA compositor uses the latter; projection sizing still
    -- belongs to the first colour attachment in both cases.
    if type(targetCanvas) == "table" then
        targetCanvas = targetCanvas[1]
    end
    if targetCanvas and targetCanvas.getDimensions then
        targetWidth, targetHeight = targetCanvas:getDimensions()
    end
'''
if new in text:
    print("attachment-aware canvas sizing already applied")
elif text.count(old) == 1:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("attachment-aware canvas sizing applied")
else:
    raise SystemExit(f"expected one target-canvas block, found {text.count(old)}")
