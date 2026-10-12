[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$entryPoint = Join-Path $projectRoot 'main.py'
$releaseDir = Join-Path $projectRoot 'release'
$workDir = Join-Path $projectRoot 'build\pyinstaller'
$imageDirName = ([char]0x56FE) + ([char]0x7247)
$imageDir = Join-Path $projectRoot $imageDirName

if (-not (Test-Path -LiteralPath $entryPoint)) {
    throw "Entry point not found: $entryPoint"
}

$arguments = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--windowed',
    '--name', 'StudyPet',
    '--distpath', $releaseDir,
    '--workpath', $workDir,
    '--specpath', $workDir,
    '--collect-submodules', 'keyring',
    '--hidden-import', 'keyring.backends.Windows',
    '--add-data', "$projectRoot\resources;resources",
    '--add-data', "$imageDir;$imageDirName",
    $entryPoint
)

Write-Host 'Building StudyPet for Windows...' -ForegroundColor Cyan
& python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code: $LASTEXITCODE"
}

Write-Host "Build complete: $releaseDir\StudyPet\StudyPet.exe" -ForegroundColor Green
Write-Host 'Runtime data is stored next to StudyPet.exe in data and should not be committed to Git.' -ForegroundColor Yellow
