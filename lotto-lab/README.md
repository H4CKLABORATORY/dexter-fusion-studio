## Navegación por páginas independientes

**Generador primero, siempre.** El inicio del sitio publicado en `/lotto-lab/` muestra el generador matemático y la selección diaria de números de la suerte, seguido de tarjetas que conducen a páginas verdaderamente independientes. Ya no es necesario recorrer toda una página larga para encontrar los servicios.

| Ruta de GitHub Pages | Servicio |
|---|---|
| `index.html` | **Portada y generador** (prioridad visual) |
| `revisar.html` | Verificación numérica contra resultados oficiales disponibles |
| `escanear.html` | Lectura local de código de barras / QR y enlaces a escáner oficial |
| `premios.html` | Tabla de premios y probabilidades |
| `presupuesto.html` | Presupuesto e información de retornos matemáticos |
| `impuestos.html` | Retenciones y escenario ilustrativo de impuestos finales |
| `simulador.html` | Plató virtual con sorteo animado, reproducción y pruebas |
| `matematicas.html` | Auditor científico y cálculo de cobertura |
| `probabilidades.html` | Comparación de juegos por posibilidades exactas |
| `historial.html` | Biblioteca histórica y directorio de loterías de Estados Unidos |

### Diseño y mantenimiento

La fuente canónica `lotto-lab/index.html` conserva las secciones originales para facilitar mantenimiento y compatibilidad con pruebas previas. Durante la compilación, `node lotto-lab/scripts/build_pages.mjs lotto-lab _pages/lotto-lab` **genera diez documentos HTML distintos** a partir de esas secciones y sustituye el `index.html` desplegado por la portada enfocada en el generador.

La separación es por URL y documento real: cambiar de pestaña cambia de página. Los módulos `assets/page-context.mjs` y `assets/game-catalog.mjs` comparten reglas y la lotería seleccionada entre páginas; la última combinación calculada se conserva en el almacenamiento temporal de la pestaña cuando el navegador lo permite. `assets/multipage-nav.mjs` mantiene el menú y redirige enlaces antiguos con `#servicesHub`, `#sorteoVirtual` y otros fragmentos a las páginas nuevas.

Los cinco servicios de boletos reutilizan el marcado de los formularios de origen por compatibilidad, pero cada documento está publicado en su propia URL y abre directamente su herramienta activa; las otras pestañas navegan a otro documento. La generación no requiere backend, cuenta ni pago. El sistema de pruebas comprueba los diez archivos separados y la prioridad del generador.


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
- **Generador principal determinista**: cada combinación se calcula desde una semilla interna fija y un contador reproducibles, sin mostrar ni permitir modificar la semilla en la interfaz, y sin fingir capacidad predictiva. Incluye opciones equilibradas, pares, impares, altas, bajas, números favoritos y frecuencias históricas del régimen actual. Se conserva el generador criptográfico clásico oculto por compatibilidad interna.
- Prueba walk-forward: en cada paso entrena sobre el pasado y evalúa el resultado siguiente, sin mirar datos futuros. Se compara con una línea base matemática, no promete ventaja predictiva.
- Instalación tipo web app en iPhone mediante **Compartir > Agregar a pantalla de inicio**, y en PC por navegador compatible. Datos en caché para consultas sin conexión después de la primera carga correcta.
- Opción matemática **La Chica Honduras (00–99)** con una probabilidad teórica de 1/100 para un número específico en un sorteo uniforme. **No se proporciona historial oficial hondureño hasta encontrar una fuente verificable.**
- Panel de probabilidades por cada bola con porcentajes teóricos y frecuencias históricas observadas (cuando exista una base verificada); entropía combinatoria e intervalos Wilson descriptivos. La probabilidad real del siguiente sorteo NO se deduce de frecuencias pasadas.
- Interfaz de lotería con generador primero, grandes premios históricos documentados y el historial de sorteos en una pestaña desplegable al final. El pozo actual solo se consulta mediante enlaces oficiales para evitar cifras desactualizadas.
- No cuentas, pagos, compra de boletos, publicidad ni trackers externos.

## Compilar biblioteca oficial

Requiere Python 3.10+ con Internet:

```bash
python scripts/build_data.py data
python -m unittest discover -s tests -v
node --test tests/test_*.mjs
```

Para ver la web localmente:

```bash
python -m http.server 8000
```

Abre http://localhost:8000. La biblioteca se sirve desde `data/` y se actualiza desde GitHub Actions de forma programada cuando el repositorio tenga Pages habilitado. No hace falta API key ni usar la nube para cálculos, pero sí conexión para obtener sorteos nuevos.

## Cinco servicios: comprobación, escáner, premios, presupuesto e impuestos

La página incluye cinco pestañas desde el **Centro de servicios**: revisión de combinaciones contra resultados históricos oficiales descargados, lectura local de códigos de barras con fallback ZXing para iPhone, premios por categoría documentados, planificación educativa de presupuesto y comparación de retención tributaria con un escenario final editable.

**Cotejar números o leer un barcode nunca valida un premio real ni confirma que se pueda cobrar**: esa verificación debe hacerse con la lotería oficial. Los jackpots y pagos variables no se inventan. La lectura de fotos no las envía a servidores de LOTTO LAB.

