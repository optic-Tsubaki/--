[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$entryPoint = Join-Path $projectRoot 'main.py'
$releaseDir = Join-Path $projectRoot 'release'
$workDir = Join-Path $projectRoot 'build\pyinstaller'
$appDir = Join-Path $releaseDir 'StudyPet'
$packageDir = Join-Path $releaseDir 'StudyPet-Windows'
$packageZip = Join-Path $releaseDir 'StudyPet-Windows.zip'
$imageDirName = ([char]0x56FE) + ([char]0x7247)
$imageDir = Join-Path $projectRoot $imageDirName
$iconPath = Join-Path $projectRoot 'resources\icon\studypet.ico'

if (-not (Test-Path -LiteralPath $entryPoint)) {
    throw "Entry point not found: $entryPoint"
}
if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Application icon not found: $iconPath"
}

$arguments = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--windowed',
    '--name', 'StudyPet',
    '--icon', $iconPath,
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

if (Test-Path -LiteralPath $packageDir) {
    $releaseFullPath = [IO.Path]::GetFullPath($releaseDir).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $packageFullPath = [IO.Path]::GetFullPath($packageDir)
    if (-not $packageFullPath.StartsWith($releaseFullPath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clear package path outside the release directory: $packageFullPath"
    }
    Remove-Item -LiteralPath $packageFullPath -Recurse -Force
}

New-Item -ItemType Directory -Path $packageDir | Out-Null
Copy-Item -Path (Join-Path $appDir '*') -Destination $packageDir -Recurse -Force
Rename-Item -LiteralPath (Join-Path $packageDir 'StudyPet.exe') -NewName 'START StudyPet.exe'

$packageReadme = @(
    'StudyPet AI for Windows',
    '',
    'Double-click "START StudyPet.exe" to launch StudyPet.',
    '',
    'Keep START StudyPet.exe and the _internal folder together.',
    'Your local tasks, reminders, and settings are stored in the data folder.'
)
$packageReadme | Set-Content -LiteralPath (Join-Path $packageDir 'README-START-HERE.txt') -Encoding utf8

if (Test-Path -LiteralPath $packageZip) {
    Remove-Item -LiteralPath $packageZip -Force
}
Compress-Archive -LiteralPath $packageDir -DestinationPath $packageZip -Force

Write-Host "Build complete: $appDir\StudyPet.exe" -ForegroundColor Green
Write-Host "GitHub release package: $packageZip" -ForegroundColor Green
Write-Host 'Runtime data is stored next to StudyPet.exe in data and should not be committed to Git.' -ForegroundColor Yellow
