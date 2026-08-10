-- Composition root for headless/build tooling.
--
-- The long-standing CLI implementation lives in cli_tools_impl.lua unchanged.
-- This tiny wrapper owns the one host-only interception Second Rite needs for
-- Thestra Studio's authoritative map-renderable bridge. Normal CLI calls are
-- delegated byte-for-byte to the implementation; only a preview-map process
-- explicitly launched with SECOND_RITE_RENDERABLE_REQUEST takes the bridge
-- path.
local cli = require("engine.cli_tools_impl")
local ordinaryPreviewMap = cli.runPreviewMap

function cli.runPreviewMap(mapId, x, y, dir, loader)
    local requestPath = os.getenv("SECOND_RITE_RENDERABLE_REQUEST")
    if not requestPath or requestPath == "" then
        return ordinaryPreviewMap(mapId, x, y, dir, loader)
    end
    return require("engine.editor_renderable_bridge").run(requestPath, mapId, loader, cli)
end

return cli
