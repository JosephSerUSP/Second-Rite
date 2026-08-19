param(
    [Parameter(Mandatory = $true)]
    [string]$Lovec,

    [int]$MaxSeconds = 10
)

$ErrorActionPreference = "Stop"

$tempRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$probeRoot = Join-Path $tempRoot ("thestra-love-syntax-probe-{0}" -f $PID)
$manifestPath = Join-Path $tempRoot ("thestra-love-syntax-manifest-{0}.txt" -f $PID)
$negativePath = Join-Path $tempRoot ("thestra-love-syntax-negative-{0}.lua" -f $PID)

function Invoke-LoveSyntaxProbe {
    param(
        [string]$Executable,
        [string]$ProbeRoot,
        [string]$Manifest,
        [int]$TimeoutSeconds
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Executable
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.Environment['SDL_AUDIODRIVER'] = 'dummy'
    $startInfo.Environment['THESTRA_LUA_SYNTAX_MANIFEST'] = $Manifest
    $startInfo.ArgumentList.Add($ProbeRoot)

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo

    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not $process.Start()) {
        throw "failed to start LOVE syntax probe"
    }

    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        try { $process.Kill($true) } catch { }
        throw "LOVE syntax probe exceeded ${TimeoutSeconds}s; parser checks must fail before bridge-style timeouts"
    }

    $timer.Stop()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    return @{
        ExitCode = $process.ExitCode
        Elapsed = $timer.Elapsed
        Output = ($stdout + "`n" + $stderr).Trim()
    }
}

function Write-Manifest {
    param([string[]]$Paths)
    $resolved = foreach ($path in $Paths) {
        [System.IO.Path]::GetFullPath($path)
    }
    $resolved | Set-Content -Path $manifestPath -Encoding utf8
}

try {
    New-Item -ItemType Directory -Path $probeRoot -Force | Out-Null

    # This tiny LOVE app never requires Second Rite/Thestra modules. Disable the
    # window/audio modules entirely so the syntax job needs no OpenGL/audio host
    # and cannot perturb the runner used for the repository's ordinary gates.
    @'
function love.conf(t)
    t.window = nil
    t.audio = false
end
'@ | Set-Content -Path (Join-Path $probeRoot 'conf.lua') -Encoding utf8

    # Use the exact Lua parser embedded in the pinned LOVE runtime to compile
    # each source file with loadfile(). A broken game module therefore cannot
    # trap us in the game's own boot/error path before the parser diagnostic.
    @'
function love.load()
    local manifest = assert(os.getenv("THESTRA_LUA_SYNTAX_MANIFEST"), "missing syntax manifest")
    local count = 0
    for filename in io.lines(manifest) do
        if filename ~= "" then
            local chunk, err = loadfile(filename)
            if not chunk then
                io.stderr:write("LUA SYNTAX ERROR: " .. filename .. ": " .. tostring(err) .. "\n")
                love.event.quit(2)
                return
            end
            count = count + 1
        end
    end
    print("LUA SYNTAX OK files=" .. tostring(count))
    love.event.quit(0)
end
'@ | Set-Content -Path (Join-Path $probeRoot 'main.lua') -Encoding utf8

    # Negative control: copy a real runtime module and corrupt only the temporary
    # copy. This proves that the parser harness reports the exact class of defect
    # that motivated #626 without ever booting a malformed game checkout.
    $sourceInterpreter = Join-Path (Get-Location) 'runtime/engine/interpreter.lua'
    if (-not (Test-Path $sourceInterpreter)) {
        throw "negative-control source missing: $sourceInterpreter"
    }
    Copy-Item -Path $sourceInterpreter -Destination $negativePath -Force
    Add-Content -Path $negativePath -Value "`nfunction __thestra_deliberate_parse_error("
    Write-Manifest -Paths @($negativePath)

    $negative = Invoke-LoveSyntaxProbe -Executable $Lovec -ProbeRoot $probeRoot -Manifest $manifestPath -TimeoutSeconds $MaxSeconds
    Write-Host $negative.Output
    Write-Host ("negative-control exit={0} elapsed={1:N3}s" -f $negative.ExitCode, $negative.Elapsed.TotalSeconds)
    if ($negative.ExitCode -eq 0) {
        throw "LOVE syntax negative control unexpectedly accepted malformed Lua"
    }
    if ($negative.Output -notmatch "LUA SYNTAX ERROR") {
        throw "LOVE syntax negative control failed without the causal parser diagnostic"
    }
    Write-Host "LOVE SYNTAX NEGATIVE CONTROL OK"

    # Real gate: syntax-check tracked runtime/test Lua before any normal game boot
    # or bridge subprocess. Deliberately exclude archived/reference/vendor trees;
    # these are not executable repository authority.
    $tracked = git ls-files -- '*.lua'
    if ($LASTEXITCODE -ne 0) { throw "git ls-files failed while building Lua syntax manifest" }
    $runtimeLua = @($tracked | Where-Object {
        $_ -notmatch '^(docs/archive|inspiration|tmp|vendor|node_modules|experiments)/'
    })
    if ($runtimeLua.Count -eq 0) { throw "Lua syntax manifest is unexpectedly empty" }
    Write-Manifest -Paths $runtimeLua

    $real = Invoke-LoveSyntaxProbe -Executable $Lovec -ProbeRoot $probeRoot -Manifest $manifestPath -TimeoutSeconds $MaxSeconds
    Write-Host $real.Output
    Write-Host ("real-syntax exit={0} elapsed={1:N3}s files={2}" -f $real.ExitCode, $real.Elapsed.TotalSeconds, $runtimeLua.Count)
    if ($real.ExitCode -ne 0) {
        throw "tracked Lua syntax check failed"
    }
    if ($real.Output -notmatch "LUA SYNTAX OK") {
        throw "tracked Lua syntax check exited cleanly without success marker"
    }

    Write-Host "LOVE LUA SYNTAX FAIL-FAST OK"
}
finally {
    Remove-Item -Recurse -Force $probeRoot -ErrorAction SilentlyContinue
    Remove-Item -Force $manifestPath -ErrorAction SilentlyContinue
    Remove-Item -Force $negativePath -ErrorAction SilentlyContinue
}
