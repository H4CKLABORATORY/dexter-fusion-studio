# TOKENLAB X — monitor de eficiencia de contexto

Este directorio y el workflow .github/workflows/tokenlab-x-watch.yml son una extensión **aislada** para supervisar documentos oficiales sobre compaction, prompt caching y Codex.

- Revisión automática solicitada: una vez cada día mediante GitHub Actions (UTC).
- Evidencia: change_report.md y source_hashes.json, creados tras el primer inicio correcto.
- No lee conversaciones privadas, no necesita API key y no envía datos de usuarios.
- Solo detecta cambios en tres páginas oficiales. No es investigación universal ni prueba que se mejoró el uso real de tokens.
- No cambia límites, modelos, facturación o funcionamiento interno de ChatGPT/Codex.
- No se deben aplicar cambios automáticos sin revisar las fuentes y comparar pruebas medibles.
- La programación de GitHub no detecta pausas de ChatGPT, puede retrasarse, fallar o suspenderse por políticas del servicio.
- Para detenerlo, desactiva el workflow desde la pestaña Actions o elimina el archivo YAML.

Esta adición no interfiere con LOTTO LAB, las demás herramientas ni con sus flujos existentes.

Para mejorar la eficiencia de Codex en cada repositorio, conserva un AGENTS.md breve, registra estado probado de cada fase y recupera solo los archivos necesarios para la tarea.
