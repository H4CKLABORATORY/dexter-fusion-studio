# SIGUIENTE TAREA PRIORITARIA — MOTOR MULTIPISTA V3 (RAMA, PENDIENTE DE MERGE)

Estado (2026-11-06): el incremento prioritario anterior está **completado y verificado en la rama `feature/multitrack-engine-v1`** (no en `main`): motor multifuente, visor proxy de composición real, ondas por pista, medidores, fades y gain envelopes con keyframes, keyframes de transformación, migración v2→v3, OTIO y captura Qt real. Detalle: `PROJECT_STATUS.md`, `docs/ENGINE_COMPARISON.md`, `CHANGELOG.md`, `KNOWN_ISSUES.md`. Suite completa: 154 passed + 67 subtests.

## Siguiente incremento prioritario (en este orden)

1. **Revisión y merge a `main` de `feature/multitrack-engine-v1`** (revisión humana de Douglas o de otro agente; no auto-mergear). Verificar que V2/A3 de PR #11 siguen funcionando tras el merge y que la suite completa sigue en verde.
2. **Verificación en Windows con RTX 3090** (no verificable en dexter): NVENC/NVDEC real, EXE portable de GitHub Actions, arranque y render, medición de velocidad y memoria del proxy y del render completo, reproducción en tiempo real del proxy.
3. **Paridad de flujos importantes antes de retirar nada**: la UI Tk clásica y el flujo v2 siguen disponibles; no retirar hasta que el flujo multipista cubra importar → editar → proxy → exportar en Windows.
4. **Mejoras del motor v3**: posición de texto con keyframes (hoy estática en v1), opacidad con keyframes continuos (hoy segmentos de 0.25 s), vista previa en vivo por frame-server durante scrub, mezcla de audio de nivel DAW.
5. **TokenLab / PR #12**: sigue abierto y sin fusionar; si se integra, debe ser un subsistema interno del Director Creativo, no bloquear UI ni render.

### No volver a hacer
- No crear botones que no actúen sobre el motor.
- No copiar componentes de código GPL/propietario sin revisar obligaciones de licencia.
- No eliminar la UI anterior hasta que exista paridad funcional de flujos importantes.
- No prometer ejecución autónoma infinita; guardar checkpoints para la siguiente sesión.
- No afirmar NVENC, EXE Windows ni tiempo real sin haberlo medido en hardware real.

### Validación
Pruebas de PNG compositado, correlación de tonos de música, exportación multiarchivo, GUI Qt offscreen, arranque EXE Windows, captura verdadera y proyecto rescatable tras error.
