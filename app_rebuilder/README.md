# DEXTER App Rebuilder — fase 1

Módulo de inventario y análisis estático de archivos propios o autorizados. No ejecuta archivos importados.

## Uso
```bash
python -m app_rebuilder.cli ruta/al/archivo.exe --json
python -m unittest discover -s app_rebuilder/tests -v
```

Compatible con Windows, Linux y macOS usando solo la biblioteca estándar de Python. Detecta firmas PE, ELF, Mach-O y ZIP/APK; calcula SHA-256 y registra tamaño. No afirma recuperar código fuente ni funcionalidades originales. Integraciones futuras: Ghidra headless, JADX, Apktool, reportes y reconstrucción de UI. Revisar licencias y permisos antes de analizar software ajeno.
