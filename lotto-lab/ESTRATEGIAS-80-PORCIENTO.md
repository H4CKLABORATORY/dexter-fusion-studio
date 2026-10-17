# Investigación LOTTO LAB — Objetivo del 80 % (2026-10-17)

## Conclusión comprobada

La historia de Stefan Mandel describe **cobertura de combinaciones**, no predicción del próximo sorteo. En la lotería Virginia 1992 había aproximadamente 7,1 millones de resultados posibles. Se intentaron comprar millones de combinaciones diferentes con inversores y recursos logísticos. No se obtuvo una fórmula que convierta un boleto en una predicción del 80 %.

El método más preciso para cubrir resultados es contar sin duplicados las combinaciones válidas y medir la proporción del espacio ocupado. Para un sorteo justo con N resultados y m boletos **únicos** realmente jugados en ese sorteo:

- P(acierto completo) = m / N.
- m objetivo 80 % = techo(0,8*N).
- Comprar o mostrar m boletos iguales NO multiplica la cobertura.
- El valor real del premio puede depender de ganadores compartidos y otros factores.

Ejemplos con precio básico vigente en octubre 2026:

| Juego | Resultados posibles N | Boletos distintos para >=80% | Costo teórico |
|---|---:|---:|---:|
| Powerball | 292.201.338 | 233.761.071 | US$467.522.142 |
| Mega Millions | 290.472.336 | 232.377.869 | US$1.161.889.345 |

Estas sumas son gigantes y NO garantizan beneficio o cobro integral del jackpot. El sitio no compra ni recomienda adquirir boletos. El 80 % no puede obtenerse por una semilla o el historial de sorteos bajo el supuesto de independencia y equidad.

## Otro objetivo: al menos un premio pequeño

Las loterías tienen categorías secundarias de premio. Para un billete básico en sorteos **independientes**, la probabilidad de algún premio es aproximadamente 1/24,87 en Powerball y 1/23,07 en Mega Millions. Un boleto en **cada sorteo distinto** llega matemáticamente a 80 % de **haber obtenido al menos un premio** tras ~40 sorteos Powerball o ~37 Mega Millions, usando:

t = techo(log(1-0,80)/log(1-premio_por_boleto)).

No equivale a 80 % de tener ganancias netas ni de ganar el premio mayor. No se emplea esa fórmula como aproximación de boletos correlacionados dentro de un mismo sorteo.

## Investigaciones adicionales y cuándo sirven

### Combinadics, indexación y desindexación directa

Stack Overflow resume múltiples técnicas de enumeración de k entre n sin repetición y con poca memoria (Gray Codes, iteradores y ranking lexicográfico). El motor nuevo puede recuperar una combinación a partir de su índice sin generar en memoria cientos de millones de combinaciones. Un conjunto de muestras pequeñas utiliza índices coprimos que impiden duplicados **dentro de la muestra**. Eso permite medir mejor la cobertura real, pero no produce combinaciones ganadoras privilegiadas.

### Diseños de cobertura (covering designs)

Una familia estructurada de boletos puede cubrir ciertos resultados **parciales** de una forma más conveniente. NIST estudia métodos de cobertura combinatoria. La palabra “garantía” siempre debe explicitar **la condición**: por ejemplo, un mínimo de aciertos solo cuando todos los números ganadores principales están dentro del conjunto inicial elegido. Para acertar el jackpot con 80 %, ninguna reorganización evita cubrir al menos el 80 % de los resultados totales.

### Números poco populares

La investigación de R. McHale en Significance (2012) y otras publicaciones sobre selección consciente sugiere que fechas de cumpleaños o secuencias atractivas son más populares entre compradores. Evitarlas **no cambia las probabilidades de salir**, pero podría reducir el riesgo de compartir premio en algunos juegos, si se llegara a ganar. LOTTO LAB contiene una estrategia opcional que evita 1–31 en juegos de cinco bolas cuando las reglas lo permiten. No se dispone de datos públicos de compra de boletos para probar una reducción concreta ni para dar porcentajes mayores.

### Qué aporta y qué no aporta el foro Reddit

El tema de r/askmath que propuso una “bola mágica” que da respuestas infalibles sobre el futuro admite la estrategia de búsqueda binaria: harían falta techo(log2(N)) respuestas binarias verdaderas. **No existe ese oráculo real**; por eso no proporciona datos nuevos para un sorteo futuro. El comentario sobre indexar combinaciones es una técnica computacional legítima y es la parte incorporada.

### Qué aporta y qué no aporta Stefan Mandel

Mandel había utilizado fondos de inversores y una operación material para tratar de cubrir resultados. Su caso no demuestra que exista un número “con más probabilidad de salir” dentro de un sorteo justo, ni que una estrategia actual sea económicamente favorable. Las reglas de venta, costos e impuestos hoy son diferentes.

## Integración reproducible

- assets/coverage-engine.mjs: combinadics BigInt, inversión índice -> boleto, prevención de duplicados en muestras pequeñas y cobertura exacta.
- assets/coverage-ui.mjs: metas del 10, 50, 80 y 95 %, costo estimado a precio conocido, y diferenciación entre cualquier premio y acertar todas las bolas.
- tests/test_coverage.mjs: índices reversibles, rangos legítimos y costos del 80 %.
- assets/exact-engine.mjs y scripts/verify_exact.py: cálculos de fracciones exactas en JavaScript y verificación independiente usando Python Fraction.
- La automatización de GitHub ejecuta pruebas en cada cambio y publica el sitio de iPhone solo si las pruebas pasan.

## Referencias originales y de contraste

1. Stefan Mandel, NPR/CapRadio: https://www.capradio.org/news/npr/story?storyid=659988605
2. Stefan Mandel, historia 1992 en The Washington Post: https://www.washingtonpost.com/history/2019/03/27/he-won-lottery-times-using-math-his-biggest-jackpot-still-came-down-luck/
3. Algoritmos de combinaciones: https://stackoverflow.com/questions/127704/algorithm-to-return-all-combinations-of-k-elements-from-n
4. Reddit, ejercicio hipotético de adivinación binaria: https://www.reddit.com/r/askmath/comments/1dwdj33/what_is_the_most_efficient_way_to_predict_the/
5. NIST, medición combinatoria: https://www.nist.gov/publications/combinatorial-coverage-measurement
6. R. McHale, Playing the lottery with a little bit of stats know-how, Significance 2012: https://onlinelibrary.wiley.com/doi/10.1111/j.1740-9713.2012.00540.x
7. Powerball premio y probabilidades: https://www.powerball.com/powerball-prize-chart
8. Mega Millions reglas actuales: https://www.megamillions.com/How-To-Play.aspx
9. El enlace Yahoo proporcionado: https://es-us.finanzas.yahoo.com/noticias/como-ganar-la-loteria-segun-un-matematico-que-lo-logro-14-veces-173327332.html — el servidor bloqueó la lectura directa (HTTP 429), por lo que se contrastó la historia con NPR y prensa independiente.
