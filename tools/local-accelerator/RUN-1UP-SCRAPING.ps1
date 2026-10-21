# DEXTER 1UP metadata runner — uses existing scraper, no additional npm dependencies.
# Run in PowerShell: pwsh -File .\RUN-1UP-SCRAPING.ps1
# Requires Node 18+ and a cloned 1UP-ANIME checkout.
[CmdletBinding()]
param(
  [string]$Project = (Join-Path $env:USERPROFILE 'DEXTER-LOCAL\1UP-ANIME'),
  [int]$TimeoutSeconds = 240
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$script = Join-Path $Project 'scripts\refresh-catalog.mjs'
$catalog = Join-Path $Project 'data\catalog.json'
$reportDir = Join-Path $env:USERPROFILE 'DEXTER-LOCAL\reports'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$reportPath = Join-Path $reportDir 'last-scraping-run.json'
$started = (Get-Date).ToUniversalTime()
$report = [ordered]@{ startedAt=$started.ToString('o'); finishedAt=$null; status='failed'; exitCode=$null; countBefore=$null; countAfter=$null; details=$null }
try {
  if (-not (Test-Path $script)) { throw "No existe $script" }
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js no esta instalado' }
  function Validate-Catalog([string]$path) {
    if (-not (Test-Path $path)) { return 0 }
    $data = Get-Content -Raw -Path $path | ConvertFrom-Json
    if (-not $data.updated -or -not $data.groups) { throw 'Catalogo sin updated o groups' }
    $parsedDate = [datetime]::MinValue
    if (-not [datetime]::TryParse([string]$data.updated, [ref]$parsedDate)) { throw 'Fecha updated invalida' }
    $total = 0
    foreach ($group in $data.groups.PSObject.Properties) {
      $seen = [System.Collections.Generic.HashSet[string]]::new()
      foreach ($anime in @($group.Value)) {
        if (-not $anime.id -or -not $anime.title) { throw "Registro incompleto en $($group.Name)" }
        if (-not $seen.Add([string]$anime.id)) { throw "ID duplicado en $($group.Name): $($anime.id)" }
        foreach ($link in @($anime.streaming)) {
          if ($null -ne $link -and ([string]$link.url) -notmatch '^https://') { throw "Enlace no HTTPS en $($group.Name)" }
        }
        $total++
      }
    }
    if ($total -lt 5) { throw 'Catalogo demasiado pequeno' }
    return $total
  }
  $report.countBefore = Validate-Catalog $catalog
  Push-Location $Project
  try {
    & node --check $script
    if ($LASTEXITCODE -ne 0) { throw 'Fallo node --check' }
    # Run with a hard timeout, capturing exit code. No shell command injection.
    $p = Start-Process -FilePath 'node' -ArgumentList @($script) -PassThru -NoNewWindow
    if (-not $p.WaitForExit($TimeoutSeconds * 1000)) {
      Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
      throw "Scraping excedio $TimeoutSeconds segundos"
    }
    $report.exitCode = $p.ExitCode
    if ($p.ExitCode -ne 0) { throw "Scraping termino con codigo $($p.ExitCode)" }
    $report.countAfter = Validate-Catalog $catalog
    $report.status = 'completed'
    $report.details = 'AniList metadata fetched and catalog validated. Does not verify video playback.'
  } finally { Pop-Location }
} catch {
  $report.details = $_.Exception.Message
  Write-Error -Message $report.details -ErrorAction Continue
} finally {
  $report.finishedAt = (Get-Date).ToUniversalTime().ToString('o')
  $report | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 -Path $reportPath
  Write-Host "Reporte: $reportPath"
}
if ($report.status -ne 'completed') { exit 1 }
Write-Host "Scraping verificado: $($report.countAfter) fichas"
