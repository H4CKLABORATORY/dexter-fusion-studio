@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.10+ no encontrado. Instala Python desde python.org
  pause
  exit /b 1
)
py -3 -c "import PySide6" 2>nul
if errorlevel 1 (
  echo La interfaz Qt no esta instalada.
  echo Ejecuta: py -3 -m pip install -r studio-requirements.txt
  pause
  exit /b 1
)
py -3 studio.py
if errorlevel 1 pause
endlocal
