# DEXTER bounded local worker bootstrap. Executes only after user runs this script on Windows.
# The supervisor creates isolated git worktrees; this script does not push or merge.
[CmdletBinding()]
param(
  [switch]$InstallDependencies,
  [switch]$ScraperOnly,
  [switch]$Resume,
  [switch]$Plan,
  [string]$Project = (Join-Path $env:USERPROFILE 'DEXTER-LOCAL\1UP-ANIME')
)
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:USERPROFILE 'DEXTER-LOCAL'
$supervisor = Join-Path $PSScriptRoot 'mission_supervisor.py'
$queue = Join-Path $PSScriptRoot 'mission_queue.json'
if (!(Test-Path $supervisor) -or !(Test-Path $queue)) {
  throw 'Falta mission_supervisor.py o mission_queue.json. Usa la rama del PR #30.'
}
if ($InstallDependencies) {
  & (Join-Path $PSScriptRoot 'START-DEXTER.ps1') -Install
}
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'Python no esta disponible en esta terminal. Ejecuta START-DEXTER.ps1 -Install y reabre PowerShell.'
}
if ($Plan) {
  & python $supervisor --project $Project --queue $queue --plan
  if ($LASTEXITCODE -ne 0) { throw 'Fallo el plan de mision' }
  return
}
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
  throw 'Git no esta disponible. Ejecuta START-DEXTER.ps1 -Install y reabre PowerShell.'
}
if (!(Test-Path (Join-Path $Project '.git'))) {
  if (Test-Path $Project) { throw 'Ya existe la carpeta del proyecto, pero no contiene un repositorio Git.' }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Project) | Out-Null
  & git clone 'https://github.com/H4CKLABORATORY/1UP-ANIME.git' $Project
  if ($LASTEXITCODE -ne 0) { throw 'Fallo git clone 1UP Anime' }
}
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (-not $ScraperOnly) {
  if (!(Test-Path $venvPython)) {
    & python -m venv (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de Python' }
  }
  & $venvPython -m pip show aider-chat *> $null
  if ($LASTEXITCODE -ne 0) {
    Write-Host 'Instalando Aider solo en el entorno local del agente...'
    & $venvPython -m pip install 'aider-chat>=0.86,<1'
    if ($LASTEXITCODE -ne 0) { throw 'Fallo instalacion de Aider' }
  }
}
$argsList = @('--project', $Project, '--state-root', (Join-Path $root 'supervisor'), '--queue', $queue)
if ($ScraperOnly) { $argsList += @('--max-tasks', '1') }
if ($Resume) { $argsList += '--resume' }
& python $supervisor @argsList
if ($LASTEXITCODE -ne 0) {
  throw 'La mision se bloqueo o fallo. Lee DEXTER-LOCAL\supervisor\active.json y los logs antes de reintentar.'
}
Write-Host 'Mision completada o pausada con checkpoint. Revisa el reporte antes de publicar.'
