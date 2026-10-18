# TokenLab — integración real en Dexter Fusion Studio Qt

## Funcionalidad actual
- Barra de herramientas del editor: **TokenLab**, diálogo A/B y comparación con el tokenizador `tiktoken` del modelo OpenAI para texto.
- Cuatro pestañas Qt: memoria permanente/resumen de sesión/ventana volátil con checkpoints atómicos; deduplicación SHA-256 y semántica opcional vía embeddings; priorización 60/30/10; cuatro skills JSON (buscar, resumir, contar y comparar).
- Ollama local: `fusion/tokenlab_ollama.py` permite resumen y embeddings reales; `fusion/tokenlab_stream.py` transmite tokens desde `/api/generate` con `QNetworkAccessManager` **sin bloquear el hilo Qt**.
- El botón **CANCELAR HTTP** ejecuta `QNetworkReply.abort()`; los timeouts, errores de proveedor, NDJSON inválido y conexión rechazada muestran códigos explícitos. Los tokens progresivos son tentativos hasta `done=true`.
- `fusion/tokenlab_context_async.py` compacta contexto mediante streams y conserva la memoria previa completa cuando ocurre cancelación, timeout o error. No se publican resúmenes parciales como hechos terminados.
- Las llamadas de embeddings directas aún son síncronas: en deduplicación semántica la interfaz puede esperar mientras Ollama responde. Falta migrar ese endpoint a red asíncrona para cobertura total.

## Instalar/ejecutar (Windows)
```powershell
py -3 -m pip install -r studio-requirements.txt
py -3 -m unittest tests.test_tokenlab_stream tests.test_tokenlab_compactor tests.test_tokenlab_workspace tests.test_tokenlab_live_probe_contract -v
py -3 studio.py
```

Instala Ollama en Windows y después:
```powershell
ollama pull llama3.2:1b
ollama pull nomic-embed-text
ollama serve
```
En otra terminal:
```powershell
$env:TOKENLAB_OLLAMA_MODEL = "llama3.2:1b"
$env:TOKENLAB_EMBED_MODEL = "nomic-embed-text"
py -3 studio.py
```
Las peticiones Ollama de la GUI se restringen a loopback; no se exponen claves ni se consulta una API pública sin configuración expresa.

## CI y evidencia verificable
- `tests/test_tokenlab_stream.py` usa un **servidor HTTP local de pruebas**, no un modelo real: éxito de streaming, cancelación del transporte, timeout, HTTP 503, NDJSON inválido, fallos de conexión y respuesta en controles Qt.
- `tests/test_tokenlab_compactor.py` usa señales controladas para probar commit/rollback transaccional; es una prueba de componentes, no inferencia real.
- `.github/workflows/tokenlab-ollama.yml` sí instala Ollama real y descarga `llama3.2:1b` y `nomic-embed-text`. Run [39093243927](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39093243927): generación A/B, resumen y embeddings reales en CI, SUCCESS.
- Las pruebas de paridad con `tiktoken` oficial están en `tests/test_tokenlab_tools.py`; cuentan **texto**, no el overhead completo de llamadas a ChatGPT.

## OpenAI API — opt-in y costo limitado
`.github/workflows/tokenlab-openai.yml` está publicado en la rama. Ejecutar manualmente en **Actions → TokenLab OpenAI one-call smoke (opt-in) → Run workflow**, tras crear el secreto GitHub `OPENAI_API_KEY` en **Settings → Secrets and variables → Actions → New repository secret**. Nunca pegar la clave en un chat o código.

- Si no hay secreto: `SKIPPED_NO_OPENAI_API_KEY`, sin ninguna llamada.
- Si existe: una sola petición `POST /v1/responses` al modelo `gpt-4.1-mini` con `max_output_tokens=24` y timeout de 90 s; registra latencia y recuento de tokens, sin registrar la respuesta ni la clave.
- `tests/test_tokenlab_live_probe_contract.py` verifica flujo con secreto ausente y una llamada mediante mocks, **no** inferencia OpenAI real.
- No se ha verificado todavía una ejecución del workflow con secreto real.

## Límites y seguridad
La exactitud factual de resúmenes generativos no se garantiza automáticamente. Si se declaran hechos obligatorios, `GestorContexto` rechaza compresión que no los conserve. Los prompts de checkpoint pueden contener datos privados; se guardan fuera del repositorio. No confundir chat generado, tokenización local, embeddings y respuestas de modelos distintos.

PR #12 permanece DRAFT mientras exista trabajo pendiente. Consultar `CONTINUIDAD.md` y `TOKENLAB_CHECKPOINT.json`.
