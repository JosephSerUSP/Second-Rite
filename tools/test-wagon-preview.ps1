param(
    [string]$StageDir = "out/stage",
    [string]$MapId = "32",
    [string]$X = "6",
    [string]$Y = "3",
    [string]$Dir = "S",
    [string]$OutPath = "out/shots/test_wagon_preview.png",
    [string]$Lovec = $env:LOVEC
)

$ErrorActionPreference = "Stop"

if (-not $Lovec) {
    if (Test-Path "C:\Program Files\LOVE\lovec.exe") {
        $Lovec = "C:\Program Files\LOVE\lovec.exe"
    } elseif (Get-Command lovec -ErrorAction SilentlyContinue) {
        $Lovec = (Get-Command lovec).Source
    } else {
        throw "lovec not found"
    }
}

$outParent = Split-Path -Parent $OutPath
if ($outParent -and -not (Test-Path $outParent)) {
    New-Item -ItemType Directory -Path $outParent -Force | Out-Null
}

$stageAbs = (Resolve-Path $StageDir).Path
$temp = [System.IO.Path]::GetTempFileName()
try {
    Push-Location $stageAbs
    try {
        & $Lovec $stageAbs preview-map $MapId $X $Y $Dir | Out-File -FilePath $temp -Encoding ascii
    } finally {
        Pop-Location
    }
    $raw = Get-Content $temp -Raw
    if ($raw -match 'PREVIEW BEGIN\r?\n([\s\S]*?)\r?\nPREVIEW END') {
        $json = $matches[1] | ConvertFrom-Json
        if ($json.image) {
            $bytes = [Convert]::FromBase64String($json.image)
            $targetPath = Join-Path (Get-Location) $OutPath
            [System.IO.File]::WriteAllBytes($targetPath, $bytes)
            Write-Host "Success: $($bytes.Length) bytes saved to $OutPath"
        } else {
            Write-Host "No image: $($json.error)"
        }
    } else {
        Write-Host "No match"
    }
} finally {
    Remove-Item $temp -Force -ErrorAction SilentlyContinue
}
