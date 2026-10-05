'use strict';

// Pure source semantics execute locally from the SAME Lua modules used by LOVE.
// This bounded host preloads only the material grammar, shader vocabulary and
// JSON codec. It neither boots a game nor delegates import to a child process.
const fs = require('node:fs');
const path = require('node:path');
const { lua, lauxlib, lualib, to_luastring } = require('fengari');

function parseMtl(runtimeRoot, text) {
    const L = lauxlib.luaL_newstate();
    lualib.luaL_openlibs(L);
    try {
        lua.lua_getglobal(L, to_luastring('package'));
        lua.lua_getfield(L, -1, to_luastring('preload'));
        for (const relative of ['presentation/mtl.lua', 'presentation/retro_mesh_shader.lua', 'engine/data/json.lua',
            'engine/data/vendor/lunajson/decoder.lua', 'engine/data/vendor/lunajson/encoder.lua']) {
            const source = fs.readFileSync(path.join(runtimeRoot, relative));
            if (lauxlib.luaL_loadbuffer(L, source, source.length, to_luastring(relative)) !== lua.LUA_OK) {
                throw new Error(lua.lua_tojsstring(L, -1));
            }
            lua.lua_setfield(L, -2, to_luastring(relative.replace(/\.lua$/, '').replaceAll('/', '.')));
        }
        lua.lua_settop(L, 0);
        lua.lua_pushstring(L, to_luastring(text));
        lua.lua_setglobal(L, to_luastring('MODEL_MTL_TEXT'));
        const program = to_luastring("return require('engine.data.json').encode(require('presentation.mtl').parse(MODEL_MTL_TEXT))");
        if (lauxlib.luaL_loadbuffer(L, program, program.length, to_luastring('model-material-compile')) !== lua.LUA_OK
                || lua.lua_pcall(L, 0, 1, 0) !== lua.LUA_OK) throw new Error(lua.lua_tojsstring(L, -1));
        return JSON.parse(lua.lua_tojsstring(L, -1));
    } finally { lua.lua_close(L); }
}

module.exports = { parseMtl };
