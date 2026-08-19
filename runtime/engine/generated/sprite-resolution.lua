--[[ Generated with https://github.com/TypeScriptToLua/TypeScriptToLua ]]
-- Lua Library inline imports
local function __TS__StringSubstring(self, start, ____end)
    if ____end ~= ____end then
        ____end = 0
    end
    if ____end ~= nil and start > ____end then
        start, ____end = ____end, start
    end
    if start >= 0 then
        start = start + 1
    else
        start = 1
    end
    if ____end ~= nil and ____end < 0 then
        ____end = 0
    end
    return string.sub(self, start, ____end)
end
-- End of Lua Library inline imports
ThestraSpriteResolutionSemantics = ThestraSpriteResolutionSemantics or ({})
do
    --- Directories are searched in this order and the list is part of the
    -- contract: the first matching stripped basename wins, so reordering these
    -- silently changes which file an ambiguous key resolves to.
    ThestraSpriteResolutionSemantics.ASSET_DIRS = {"assets/smallBattlers", "assets/sprites", "assets/system"}
    local function isPng(name)
        local lower = string.lower(name)
        return #lower > 4 and __TS__StringSubstring(lower, #lower - 4) == ".png"
    end
    local function stripPng(name)
        return __TS__StringSubstring(name, 0, #name - 4)
    end
    --- Lua's `s:sub(1,1):upper() .. s:sub(2):lower()`, without a locale.
    local function capitalizedAscii(value)
        if #value == 0 then
            return value
        end
        return string.upper(__TS__StringSubstring(value, 0, 1)) .. string.lower(__TS__StringSubstring(value, 1))
    end
    --- The fixed candidate list for a file key, in probe order. A host tries
    -- each in turn and takes the first that exists.
    -- 
    -- The order encodes history: smallBattlers is probed with three case
    -- spellings before sprites and system are consulted at all, so a battler
    -- named in any casing keeps resolving to the battler rather than to a
    -- same-named system sprite.
    function ThestraSpriteResolutionSemantics.candidatePaths(fileKey)
        return {
            ("assets/smallBattlers/" .. capitalizedAscii(fileKey)) .. ".png",
            ("assets/smallBattlers/" .. fileKey) .. ".png",
            ("assets/smallBattlers/" .. string.lower(fileKey)) .. ".png",
            ("assets/sprites/" .. fileKey) .. ".png",
            ("assets/system/" .. fileKey) .. ".png",
            ("assets/system/" .. capitalizedAscii(fileKey)) .. ".png"
        }
    end
    --- Build the stripped-basename lookup index from a host-supplied inventory.
    -- 
    -- `entries` must already be in the host's directory order, and within a
    -- directory in the host's own listing order, because first-match-wins is
    -- the historical contract. Non-PNG entries are ignored.
    -- 
    -- The caller passes `fileKeyOf`, which strips `[k=v]` tokens from a stem —
    -- that is the sprite-timing leaf's `parseKey().fileKey`. Keeping it a
    -- parameter is what stops this leaf from duplicating the token grammar.
    function ThestraSpriteResolutionSemantics.buildFileIndex(entries, fileKeyOf)
        local index = {}
        do
            local i = 0
            while i < #entries do
                do
                    local entry = entries[i + 1]
                    if not entry or not isPng(entry.name) then
                        goto __continue10
                    end
                    local stem = stripPng(entry.name)
                    local base = string.lower(fileKeyOf(stem))
                    if index[base] ~= nil then
                        goto __continue10
                    end
                    index[base] = {path = (entry.dir .. "/") .. entry.name, stem = stem}
                end
                ::__continue10::
                i = i + 1
            end
        end
        return index
    end
    --- The full ordered probe list for a key: the fixed candidates, then the
    -- indexed hit if there is one. An indexed path goes LAST so an exact
    -- conventional filename always beats a token-carrying variant.
    function ThestraSpriteResolutionSemantics.probeOrder(fileKey, index)
        local paths = ThestraSpriteResolutionSemantics.candidatePaths(fileKey)
        local indexed = index and index[string.lower(fileKey)] or nil
        if indexed then
            paths[#paths + 1] = indexed.path
        end
        return paths
    end
    --- The indexed entry for a key, or null. Hosts read `stem` for filename tokens.
    function ThestraSpriteResolutionSemantics.indexedFor(fileKey, index)
        if not index then
            return nil
        end
        local hit = index[string.lower(fileKey)]
        local ____temp_0
        if hit == nil then
            ____temp_0 = nil
        else
            ____temp_0 = hit
        end
        return ____temp_0
    end
end
-- THES_SHARED_LUA_SPRITE_RESOLUTION: generated module adapter; do not edit.
return ThestraSpriteResolutionSemantics
