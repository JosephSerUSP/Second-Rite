-- Persistent save I/O failures must be visible to callers and leave a prior
-- valid slot readable. The source-tree mirror is deliberately unavailable in
-- the fault case: it is never the success authority.

package.path = package.path .. ";./?.lua;./engine/?.lua"

local loader = require("engine.data.loader")
local session = require("engine.session")
local savegame = require("engine.savegame")

loader.init()

local slot = "savegame_io_regression"
local sess = session.GameSession.new(loader)
sess:initializeStartingParty()
sess.gold = 17
assert(savegame.save(sess, loader, "map", slot), "fixture save must succeed")

local originalWrite = love.filesystem.write
local originalOpen = io.open
love.filesystem.write = function()
    return false, "simulated persistent write failure"
end
io.open = function()
    return nil, "simulated source mirror failure"
end

sess.gold = 99
local saved, saveErr = savegame.save(sess, loader, "map", slot)

love.filesystem.write = originalWrite
io.open = originalOpen

assert(not saved, "persistent write failure must not report save success")
assert(type(saveErr) == "string" and saveErr:find("persistent write failure", 1, true),
    "save result exposes the durable-write failure")
local restored = assert(savegame.load(slot, loader), "prior save remains readable after failed write")
assert(restored.gold == 17, "failed replacement preserves the last valid save")
savegame.delete(slot)

print("=== savegame I/O regression: all checks passed ===")
