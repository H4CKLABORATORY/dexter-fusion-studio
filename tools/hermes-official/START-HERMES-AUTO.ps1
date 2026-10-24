# DEXTER: configura el Hermes Agent OFICIAL en Windows sin crear otro motor.
# Ejecutar en PowerShell con permisos de usuario. NUNCA insertar claves en este script.
[CmdletBinding()]
param([switch]$Install,[switch]$EnableHourlyWork,[string]$ProjectPath='')
$ErrorActionPreference = 'Stop'
function Call-Hermes([string[]]$Params) {
    & hermes @Params
    if ($LASTEXITCODE -ne 0) { throw "Hermes fallo: $($Params -join ' '), exit=$LASTEXITCODE" }
}
if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {
    if (-not $Install) { throw 'No esta instalado Hermes. Repite con -Install para usar el instalador oficial.' }
    $installer=Invoke-RestMethod 'https://hermes-agent.nousresearch.com/install.ps1' -TimeoutSec 45
    & ([scriptblock]::Create($installer)) -NonInteractive
    $env:Path=[Environment]::GetEnvironmentVariable('Path','Machine')+';'+[Environment]::GetEnvironmentVariable('Path','User')
}
if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {
    throw 'Hermes no aparece en PATH aun. Abre PowerShell nuevo y ejecuta sin -Install.'
}
Write-Host 'Buscando el servidor de IA LOCAL (no descarga otros modelos)...'
$found=$false
foreach ($url in @('http://127.0.0.1:1234/v1/models','http://127.0.0.1:11434/api/tags')) {
    try {
        $response=Invoke-RestMethod -Uri $url -TimeoutSec 3
        Write-Host "Servidor local disponible: $url"
        if ($response.data) { $response.data | ForEach-Object { Write-Host $_.id } }
        if ($response.models) { $response.models | ForEach-Object { Write-Host $_.name } }
        $found=$true
    } catch { }
}
if (-not $found) {
    Write-Warning 'Activa el servidor Qwen de LM Studio/Ollama; si usas LU, configura su URL propia en Custom endpoint.'
}
Write-Host 'Selecciona LM Studio, Ollama o Custom endpoint y tu modelo Qwen instalado.'
Call-Hermes -Params @('model')
Call-Hermes -Params @('config','set','compression.enabled','true')
Call-Hermes -Params @('config','set','compression.threshold','0.80')
Call-Hermes -Params @('config','set','compression.tail_mode','lean')
Call-Hermes -Params @('gateway','install')
Call-Hermes -Params @('gateway','start')
Call-Hermes -Params @('gateway','status')
Call-Hermes -Params @('cron','status')
if ($EnableHourlyWork) {
    if (-not $ProjectPath) { throw 'Falta -ProjectPath con la ruta al repositorio.' }
    $project=(Resolve-Path -LiteralPath $ProjectPath -ErrorAction Stop).Path
    if (-not (Test-Path -LiteralPath (Join-Path $project '.git'))) { throw 'La carpeta no tiene .git; no programo tareas fuera de un proyecto Git.' }
    $name='DEXTER-AUTO-'+[IO.Path]::GetFileName($project)
    $jobs=(& hermes cron list 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo listar los trabajos existentes.' }
    if ($jobs -notmatch [regex]::Escape($name)) {
        $prompt="Actua solo en el repositorio '$project'. Lee AGENTS.md, los checkpoints, git status y HEAD. Completa SOLO una tarea pendiente pequena y reversible, ejecuta pruebas y guarda checkpoint con resultados y siguiente paso. Usa rama separada. No toques main, no hagas push/merge/deploy, no realices pagos ni expongas secretos. No dupliques un trabajo que siga en ejecucion. Si hay bloqueo, registralo y deten la tarea."
        Call-Hermes -Params @('cron','create','every 1h',$prompt,'--name',$name)
    } else { Write-Host "Trabajo $name ya existe, no se duplica." }
    Call-Hermes -Params @('cron','list')
} else {
    Write-Host 'Sincronizacion y gateway listos. Tras verificar un chat, reejecuta con -EnableHourlyWork -ProjectPath RUTA_REPOSITORIO.'
}
Write-Host 'Configuracion enviada. IMPORTANTE: prueba una tarea y verifica que Qwen siga disponible tras reiniciar.'