Ver detalles, fuentes oficiales, límites de escaneo y cálculos en [SERVICIOS-BOLETOS.md](SERVICIOS-BOLETOS.md). Las pruebas automatizadas cubren matrices de pago, apuestas de Maryland, multiplicadores, tasas de Virginia, escáner local y navegación por pestañas.

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


## Simulador de cobertura matemática

El panel muestra cómo aumenta la probabilidad de acertar **el premio mayor** al disponer hipotéticamente de 1, 5, 10, 20 o 100 boletos **válidos y distintos** en un mismo sorteo. Cálculo exacto: `cantidad_de_combinaciones_distintas / total_de_combinaciones_posibles`, con máximo 100 %. El simulador no genera boletos adicionales, no compra nada ni garantiza retorno positivo. Jugar más también puede aumentar las pérdidas. El filtro del generador y la semilla interna no cambian la probabilidad de un boleto.

## Alcance de los archivos y de los métodos matemáticos

La biblioteca JSON generada por el proceso diario conserva todos los sorteos **disponibles en las dos fuentes públicas**, Powerball desde 2010 y Mega Millions desde 2002. No promete recuperar sorteos anteriores a la cobertura de esas fuentes ni de todas las loterías del planeta. Para el análisis descriptivo por número se usa únicamente el período de reglas actuales; la pestaña histórica conserva también los registros de reglas anteriores. La copia generada se publica como archivos JSON estáticos en Pages y como artefacto descargable de Actions; no hay base de datos de pago.

**Una bola principal determinada:** en Powerball su probabilidad exacta por sorteo justo es `5/69`; Mega Millions `5/70`; la bola especial `1/26` o `1/24`. En La Chica de dos cifras y bajo un modelo uniforme de 00 a 99, `1/100`. **Una combinación completa:** `1 / (C(n,k) × b)`, y `1/100` en La Chica con un solo número de dos cifras. Los porcentajes de frecuencia histórica se calculan como `sorteos_con_el_numero / sorteos_validos` y no son probabilidades mejores del siguiente sorteo. Una semilla produce números reproducibles, pero no descubre patrones futuros. Las técnicas «cuánticas» no transforman un sorteo justo independiente en uno predecible.

Para La Chica se enlaza al [PANI](https://www.pani.gob.hn/); falta comprobar un archivo descargable oficial y su estructura antes de añadir sorteos hondureños a la base. No se incorporan registros sin fuente o con premios acumulados no verificables.

Pruebas adicionales: `tests/test_generator.mjs` comprueba combinatoria, probabilidades, validación de rangos, reproducibilidad, preferencias e integridad del diseño. La automatización verifica además por HTTPS los nuevos recursos `assets/generator-pro.js` y `assets/lottery-pro.css`.


## Sorteos animados y comparación de simuladores

**LOTTO LAB LIVE** funciona en iPhone y escritorio sin conexión a servicios de apuestas, claves ni planes de pago. Al abrir [el estudio de sorteos](https://h4cklaboratory.github.io/dexter-fusion-studio/lotto-lab/#sorteoVirtual) puedes:

- Probar números del generador, de «Números de la suerte» o una combinación manual.
- Ver a un presentador virtual y una máquina transparente animada que extraen las bolas una a una.
- Elegir un **sorteo virtual nuevo** (crypto.getRandomValues con rechazo uniforme de sesgo módulo, mezcla Fisher–Yates) o **reproducir un sorteo oficial anterior** tomado de la biblioteca verificada para las reglas vigentes.
- Comprobar aciertos de bolas principales, bola especial y categorías premiadas documentadas, sin afirmar que el sorteo visual es oficial ni que se ha ganado dinero.
- Ejecutar 1.000 ensayos virtuales, cotejar números contra resultados publicados y explorar tendencias de los últimos 50, 200 y 500 sorteos.
- Desactivar animaciones mediante la opción de **reducir movimiento** del dispositivo.

La simulación no produce predicciones ni resultados oficiales. El resultado virtual se determina **antes** de animar las bolas. La repetición histórica es una muestra de un resultado pasado, no un sorteo nuevo. Los juegos sin histórico verificable no simulan tenerlo.

Fuentes y decisiones técnicas: [investigación de páginas de pronósticos y simuladores](INVESTIGACION-SIMULADOR-COMPETIDORES.md). Pruebas especializadas: `tests/test_draw.mjs`, `tests/test_draw_simulator.mjs` y `tests/test_draw_ui.mjs`. La acción de GitHub verifica además que el HTML y los módulos nuevos estén publicados por HTTPS.

## Estado general de las bibliotecas y del generador

Además de Powerball y Mega Millions, el proceso diario utiliza la biblioteca histórica oficial de **New York Take 5 desde 1992**, manteniendo separadas sus sesiones de mediodía y noche cuando existen. Se incluye un catálogo consultable de **48 jurisdicciones de lotería de Estados Unidos** y generadores para modalidades estatales cuyas reglas hayan sido verificadas. No significa que ya se hayan descargado todos los juegos de cada estado.

El motor mantiene las probabilidades completas internamente y muestra porcentajes individuales enteros por claridad, la sección de **Números de la suerte** (sugerencias sin ventaja demostrada), el laboratorio científico y el explorador de cobertura. Las probabilidades de jackpot se presentan como **«1 entre N»**, para no redondear valores diminutos a un 0 % engañoso.

