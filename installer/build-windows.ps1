$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$version = '0.3.0'
$dist = 'dist/DexterFusionStudio'
$release = 'release'

Write-Host "Installing packaging libraries..."
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed' }
python -m pip install 'pyinstaller>=6.11,<7' 'faster-whisper>=1.1,<2'
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies unavailable' }

Write-Host "Compiling standalone Dexter Fusion Studio for Windows x64..."
python -m PyInstaller --noconfirm --clean --windowed --onedir --name DexterFusionStudio --collect-all faster_whisper --collect-all ctranslate2 --collect-all av --collect-all tokenizers --collect-all huggingface_hub main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
if (!(Test-Path "$dist/DexterFusionStudio.exe")) { throw 'No Windows executable found' }

Write-Host "Downloading complete FFmpeg/ffprobe GPL shared build from BtbN..."
$releaseInfo = Invoke-RestMethod -Uri 'https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest' -Headers @{ Accept='application/vnd.github+json'; 'User-Agent'='DexterStudioBuild' }
$asset = $releaseInfo.assets | Where-Object { $_.name -eq 'ffmpeg-master-latest-win64-gpl-shared.zip' } | Select-Object -First 1
if (!$asset) { throw 'Expected ffmpeg GPL release not found' }
New-Item -ItemType Directory -Force -Path build/ffmpeg-download | Out-Null
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile build/ffmpeg-download.zip
Expand-Archive -Path build/ffmpeg-download.zip -DestinationPath build/ffmpeg-download -Force
$exe = Get-ChildItem -Path build/ffmpeg-download -Recurse -File -Filter ffmpeg.exe | Select-Object -First 1
if (!$exe) { throw 'Missing FFmpeg executable in upstream package' }
$sourceBin = $exe.Directory.FullName
$destination = "$dist/bin"
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Copy-Item -Path (Join-Path $sourceBin '*') -Destination $destination -Recurse -Force
if (!(Test-Path "$destination/ffprobe.exe")) { throw 'Missing ffprobe' }
$legal = Get-ChildItem -Path build/ffmpeg-download -File -Recurse |
    Where-Object { $_.Name -match '^(COPYING|LICENSE)' } |
    Select-Object -First 6
foreach ($item in $legal) {
    Copy-Item -Path $item.FullName -Destination (Join-Path $destination ('UPSTREAM-' + $item.Name)) -Force
}

$ffmpeg = (Resolve-Path "$destination/ffmpeg.exe").Path
$versionText = & $ffmpeg -version
$versionText | Select-Object -First 10 | Out-File -Encoding utf8 "$dist/ffmpeg-version.txt"
$encoders = & $ffmpeg -hide_banner -encoders
if (!($encoders | Select-String 'libx264')) { throw 'H264 encoder is missing' }
$filters = & $ffmpeg -hide_banner -filters
if (!($filters | Select-String 'subtitles')) { throw 'Subtitles filter is missing' }

Write-Host "Running genuine FFmpeg Python and bundled EXE tests..."
$env:PATH = (Resolve-Path $destination).Path + ';' + $env:PATH
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Unit or export tests failed' }
& "$dist/DexterFusionStudio.exe" --self-check
if ($LASTEXITCODE -ne 0) { throw 'Frozen EXE startup/self-check failed' }

$tool = Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Inno Setup 6/ISCC.exe'
if (!(Test-Path $tool)) {
    Write-Host "Installing Inno Setup..."
    choco install innosetup --yes --no-progress
}
if (!(Test-Path $tool)) { throw 'Inno Setup compiler not found' }

New-Item -ItemType Directory -Force -Path $release | Out-Null
Write-Host "Creating click-to-install setup executable..."
& $tool "installer/windows.iss"
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed' }

Write-Host "Creating portable backup..."
Compress-Archive -Path "$dist/*" -DestinationPath "$release/Dexter-Fusion-Studio-Portable-v$version.zip" -CompressionLevel Optimal -Force

$setup = "$release/Dexter-Fusion-Studio-Setup-v$version.exe"
if (!(Test-Path $setup)) { throw 'Installer is missing' }
Write-Host "Built installer: $setup"
Write-Host "Built portable: $release/Dexter-Fusion-Studio-Portable-v$version.zip"
