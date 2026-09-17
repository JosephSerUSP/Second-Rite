return function(suite_name, failed, passed)
    if failed > 0 then
        print("FAIL: " .. suite_name .. " (" .. failed .. " failing)")
        os.exit(1)
    else
        print("PASS: " .. suite_name)
    end
end
