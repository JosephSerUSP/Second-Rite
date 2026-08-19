local socket = require("socket")
local json = require("engine.data.json")
local authored_storage = require("engine.data.authored_storage")

local server = {}
local tcpListener = nil
local active = false
server.configReloaded = false

-- Shared authored-storage metadata owns the database resources exposed by the
-- developer save server. This intentionally replaces the second hand-written
-- DATA_FILES list that used to drift from tools/editor/server.js.
local DATA_FILES = authored_storage.bulkEditableResources()
local DATA_FILE_SET = {}
for _, name in ipairs(DATA_FILES) do DATA_FILE_SET[name] = true end

function server.start()
    tcpListener = socket.bind("127.0.0.1", 8081)
    if tcpListener then
        tcpListener:settimeout(0)
        active = true
        print("Developer hot-reload server running on http://127.0.0.1:8081/")

        -- Ping the editor server to notify successful startup
        pcall(function()
            local http = require("socket.http")
            http.TIMEOUT = 0.5
            http.request("http://127.0.0.1:8080/ping?scene=game_loaded")
        end)
    else
        print("Failed to bind developer hot-reload server to port 8081")
    end
end

function server.stop()
    if tcpListener then
        tcpListener:close()
        tcpListener = nil
    end
    active = false
end

function server.isActive()
    return active
end

local function sendResponse(client, status, contentType, body)
    local headers = {
        "HTTP/1.1 " .. status,
        "Content-Type: " .. contentType,
        "Access-Control-Allow-Origin: http://127.0.0.1:8080",
        "Access-Control-Allow-Methods: GET, POST, OPTIONS",
        "Access-Control-Allow-Headers: Content-Type",
        "Content-Length: " .. tostring(#body),
        "Connection: close",
        "",
        body
    }
    client:send(table.concat(headers, "\r\n"))
    client:close()
end

local function reloadAuthoredData()
    local loader = require("engine.data.loader")
    loader.init()

    local config = require("engine.config")
    config.load()

    server.configReloaded = true
end

local function readPayload(client, contentLength)
    if contentLength <= 0 then return nil, "Save request had no body." end
    local body = client:receive(contentLength)
    if not body or body == "" then return nil, "Save request had no body." end
    local ok, payload = pcall(json.decode, body)
    if not ok or type(payload) ~= "table" then
        return nil, "Failed to parse save data."
    end
    return payload
end

local function validateSavePayload(payload)
    for name in pairs(payload) do
        if type(name) == "string" and name:sub(1, 1) ~= "_" and not DATA_FILE_SET[name] then
            error("Unsupported authored resource in save payload: " .. tostring(name))
        end
    end

    local pending = {}
    for _, name in ipairs(DATA_FILES) do
        local value = payload[name]
        if value ~= nil then
            -- Validate every supplied resource before the first write so a bad
            -- top-level shape cannot leave a partially updated authored set.
            authored_storage.validateResource(name, value)
            table.insert(pending, { name = name, value = value })
        end
    end
    if #pending == 0 then error("Save payload contains no authored resources") end
    return pending
end

local function persistPayload(payload)
    local pending = validateSavePayload(payload)
    local root = require("engine.data.loader").root
    for _, entry in ipairs(pending) do
        authored_storage.writeResource(root, entry.name, entry.value)
    end
end

function server.update(dt)
    if not active or not tcpListener then return end

    local client = tcpListener:accept()
    if client then
        client:settimeout(1.0)
        local line = client:receive()
        if line then
            local method, path = line:match("^(%S+)%s+(%S+)%s+HTTP/")
            if method then
                if method == "OPTIONS" then
                    sendResponse(client, "200 OK", "text/plain", "")
                elseif method == "GET" and path == "/reload" then
                    reloadAuthoredData()
                    sendResponse(client, "200 OK", "application/json",
                        json.encode({ success = true, message = "Reloaded config and database" }))
                elseif method == "GET" and path == "/data" then
                    local ok, result = pcall(function()
                        local data = {}
                        local root = require("engine.data.loader").root
                        for _, name in ipairs(DATA_FILES) do
                            data[name] = authored_storage.loadResource(root, name)
                        end
                        return data
                    end)
                    if ok then
                        sendResponse(client, "200 OK", "application/json", json.encode(result))
                    else
                        sendResponse(client, "500 Internal Server Error", "application/json",
                            json.encode({ success = false, message = tostring(result) }))
                    end
                elseif method == "POST" and path == "/save" then
                    local contentLength = 0
                    while true do
                        local headerLine = client:receive()
                        if not headerLine or headerLine == "" then break end
                        local len = headerLine:match("[Cc]ontent%-[Ll]ength:%s*(%d+)")
                        if len then contentLength = tonumber(len) end
                    end

                    local payload, parseError = readPayload(client, contentLength)
                    if not payload then
                        sendResponse(client, "400 Bad Request", "application/json",
                            json.encode({ success = false, message = parseError }))
                    else
                        local ok, saveError = pcall(function()
                            persistPayload(payload)
                            reloadAuthoredData()
                        end)
                        if ok then
                            sendResponse(client, "200 OK", "application/json", json.encode({
                                success = true,
                                message = "Saved and hot-reloaded successfully!"
                            }))
                        else
                            sendResponse(client, "400 Bad Request", "application/json", json.encode({
                                success = false,
                                message = tostring(saveError)
                            }))
                        end
                    end
                else
                    sendResponse(client, "404 Not Found", "text/plain", "Not Found")
                end
            else
                client:close()
            end
        else
            client:close()
        end
    end
end

return server
