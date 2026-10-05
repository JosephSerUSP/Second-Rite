local compositor = require("presentation.world_pass_compositor")
local viewport = require("presentation.viewport_3d")

local passed, failed = 0, 0
local function check(condition, message)
    if condition then
        passed = passed + 1
    else
        failed = failed + 1
        io.stderr:write("FAIL: " .. message .. "\n")
    end
end

local function sessionWithScale(value)
    return {
        loader = {
            system = {
                dungeon = {
                    psxRendering = {
                        environmentSupersample = value,
                    },
                },
            },
        },
    }
end

check(compositor.resolveScale(sessionWithScale(nil)) == 1,
    "selective environment AA defaults off")
check(compositor.resolveScale(sessionWithScale(3)) == 3,
    "3x environment supersampling resolves")
check(compositor.resolveScale(sessionWithScale(9)) == 4,
    "environment supersampling is bounded to 4x")
check(compositor.resolveScale(sessionWithScale(1)) == 1,
    "1x uses the ordinary world path")

local eligible = sessionWithScale(3)
check(compositor.isEligible(eligible),
    "ordinary live-3D session accepts selective AA")
eligible.roomBakePass = "depth"
check(not compositor.isEligible(eligible),
    "room bake diagnostics bypass selective AA")

local prerendered = sessionWithScale(3)
prerendered.townTraversal = { environment = { preRendered = { mode = "layered_2d" } } }
check(not compositor.isEligible(prerendered),
    "literal layered prerender stays on its existing renderer")

check(viewport.surfacePresentationPass({ category = "billboard" }) == "live",
    "ordinary billboards default to the live pass")
check(viewport.surfacePresentationPass({ category = "wall_clip" }) == "environment",
    "structural dynamic geometry defaults to environment")
check(viewport.surfacePresentationPass({ presentationPass = "live", category = "wall_clip" }) == "live",
    "explicit renderer pass ownership wins")
check(viewport.surfacePresentationPass({ model = true }) == "environment",
    "unclassified placed models retain environment default")

print(string.format("WORLD PASS COMPOSITOR TESTS: %d passed, %d failed", passed, failed))
if failed > 0 then os.exit(1) end
