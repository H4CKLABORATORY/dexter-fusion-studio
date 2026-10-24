# Install upstream gstack skills for OpenCode ONLY (no Claude, no other agents).
# PowerShell 5.1+; no admin rights required. User executes this on their PC.
[CmdletBinding()]
param([switch]$WithBrowser)
$ErrorActionPreference = 'Stop'
foreach ($command in @('git','bun','node','opencode')) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
    throw "Falta $command. Instala el programa y reabre PowerShell; no se modifico OpenCode."
  }
}
$local = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE 'AppData\Local' }
$root = Join-Path $local 'DEXTER-TOOLS'
$checkout = Join-Path $root 'gstack'
$expected = 'https://github.com/garrytan/gstack.git'
New-Item -ItemType Directory -Force -Path $root | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $checkout '.git'))) {
  if (Test-Path -LiteralPath $checkout) {
    throw "La carpeta $checkout existe pero no es repositorio Git. No sera sobrescrita."
  }
  & git clone --single-branch --depth 1 $expected $checkout
  if ($LASTEXITCODE -ne 0) { throw 'Fallo descargar el gstack oficial de Garry Tan' }
} else {
  $origin = (& git -C $checkout remote get-url origin | Out-String).Trim()
  if ($LASTEXITCODE -ne 0 -or $origin -notin @(
     $expected,'https://github.com/garrytan/gstack','git@github.com:garrytan/gstack.git'
  )) { throw "Origen Git de gstack no reconocido: $origin" }
  Write-Host 'Se reutiliza el checkout existente; no se hace git pull automaticamente.'
}
$upstreamSetup = Join-Path $checkout 'setup.ps1'
if (-not (Test-Path -LiteralPath $upstreamSetup)) {
  throw 'No se encontro el setup.ps1 oficial en la carpeta descargada.'
}
$setupArgs = @('--host','opencode')
if (-not $WithBrowser) { $setupArgs += '--no-browser' }
& $upstreamSetup @setupArgs
if ($LASTEXITCODE -ne 0) { throw "Falló gstack setup --host opencode (codigo $LASTEXITCODE)" }
& $upstreamSetup --status
if ($LASTEXITCODE -ne 0) { throw 'gstack instalado pero el chequeo de enlaces fallo: revisa setup --status' }
Write-Host 'gstack OpenCode instalado; cierra y reabre OpenCode.'
Write-Host 'Prueba /gstack-review sobre una rama con cambios. Para activar la calidad en el dispatcher usa --gstack review.'
Write-Host 'No se instalo otro modelo IA ni se ha programado ningun trabajo de Hermes.'
