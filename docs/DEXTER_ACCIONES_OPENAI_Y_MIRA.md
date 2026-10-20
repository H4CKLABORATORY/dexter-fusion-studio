# Acciones manuales de Dexter — OpenAI y publicación independiente de MIRA

**Estado:** procedimiento preparado, **no ejecutado**. No introducir secretos en el chat, commits ni comentarios. El PR #12 permanece DRAFT.

## A. Configurar el secreto OpenAI en GitHub

1. Abre https://github.com/H4CKLABORATORY/dexter-fusion-studio/settings/secrets/actions . Requiere permiso de administración del repositorio.
2. En **Repository secrets**, pulsa **New repository secret**.
3. En **Name**, introduce exactamente `OPENAI_API_KEY`. En **Secret**, pega tu clave privada **sólo dentro del formulario de GitHub** y guarda.
4. Comprueba que aparece el **nombre**, no el valor. Los secretos no pueden leerse después; no intentes enviarlos a ChatGPT.
5. Abre https://github.com/H4CKLABORATORY/dexter-fusion-studio/pull/12 . En la barra derecha, sección **Labels**, selecciona `tokenlab-openai-smoke`. Si no existe, crea la etiqueta desde **Issues → Labels → New label** y después aplícala al PR (debe ser un evento **labeled** nuevo).
6. Abre **Actions** del repositorio y busca **TokenLab OpenAI one-call smoke (opt-in)**. Localiza la ejecución desencadenada por la etiqueta y revisa el paso **Run one request or explicitly skip if secret absent**.
7. Resultados posibles:
   - `SKIPPED_NO_OPENAI_API_KEY`: no se configuró o no estuvo accesible; **no se ejecutó inferencia**.
   - `real_inference: true` con `latency_ms`, `input_tokens`, `output_tokens` y SUCCESS: evidencia de una llamada real.
   - FAILED: resolver la causa **sin publicar el secreto**. Revisar facturación/permiso del modelo y conectividad.
8. Para volver a ejecutar desde la etiqueta, quítala y **vuélvela a añadir**. No dispares repetidamente llamadas pagadas. El workflow limita cada ejecución a **una llamada**, modelo `gpt-4.1-mini`, máximo **24 tokens de salida** y timeout de 90 s (4 min máximo de job).

**Importante:** `workflow_dispatch` manual puede no mostrarse hasta que el workflow exista en la rama por defecto; el evento `pull_request: labeled` permite probar el PR sin fusionarlo. Evitar aplicar la etiqueta a PRs de forks: el workflow verifica que la rama de origen pertenece al mismo repositorio.

## B. Crear repositorio propio y privado MIRA

1. Abre https://github.com/organizations/H4CKLABORATORY/repositories/new o utiliza **GitHub → New repository**.
2. **Owner:** `H4CKLABORATORY`; **Repository name:** `mira-neural-prompt-studio`; **Visibility:** `Private`.
3. No marques **Add a README**, **Add .gitignore**, ni **Choose a license** para iniciar el repositorio vacío. Crea el repositorio.
4. Descarga desde este chat el archivo **MIRA_v2.4_TOKENLAB_INTEGRADO_VALIDADO.zip**. Abre PowerShell en Windows y ajusta `$zip` a donde quedó descargado.
5. **Verifica obligatoriamente SHA-256 antes de descomprimir o subir**:

```powershell
$zip = "$HOME\Downloads\MIRA_v2.4_TOKENLAB_INTEGRADO_VALIDADO.zip"
$expected = "1e9e890c9b70478e9d1cbe55479891a29fb798748c84c05cd2e2eb5b69b0003e"
$actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "ZIP distinto: hash no coincide. No publicar." }
$dest = Join-Path $HOME "Desktop\MIRA_Publicacion"
New-Item -ItemType Directory -Force $dest | Out-Null
Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force
Set-Location (Join-Path $dest "MIRA_Neural_Prompt_Studio")
```

6. **Inspecciona el contenido** para evitar contraseñas, tokens, datos privados y archivos temporales. Crea un `.gitignore` desde esa carpeta:

```powershell
@'
.env
.env.*
!.env.example
__pycache__/
*.pyc
.venv/
venv/
node_modules/
*.log
tmp/
build/
dist/
checkpoints/
*.key
*.pem
'@ | Set-Content -Encoding UTF8 .gitignore
git init -b main
git add .
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
```

7. Antes de hacer commit, revisa manualmente los archivos marcados por `git diff --cached --name-only`; ejecuta un escaneo de secretos en el contenido y no continúes si hay una credencial o material privado. El hash del ZIP sólo valida integridad, **no garantiza que no existan secretos**.
8. Cuando esté limpio:

```powershell
git commit -m "feat(mira): publish v2.4 with TokenLab integration"
git remote add origin https://github.com/H4CKLABORATORY/mira-neural-prompt-studio.git
git push -u origin main
git rev-parse HEAD
```

9. Abre https://github.com/H4CKLABORATORY/mira-neural-prompt-studio y comprueba que está **Private** y tiene los archivos originales. Configura CI para tests Python/JS y revisa el despliegue; no confundas subir código con declarar producción terminada.
10. Comunica únicamente los enlaces del repositorio y del run de Actions (no secretos). La conexión GitHub podrá verificar el commit publicado y evaluar el cierre del PR #12.

## C. Criterios antes de quitar DRAFT y fusionar PR #12

- CI del **SHA final del PR** verde: general, Qt, Windows EXE y Ollama real.
- Prueba autenticada OpenAI de una única llamada con latencia y uso verificables en logs. `SKIPPED` **no cumple**.
- Repositorio privado propio MIRA con código completo, commit real, revisión de secretos y pruebas aplicables.
- Revisión final de cambios y permisos; aprobación del propietario para fusión. **Sólo después** registrar el SHA efectivo de `main` posterior al merge.

**No ejecutar estos pasos desde ChatGPT en nombre de Dexter sin autorización o herramientas adecuadas; son instrucciones manuales.**
