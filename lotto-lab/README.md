# LOTTO LAB DEXTER 2.0

**Sitio estático para iPhone y PC con archivo histórico verificable de sorteos, matemáticas y validación de estrategias sin engaños predictivos.**

## Fuentes

- [NY Open Data Powerball, desde 2010](https://data.ny.gov/d/d6yy-54nr)
- [NY Open Data Mega Millions, desde 2002](https://data.ny.gov/d/5xaw-6ayf)

El script `scripts/build_data.py` descarga CSV públicos de NY State Gaming Commission, limpia, deduplica por fecha, verifica datos y genera `data/powerball.json` y `data/megamillions.json`. Si la descarga falla, el flujo no inventa registros. **No es el historial de todas las loterías del mundo, ni incluye Powerball anterior a 2010**. La propia fuente advierte que prevalece la certificación del operador ante discrepancias.

## Funciones

- Powerball 5/69 + 1/26, precio ilustrativo $2, reglas actuales desde 2015-10-07.
- Mega Millions 5/70 + 1/24, precio $5, reglas actuales desde 2025-04-08.
- Biblioteca de resultados de estas fuentes y búsqueda por fecha/año.
- Frecuencias de bolas principales y especiales, pares, impar/par y exportación CSV. Los análisis comparativos solo usan sorteos bajo las reglas actuales, sin contaminar con sistemas históricos distintos.
- Probabilidad exacta para una o varias combinaciones *distintas* en un solo sorteo.
- Generador aleatorio criptográfico, sin priorizar números por frecuencia.
- Prueba walk-forward: en cada paso entrena sobre el pasado y evalúa el resultado siguiente, sin mirar datos futuros. Se compara con una línea base matemática, no promete ventaja predictiva.
- Instalación tipo web app en iPhone mediante **Compartir > Agregar a pantalla de inicio**, y en PC por navegador compatible. Datos en caché para consultas sin conexión después de la primera carga correcta.
- No cuentas, pagos, compra de boletos, publicidad ni trackers externos.

## Compilar biblioteca oficial

Requiere Python 3.10+ con Internet:

```bash
python scripts/build_data.py data
python -m unittest discover -s tests -v
node --test tests/test_core.mjs
```

Para ver la web localmente:

```bash
python -m http.server 8000
```

Abre http://localhost:8000. La biblioteca se sirve desde `data/` y se actualiza desde GitHub Actions de forma programada cuando el repositorio tenga Pages habilitado. No hace falta API key ni usar la nube para cálculos, pero sí conexión para obtener sorteos nuevos.

## Aviso fundamental

Un sorteo bien diseñado es independiente: **ni los números calientes, ni los atrasados, ni una IA, aumentan la probabilidad de acertar el siguiente sorteo**. Los historiales y probabilidades no son asesoramiento financiero. Evita gastar dinero que necesites para vivir. Se incluye el programa previo en `legacy.html`.

## GitHub Pages

Este proyecto está diseñado para publicarse en una ruta independiente `lotto-lab/` de un repositorio de GitHub existente si no hay permisos para crear otro repositorio. Para usar Pages, habilita **Settings > Pages > Build and deployment > Source: GitHub Actions** una vez. La acción se ejecuta en `main` y cada día para refrescar las copias de las fuentes, y el sitio es accesible en la URL Pages del repositorio.

Documentación técnica y pruebas en la carpeta `tests/`.
## Estado de publicación verificado (2026-10-17)

- GitHub Pages quedó habilitado. El despliegue del [flujo LOTTO LAB n.º 2](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/runs/39029432258) concluyó correctamente.
- Dirección prevista: **https://h4cklaboratory.github.io/dexter-fusion-studio/lotto-lab/**. El artefacto Pages ahora conserva deliberadamente el prefijo `lotto-lab/` para no colocar el sitio sobre la raíz de otros proyectos.
- `.github/workflows/lotto-lab-pages.yml` verifica las pruebas de Python/Node, descarga nuevos sorteos oficiales, valida ambos JSON, crea el artefacto web y publica Pages. Tras el despliegue, una prueba de humo solicita por HTTPS el HTML y los dos JSON, comprueba su formato y exige al menos 1000 registros por juego. Si no son accesibles después de varios intentos, el flujo falla claramente.
- Los históricos se reconstruyen en el runner cada día (UTC: 12:27); no hay que confundir una ejecución correcta con una ventaja predictiva.
- Para comprobar el estado más reciente, consulta [GitHub Actions](https://github.com/H4CKLABORATORY/dexter-fusion-studio/actions/workflows/lotto-lab-pages.yml).

