# TokenLab integrado en Dexter Fusion Studio (Qt)

## Qué funciona realmente
- La **ventana principal de PySide6** contiene una acción **⌁ TokenLab** que abre `fusion.tokenlab_dialog.TokenLabDialog`. Introduce PROMPT A y B, selecciona el modelo OpenAI y usa **COMPARAR TOKENS A/B**.
- `fusion.tokenlab_tools.compare_texts` usa `tiktoken.encoding_for_model(model)`; informa conteos exactos de **texto**, diferencia y porcentaje de ahorro.
- Guarda y restaura el checkpoint `studio_ab` desde `~/Documents/DexterFusionStudio/tokenlab/`, con escritura temporal + fsync + renombrado atómico. No sube prompts al repositorio ni a ninguna API.
- SHA-256 exacto disponible para identificar fragmentos; no se afirma deduplicación semántica en esta integración parcial.
- `tests/test_tokenlab_tools.py` compara el conteo con el tokenizador oficial instalado. Ejecutar `python -m unittest tests.test_tokenlab_tools -v`. CI de Qt y Windows instala tiktoken desde `studio-requirements.txt`.

## Instalación
```bash
python -m pip install -r studio-requirements.txt
python -m unittest tests.test_tokenlab_tools -v
python studio.py
```

## Privacidad y límites
La ventana no llama a OpenAI ni a Ollama: compara prompts localmente. Suponer que tiktoken cuenta los tokens nativos de llama.cpp/Ollama sería incorrecto; integrar un tokenizador propio del modelo concreto antes de ofrecer esa capacidad. Los mensajes del chat, herramientas, imágenes y audio generan otros tokens no incluidos en conteos de texto simples. El checkpoint se escribe localmente y puede contener contenido de los prompts: evitar secretos.

## Siguiente integración pendiente
Completar en la GUI las tres capas de GestorContexto, deduplicación de embeddings, ranking 60/30/10 y el registro de skills que ya existe en el paquete TokenLab del laboratorio MIRA; son trabajo pendiente, no funciones acabadas de este PR.

## Prueba online/modelos
No hay claves OPENAI_API_KEY ni servidor Ollama accesibles en el entorno que produjo este PR; NO se ejecutó ninguna inferencia real. Estas pruebas deben hacerse con credenciales privadas y un servicio activo, nunca registrar prompts ni credenciales en logs/CI público.
