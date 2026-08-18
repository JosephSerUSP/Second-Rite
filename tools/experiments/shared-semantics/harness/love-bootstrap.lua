local ok, err = xpcall(function()
    dofile("body.lua")
end, debug.traceback)

if not ok then
    io.stderr:write("SHARED_SEMANTICS_LOVE_FAILURE\n")
    io.stderr:write(tostring(err) .. "\n")
    os.exit(1)
end

os.exit(0)
