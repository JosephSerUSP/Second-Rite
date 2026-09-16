[CmdletBinding()]
param(
    [ValidateSet('lab','validate','critics','rate','candidate')]
    [string]$Mode = 'lab',
    [ValidateSet('A','B','C')]
    [string]$Candidate = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$args = @("$root\tools\gauntlet\PLAY_GAUNTLET.js", "--$Mode")
if ($Mode -eq 'candidate') { $args += $Candidate }
Write-Host 'PLAY_GAUNTLET READY FOR OWNER PLAY' -ForegroundColor Green
& node @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
