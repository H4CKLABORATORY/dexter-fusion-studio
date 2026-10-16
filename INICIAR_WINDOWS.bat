@echo off
cd /d "%~dp0"
py -3 main.py
if errorlevel 1 (
  echo.
  echo No se pudo iniciar. Comprueba que Python 3 y FFmpeg esten instalados.
  pause
)
