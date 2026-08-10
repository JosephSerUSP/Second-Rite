[CmdletBinding()]
param(
    [ValidateSet("g5", "g6", "all")]
    [string]$Gate = "all",
    [int]$StepTimeout = 180,
    [int]$GateTimeout = 1200
)

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Set-Location $rootDir

# Prefer the Windows Python launcher. Some developer machines have a shadowing
# python.exe app alias earlier on PATH; once record.py is running it uses its
# concrete sys.executable for the gate's temporary Python shim.
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 "tools/golden/record.py" --gate $Gate --step-timeout $StepTimeout --gate-timeout $GateTimeout
} else {
    & python "tools/golden/record.py" --gate $Gate --step-timeout $StepTimeout --gate-timeout $GateTimeout
}
exit $LASTEXITCODE
