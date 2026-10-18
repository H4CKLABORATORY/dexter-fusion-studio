# SIGUIENTE TAREA PRIORITARIA — EDITOR DE COMPOSICIÓN AUTÉNTICO

Estado: PR #11 incorporado a `main` (commit `0ff9445`): overlays V2 y música A3 participan en el MP4 final; el visor reproduce el render final tras terminar. No confundir con un visor de efectos en tiempo real.

## Siguiente incremento prioritario
**Motor multifuente y visor de composición** en una arquitectura modular.

- Diseñar clips fuente normalizados (asset_id, source_in/out, timeline_start, track_id) y esquema de proyecto versionado.
- Permitir varios videos importados con audio separado, edición no destructiva, drag/drop y snapping.
- Introducir render proxy de baja resolución para **previsualizar la composición real sin exportar la película entera**, preferiblemente con caché incremental.
- Añadir al timeline V2/A3 el recorte y movimiento visual por drag/drop, y ondas reales independientes para A3.
- Añadir medidores de audio, fades y gain envelopes de mínimo 2 keyframes.
- Verificar clips de FPS/resolución diferentes, subtítulos, audio, overlays, silencio, render de 60 s y proyectos reordenados.
- Medir velocidad y uso de memoria en Windows y documentar límites.

### No volver a hacer
- No crear botones que no actúen sobre el motor.
- No copiar componentes de código GPL/propietario sin revisar obligaciones de licencia.
- No eliminar la UI anterior hasta que exista paridad funcional de flujos importantes.
- No prometer ejecución autónoma infinita; guardar checkpoints para la siguiente sesión.

### Validación
Pruebas de PNG compositado, correlación de tonos de música, exportación multiarchivo, GUI Qt offscreen, arranque EXE Windows, captura verdadera y proyecto rescatable tras error.
