# Install DEXTER Hermes -> OpenCode bridge using installed Git/Python/OpenCode/Hermes.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ProjectPath,
  [string]$Model = '',
  [switch]$EnableHourly,
  [switch]$RunPilot
)
$ErrorActionPreference = 'Stop'
function Need([string]$name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Falta '$name'. Instala/configura la herramienta y vuelve a ejecutar."
  }
}
Need 'git'
Need 'python'
Need 'opencode'
Need 'hermes'
$project=(Resolve-Path -LiteralPath $ProjectPath -ErrorAction Stop).Path
if (-not (Test-Path -LiteralPath (Join-Path $project '.git'))) {
  throw "ProjectPath debe apuntar a la raiz de un repositorio Git: $project"
}
$local=if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE 'AppData\Local' }
$hermesHome=if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $local 'hermes' }
$scripts=Join-Path $hermesHome 'scripts'
New-Item -ItemType Directory -Force -Path $scripts | Out-Null
$worker=Join-Path $scripts 'dexter_opencode_tick.py'
$source=Join-Path $PSScriptRoot 'dexter_opencode_tick.py'
if (Test-Path -LiteralPath $source) {
  Copy-Item -LiteralPath $source -Destination $worker -Force
} else {
  $remote='https://raw.githubusercontent.com/H4CKLABORATORY/dexter-fusion-studio/feature/opencode-goals-setup-20261022/tools/hermes-official/dexter_opencode_tick.py'
  Invoke-WebRequest -Uri $remote -OutFile $worker -TimeoutSec 30
}
& python -m py_compile $worker
if ($LASTEXITCODE -ne 0) { throw 'Error de sintaxis en bridge Python' }
& python $worker doctor
if ($LASTEXITCODE -ne 0) { throw 'Git/OpenCode CLI no estan disponibles' }
$root=Join-Path $local 'DEXTER-AUTO'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$queue=Join-Path $root 'tasks.json'
$id='pilot-' + ([IO.Path]::GetFileName($project) -replace '[^A-Za-z0-9_-]','-')
if ($id.Length -gt 45) { $id=$id.Substring(0,45) }
$exists=$false
if (Test-Path $queue) {
  $existing=Get-Content -LiteralPath $queue -Raw | ConvertFrom-Json
  $exists=@($existing.tasks | Where-Object { $_.id -eq $id }).Count -gt 0
}
if (-not $exists) {
  $promptFile=Join-Path $root 'pilot.txt'
  @'
Inspecciona AGENTS.md, checkpoints y Git. Implementa una sola mejora pequena y reversible, ejecuta pruebas y reporta evidencia. No alteres credenciales, autenticacion, servidores externos ni pagos; no publiques, hagas push o fusiones ramas.
'@ | Set-Content -LiteralPath $promptFile -Encoding UTF8
  $options=@('add','--project',$project,'--prompt-file',$promptFile,'--name',$id,'--timeout','1200')
  if ($Model) { $options+=@('--model',$Model) }
  & python $worker @options
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la tarea piloto' }
} else { Write-Host "Tarea $id ya existe, conservamos su progreso" }
& hermes gateway install
if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar gateway de Hermes' }
& hermes gateway start
if ($LASTEXITCODE -ne 0) { throw 'No se pudo arrancar gateway de Hermes' }
if ($EnableHourly) {
  $list=(& hermes cron list 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo consultar trabajos cron' }
  if ($list -notmatch 'DEXTER OpenCode Queue') {
    & hermes cron create 'every 1h' --no-agent --script 'dexter_opencode_tick.py' --name 'DEXTER OpenCode Queue'
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo programar el dispatcher' }
  } else { Write-Host 'Cron DEXTER OpenCode Queue ya existe' }
}
& hermes gateway status
& hermes cron status
& python $worker status
if ($RunPilot) {
  Write-Host 'Ejecutando una tarea real en OpenCode...'
  & python $worker run
  if ($LASTEXITCODE -ne 0) { throw 'Piloto bloqueado: revisar estado en DEXTER-AUTO' }
}
Write-Host "Bridge preparado: $worker"
Write-Host "Nueva tarea: python '$worker' add --project RUTA-GIT --prompt-file RUTA-TAREA.txt"
Write-Host "Estado: python '$worker' status"
