param(
    [Parameter(Mandatory = $true)]
    [string]$Lovec,

    [int]$MaxSeconds = 10
)

$ErrorActionPreference = "Stop"

$tempRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$probeRoot = Join-Path $tempRoot ("thestra-love-boot-negative-{0}" -f $PID)

function Invoke-LoveProbe {
    param(
        [string]$Executable,
        [string]$ProjectRoot,
        [int]$TimeoutSeconds
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Executable
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.ArgumentList.Add($ProjectRoot)
    $startInfo.ArgumentList.Add("validate")

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo

    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not $process.Start()) {
        throw "failed to start LOVE negative-control probe"
    }

    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        try { $process.Kill($true) } catch { }
        throw "LOVE boot negative control exceeded ${TimeoutSeconds}s; a parser/boot failure must fail before bridge-style timeouts"
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

try {
    git worktree add --detach $probeRoot HEAD | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "failed to create detached negative-control worktree"
    }

    $interpreter = Join-Path $probeRoot "engine/interpreter.lua"
    if (-not (Test-Path $interpreter)) {
        throw "negative-control target missing: $interpreter"
    }

    # Deliberately plant the same class of defect that motivated #626: a Lua
    # parse failure in a runtime module loaded during normal validation. Keep it
    # isolated in a detached worktree so the commit under test is never mutated.
    Add-Content -Path $interpreter -Value "`nfunction __thestra_deliberate_parse_error("

    $result = Invoke-LoveProbe -Executable $Lovec -ProjectRoot $probeRoot -TimeoutSeconds $MaxSeconds
    Write-Host $result.Output
    Write-Host ("negative-control exit={0} elapsed={1:N3}s" -f $result.ExitCode, $result.Elapsed.TotalSeconds)

    if ($result.ExitCode -eq 0) {
        throw "LOVE boot negative control unexpectedly succeeded with malformed engine/interpreter.lua"
    }
    if ($result.Output -notmatch "(?i)(syntax|unexpected|near|<eof>)") {
        throw "LOVE boot negative control failed, but did not report a recognizable Lua parse error"
    }

    Write-Host "LOVE BOOT NEGATIVE CONTROL OK"
}
finally {
    if (Test-Path $probeRoot) {
        git worktree remove --force $probeRoot | Out-Null
    }
}
