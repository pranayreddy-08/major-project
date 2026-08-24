$ErrorActionPreference = 'Stop'
$installDirectory = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$dataDirectory = Join-Path $env:LOCALAPPDATA 'ECTI\data'
Push-Location $installDirectory
try {
    docker compose --env-file .env -f compose.desktop.yml up -d
} finally {
    Pop-Location
}
$sensorExecutable = Join-Path $installDirectory 'ecti-sensor.exe'
$running = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $sensorExecutable }
if (-not $running) {
    Start-Process -FilePath $sensorExecutable -ArgumentList "--config `"$dataDirectory\sensor.json`"" -WindowStyle Hidden
}
Start-Process 'http://127.0.0.1:8080'
