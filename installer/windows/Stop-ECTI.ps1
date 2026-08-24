$ErrorActionPreference = 'Stop'
$installDirectory = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$sensorExecutable = Join-Path $installDirectory 'ecti-sensor.exe'
Get-CimInstance Win32_Process |
    Where-Object { $_.ExecutablePath -eq $sensorExecutable } |
    ForEach-Object { Stop-Process -Id $_.ProcessId }
Push-Location $installDirectory
try {
    docker compose --env-file .env -f compose.desktop.yml stop
} finally {
    Pop-Location
}
