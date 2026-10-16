# 1. Crea un repositorio PRIVADO VACÍO en https://github.com/new
# 2. Ejecuta desde esta carpeta: .\SUBIR_A_GITHUB.ps1 -User "TU_USUARIO"
# Requiere Git para Windows. GitHub pedirá autenticación de manera segura.
param([Parameter(Mandatory=$true)][string]$User,
      [string]$Repo = 'dexter-fusion-studio')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Instala Git para Windows' }
if (-not (Test-Path .git)) { git init -b main }
git add README.md .gitignore INICIAR_WINDOWS.bat SUBIR_A_GITHUB.ps1 main.py pyproject.toml fusion tests docs
$changes = git status --porcelain
if ($changes) { git commit -m 'Initial Dexter Fusion Studio original source' }
$remote = "https://github.com/$User/$Repo.git"
$existing = git remote get-url origin 2>$null
if (-not $existing) { git remote add origin $remote }
elseif ($existing -ne $remote) { throw "El remote origin ya apunta a $existing. Comprueba antes de continuar." }
git push -u origin main
