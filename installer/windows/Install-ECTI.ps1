[CmdletBinding()]
param(
    [string]$InstallDirectory = "$env:LOCALAPPDATA\ECTI"
)

$ErrorActionPreference = 'Stop'
$sourceDirectory = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker Desktop is required. Install and start Docker Desktop, then run this installer again.'
}
docker info | Out-Null

function New-HexSecret([int]$Bytes = 32) {
    $buffer = New-Object byte[] $Bytes
    [Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    return [Convert]::ToHexString($buffer).ToLowerInvariant()
}

$resolvedSource = [IO.Path]::GetFullPath($sourceDirectory)
$resolvedTarget = [IO.Path]::GetFullPath($InstallDirectory)
New-Item -ItemType Directory -Path $resolvedTarget -Force | Out-Null
if ($resolvedSource -ne $resolvedTarget) {
    Copy-Item -LiteralPath "$resolvedSource\backend" -Destination $resolvedTarget -Recurse -Force
    Copy-Item -LiteralPath "$resolvedSource\frontend" -Destination $resolvedTarget -Recurse -Force
    Copy-Item -LiteralPath "$resolvedSource\infra\compose.desktop.yml" -Destination "$resolvedTarget\compose.desktop.yml" -Force
    Copy-Item -LiteralPath "$resolvedSource\ecti-sensor.exe" -Destination "$resolvedTarget\ecti-sensor.exe" -Force
    $installerTarget = Join-Path $resolvedTarget 'installer\windows'
    New-Item -ItemType Directory -Path $installerTarget -Force | Out-Null
    Copy-Item -Path (Join-Path $PSScriptRoot '*') -Destination $installerTarget -Recurse -Force
}

$environmentPath = Join-Path $resolvedTarget '.env'
$sensorToken = New-HexSecret
@(
    "POSTGRES_PASSWORD=$(New-HexSecret)"
    "JWT_SECRET=$(New-HexSecret 48)"
    "SENSOR_INGEST_TOKEN=$sensorToken"
) | Set-Content -LiteralPath $environmentPath -Encoding ascii

$dataDirectory = Join-Path $env:LOCALAPPDATA 'ECTI\data'
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
@{
    api_url = 'http://127.0.0.1:8000'
    token = $sensorToken
    sensor_id = "windows-$($env:COMPUTERNAME.ToLowerInvariant())-$([guid]::NewGuid().ToString('N').Substring(0,12))"
    interval_seconds = 60
    state_file = 'sensor-state.json'
    log_file = 'sensor.log'
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dataDirectory 'sensor.json') -Encoding utf8

Push-Location $resolvedTarget
try {
    docker compose --env-file .env -f compose.desktop.yml up --build -d
} finally {
    Pop-Location
}

$sensorExecutable = Join-Path $resolvedTarget 'ecti-sensor.exe'
$sensorArguments = "--config `"$dataDirectory\sensor.json`""
Start-Process -FilePath $sensorExecutable -ArgumentList $sensorArguments -WindowStyle Hidden
Start-Process 'http://127.0.0.1:8080'
Write-Host 'ECTI is installed for this Windows user. Create your owner account in the browser.' -ForegroundColor Green
Write-Host 'Run installer\windows\Start-ECTI.ps1 after a reboot to start the local sensor again.'
