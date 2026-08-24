[CmdletBinding()]
param(
    [string]$OutputDirectory = "$(Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'release')"
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$buildId = [guid]::NewGuid().ToString('N').Substring(0, 12)
$workingDirectory = Join-Path $repositoryRoot "build\windows-$buildId"
$bundleDirectory = Join-Path $workingDirectory 'ecti-windows-x64'
$virtualEnvironment = Join-Path $workingDirectory '.venv'

function Copy-SourceTree(
    [string]$Source,
    [string]$Destination,
    [string[]]$ExcludedDirectories = @()
) {
    $arguments = @($Source, $Destination, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/XF', '.env')
    if ($ExcludedDirectories.Count -gt 0) {
        $arguments += '/XD'
        $arguments += $ExcludedDirectories
    }
    & robocopy @arguments
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to copy $Source (robocopy exit $LASTEXITCODE)"
    }
}

New-Item -ItemType Directory -Path $bundleDirectory, $OutputDirectory -Force | Out-Null
python -m venv $virtualEnvironment
$python = Join-Path $virtualEnvironment 'Scripts\python.exe'
$pyinstaller = Join-Path $virtualEnvironment 'Scripts\pyinstaller.exe'
& $python -m pip install --upgrade pip
& $python -m pip install (Join-Path $repositoryRoot 'sensor') 'pyinstaller==6.22.2'
& $pyinstaller --onefile --name ecti-sensor --paths (Join-Path $repositoryRoot 'sensor') --distpath $bundleDirectory --workpath (Join-Path $workingDirectory 'pyinstaller') --specpath $workingDirectory (Join-Path $repositoryRoot 'sensor\ecti_sensor\__main__.py')

Copy-SourceTree (Join-Path $repositoryRoot 'backend') (Join-Path $bundleDirectory 'backend') @('__pycache__', '.pytest_cache', '.ruff_cache', '.venv')
Copy-SourceTree (Join-Path $repositoryRoot 'frontend') (Join-Path $bundleDirectory 'frontend') @('node_modules', 'dist', 'coverage')
New-Item -ItemType Directory -Path (Join-Path $bundleDirectory 'infra'), (Join-Path $bundleDirectory 'installer') -Force | Out-Null
Copy-Item (Join-Path $repositoryRoot 'infra\compose.desktop.yml') (Join-Path $bundleDirectory 'infra\compose.desktop.yml')
Copy-SourceTree (Join-Path $repositoryRoot 'installer\windows') (Join-Path $bundleDirectory 'installer\windows')

$archive = Join-Path $OutputDirectory 'ecti-windows-x64.zip'
Compress-Archive -Path (Join-Path $bundleDirectory '*') -DestinationPath $archive -Force
Write-Host "Created $archive" -ForegroundColor Green
