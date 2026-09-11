param(
    [string]$MapId = "32",
    [string]$X = "6",
    [string]$Y = "3",
    [string]$Dir = "S",
    [string]$OutName = "test_wagon_preview.png"
)
$lovec = "C:\Program Files\LOVE\lovec.exe"
$stageAbs = (Resolve-Path "out/stage").Path
$artifactDir = "C:\Users\josep\.gemini\antigravity\brain\4ba4a222-181c-4731-9be7-d3f745ffa175"
$temp = [System.IO.Path]::GetTempFileName()
try {
    Push-Location $stageAbs
    try {
        & $lovec $stageAbs preview-map $MapId $X $Y $Dir | Out-File -FilePath $temp -Encoding utf8
    } finally { Pop-Location }
    $raw = Get-Content $temp -Raw
    if ($raw -match 'PREVIEW BEGIN\r?\n([\s\S]*?)\r?\nPREVIEW END') {
        $json = $matches[1] | ConvertFrom-Json
        if ($json.image) {
            $bytes = [Convert]::FromBase64String($json.image)
            [IO.File]::WriteAllBytes((Join-Path $artifactDir $OutName), $bytes)
            Write-Host "Success: $($bytes.Length) bytes saved to $OutName"
        } else {
            Write-Host "No image: $($json.error)"
        }
    } else {
        Write-Host "No match"
    }
} finally {
    Remove-Item $temp -Force -ErrorAction SilentlyContinue
}
