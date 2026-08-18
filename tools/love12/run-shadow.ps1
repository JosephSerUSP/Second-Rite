param(
    [Parameter(Mandatory=$true)][string]$Love11,
    [Parameter(Mandatory=$true)][string]$Love12,
    [Parameter(Mandatory=$true)][string]$GameRoot,
    [Parameter(Mandatory=$true)][string]$ResultsRoot,
    [Parameter(Mandatory=$true)][string]$RepoRoot,
    [string]$VulkanIcd = ''
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $ResultsRoot -Force | Out-Null

function Invoke-BoundedLove {
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][string]$Executable,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [int]$TimeoutSeconds = 180
    )

    $stdout = Join-Path $ResultsRoot "$Label.txt"
    $stderr = Join-Path $ResultsRoot "$Label.stderr.txt"
    Remove-Item $stdout,$stderr -Force -ErrorAction SilentlyContinue
    Write-Host "LOVE12_SHADOW START $Label :: $Executable $($Arguments -join ' ')"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $RepoRoot `
        -NoNewWindow -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $finished = $process.WaitForExit($TimeoutSeconds * 1000)
    if (-not $finished) {
        try { $process.Kill($true) } catch {}
        $sw.Stop()
        Write-Host "LOVE12_SHADOW RESULT $Label timeout ms=$($sw.ElapsedMilliseconds)"
        return [pscustomobject]@{ Label=$Label; ExitCode=124; TimedOut=$true; Milliseconds=$sw.ElapsedMilliseconds; Stdout=$stdout; Stderr=$stderr }
    }
    $sw.Stop()
    $process.Refresh()
    Write-Host "LOVE12_SHADOW RESULT $Label exit=$($process.ExitCode) ms=$($sw.ElapsedMilliseconds)"
    if (Test-Path $stdout) { Get-Content $stdout | Write-Host }
    if (Test-Path $stderr) {
        Get-Content $stderr | ForEach-Object { if ($_ -ne '') { Write-Host "STDERR $Label $_" } }
    }
    return [pscustomobject]@{ Label=$Label; ExitCode=$process.ExitCode; TimedOut=$false; Milliseconds=$sw.ElapsedMilliseconds; Stdout=$stdout; Stderr=$stderr }
}

function Require-Success($result, [string]$meaning) {
    if ($result.ExitCode -ne 0) {
        throw "$meaning failed for $($result.Label) (exit $($result.ExitCode), timeout=$($result.TimedOut))"
    }
}

function Clear-GeoCache {
    Remove-Item (Join-Path $env:APPDATA 'LOVE\SecondRite\geocache') -Recurse -Force -ErrorAction SilentlyContinue
}

# Validation: same staged Project, same runner, only runtime/backend changes.
$r = Invoke-BoundedLove 'validate-11-opengl' $Love11 @($GameRoot, 'validate') 120
Require-Success $r 'validation'
$r = Invoke-BoundedLove 'validate-12-opengl' $Love12 @('--renderers','opengl',$GameRoot,'validate') 120
Require-Success $r 'validation'

$vulkanAvailable = $false
if ($VulkanIcd) {
    $env:VK_DRIVER_FILES = $VulkanIcd
    $r = Invoke-BoundedLove 'validate-12-vulkan' $Love12 @('--renderers','vulkan',$GameRoot,'validate') 120
    $vulkanAvailable = ($r.ExitCode -eq 0)
} else {
    'No Lavapipe/Vulkan ICD was found in the pinned Mesa bundle.' | Out-File (Join-Path $ResultsRoot 'validate-12-vulkan.txt') -Encoding utf8
}
@{ available=$vulkanAvailable; icd=if($VulkanIcd){$VulkanIcd}else{$null} } | ConvertTo-Json | Out-File (Join-Path $ResultsRoot 'vulkan-status.json') -Encoding utf8

# Cold map build: clear compiled geometry before each repeat. The profiler is
# production authority; this wrapper only selects runtime/backend and bounds it.
foreach ($map in @(2,15)) {
    foreach ($repeat in 1..3) {
        foreach ($spec in @(
            @{ Label='11-opengl'; Exe=$Love11; Renderer='' },
            @{ Label='12-opengl'; Exe=$Love12; Renderer='opengl' }
        )) {
            Clear-GeoCache
            $label = "profile-$($spec.Label)-map$map-r$repeat"
            $args = if ($spec.Renderer) { @('--renderers',$spec.Renderer,$GameRoot,'profile-map-build',"$map",'1','1','fresh') } else { @($GameRoot,'profile-map-build',"$map",'1','1','fresh') }
            $r = Invoke-BoundedLove $label $spec.Exe $args 180
            Require-Success $r 'map-build profile'
            if (-not (Select-String -Path $r.Stdout -Pattern 'MAP BUILD PROFILE' -Quiet)) { throw "$label emitted no profile marker" }
        }
        if ($vulkanAvailable) {
            Clear-GeoCache
            $label = "profile-12-vulkan-map$map-r$repeat"
            $r = Invoke-BoundedLove $label $Love12 @('--renderers','vulkan',$GameRoot,'profile-map-build',"$map",'1','1','fresh') 180
            Require-Success $r 'map-build profile'
            if (-not (Select-String -Path $r.Stdout -Pattern 'MAP BUILD PROFILE' -Quiet)) { throw "$label emitted no profile marker" }
        }
    }
}

# Frame + graphics memory observation. Install the shadow wrapper only in the
# disposable staged Project; the repository and production Project stay clean.
$stageMain = Join-Path $GameRoot 'main.lua'
$stageReal = Join-Path $GameRoot 'main.shadow-real.lua'
Copy-Item $stageMain $stageReal -Force
Copy-Item (Join-Path $RepoRoot 'tools\love12\shadow-main.lua') $stageMain -Force
try {
    $env:SECOND_RITE_SHADOW_WARMUP='60'
    $env:SECOND_RITE_SHADOW_FRAMES='180'
    foreach ($map in @(2,15)) {
        $env:SECOND_RITE_SHADOW_MAP_ID="$map"
        $r = Invoke-BoundedLove "frame-11-opengl-map$map" $Love11 @($GameRoot) 180
        Require-Success $r 'frame/memory probe'
        $r = Invoke-BoundedLove "frame-12-opengl-map$map" $Love12 @('--renderers','opengl',$GameRoot) 180
        Require-Success $r 'frame/memory probe'
        if ($vulkanAvailable) {
            $r = Invoke-BoundedLove "frame-12-vulkan-map$map" $Love12 @('--renderers','vulkan',$GameRoot) 180
            Require-Success $r 'frame/memory probe'
        }
    }
} finally {
    Move-Item $stageReal $stageMain -Force
}

function Capture-Visual([string]$Label, [string]$Executable, [string]$Renderer) {
    Remove-Item (Join-Path $RepoRoot 'tools\golden\screens') -Recurse -Force -ErrorAction SilentlyContinue
    $args = if ($Renderer) { @('--renderers',$Renderer,$GameRoot,'screenshots') } else { @($GameRoot,'screenshots') }
    $r = Invoke-BoundedLove "capture-$Label" $Executable $args 180
    Require-Success $r 'visual capture'
    python (Join-Path $RepoRoot 'tools\golden\screens.py') capture --input $r.Stdout
    if ($LASTEXITCODE -ne 0) { throw "$Label screenshot decode failed (exit $LASTEXITCODE)" }
    Copy-Item (Join-Path $RepoRoot 'tools\golden\screens') (Join-Path $ResultsRoot $Label) -Recurse -Force
}

# Same-runner repeat is the noise control. Only compare 12 against 11 when the
# 11a/11b repeat itself is stable enough to interpret.
Capture-Visual 'visual-11a-opengl' $Love11 ''
Capture-Visual 'visual-11b-opengl' $Love11 ''
Capture-Visual 'visual-12-opengl' $Love12 'opengl'
if ($vulkanAvailable) {
    try { Capture-Visual 'visual-12-vulkan' $Love12 'vulkan' }
    catch { Write-Warning "Vulkan visual capture failed separately: $($_.Exception.Message)" }
}

Write-Host "LOVE12_SHADOW COMPLETE vulkan=$vulkanAvailable"
