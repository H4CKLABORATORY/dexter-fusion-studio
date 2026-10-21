# DEXTER Local Accelerator - Windows bootstrap (run as normal user)
# Installs standard tools only after confirmation; does not modify BIOS or auto-merge.
[CmdletBinding()]
param([switch]$Install,[switch]$StartTask)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Join-Path $env:USERPROFILE 'DEXTER-LOCAL'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$log = Join-Path $root 'bootstrap.log'
Start-Transcript -Path $log -Append | Out-Null
try {
  function Has($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }
  Write-Host 'DEXTER Local Accelerator - comprobacion'
  if (-not (Has 'winget')) { throw 'Falta winget (App Installer). Instalarlo desde Microsoft Store antes de continuar.' }
  $packages = @(
    @{id='Git.Git';cmd='git'},
    @{id='Python.Python.3.12';cmd='python'},
    @{id='GitHub.cli';cmd='gh'},
    @{id='OpenJS.NodeJS.LTS';cmd='node'}
  )
  foreach ($p in $packages) {
    if (Has $p.cmd) { Write-Host "OK: $($p.cmd)"; continue }
    if (-not $Install) { Write-Warning "Falta $($p.cmd); usa -Install para instalar"; continue }
    Write-Host "Instalando $($p.id)..."
    & winget install --id $p.id --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Fallo instalacion de $($p.id)" }
  }
  # New PATH may require a new PowerShell process.
  if (-not (Has 'git') -or -not (Has 'python')) {
    Write-Warning 'Reabre PowerShell tras instalar Git/Python y ejecuta de nuevo.'
    return
  }
  $project = Join-Path $root '1UP-ANIME'
  if (-not (Test-Path (Join-Path $project '.git'))) {
    & git clone https://github.com/H4CKLABORATORY/1UP-ANIME.git $project
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo clonar 1UP Anime' }
  } else {
    Write-Host 'Proyecto existente: no se hace git pull ni se descartan cambios locales.'
  }
  if (-not $StartTask) {
    Write-Host 'Preparado. Ejecuta con -StartTask cuando LM Studio y su servidor local esten activos.'
    return
  }
  if (-not (Has 'gh')) { throw 'Falta GitHub CLI; reabre PowerShell o instala gh.' }
  & gh auth status
  if ($LASTEXITCODE -ne 0) { throw 'Autentica GitHub con: gh auth login' }
  try { $models = Invoke-RestMethod -Uri 'http://127.0.0.1:1234/v1/models' -TimeoutSec 8 }
  catch { throw 'LM Studio no responde en localhost:1234. Carga Qwen y activa el servidor API local.' }
  $model = @($models.data | Where-Object { $_.id -match 'qwen' } | Select-Object -First 1)
  if (-not $model) { throw 'No se encontro un modelo Qwen cargado en LM Studio.' }
  $venv = Join-Path $root '.venv'
  if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    & python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear entorno Python' }
  }
  $py = Join-Path $venv 'Scripts\python.exe'
  & $py -m pip install --upgrade 'aider-chat>=0.86,<1'
  if ($LASTEXITCODE -ne 0) { throw 'Fallo instalacion de Aider' }
  Push-Location $project
  try {
    if ((& git status --porcelain)) { throw 'Hay cambios locales: guardalos antes de arrancar el agente.' }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    & git switch -c "agent/qwen-first-task-$stamp"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear rama de trabajo' }
    $env:OPENAI_API_BASE = 'http://127.0.0.1:1234/v1'
    $env:OPENAI_API_KEY = 'lm-studio'
    $prompt = 'Lee AGENTS.md y docs/PROJECT_CONTINUITY.md. Elige UNA mejora pequena y reversible de UX o pruebas de 1UP Anime. No modifiques autenticacion, secretos ni fuentes de streaming. Implementa, ejecuta pruebas pertinentes y documenta lo realizado. No publiques, no hagas push y no fusiones ramas.'
    & $py -m aider --model "openai/$($model[0].id)" --yes-always --no-auto-commits --message $prompt
    if ($LASTEXITCODE -ne 0) { throw 'El agente termino con error; revisa registro y git diff.' }
    Write-Host 'Primera tarea ejecutada. Revisa git diff y pruebas antes de publicar.'
  } finally { Pop-Location }
} finally { Stop-Transcript | Out-Null }
