# LOTTO LAB DEXTER — Investigación matemática científica v3

Fecha del experimento: 2026-10-17. Datos descargados directamente de las fuentes oficiales de NY Open Data durante cada ejecución de GitHub Actions. Investigación estadística educativa, no un pronóstico de números ganadores.

## Meta, hallazgos y nivel de confianza

El nuevo motor analiza probabilidades exactas de todos los niveles de coincidencia, establece bandas conservadoras de fluctuación histórica y prueba fuera de muestra un modelo experimental de frecuencias. Son matemáticas comprobables, no física cuántica operativa ni un sistema capaz de alterar un sorteo justo.

La combinación de estos métodos en LOTTO LAB constituye una arquitectura propia. No se presenta como un teorema descubierto ni un método probado de ganar más dinero.

## Capa 1: combinatoria exacta

Para un boleto fijo con k números distintos de un conjunto de n, la probabilidad de obtener exactamente r coincidencias es:

P(R=r) = C(k,r) * C(n-k,k-r) / C(n,k)

Si existe una bola especial independiente entre b alternativas, se multiplica la probabilidad por 1/b para acierto y por (b-1)/b para desacierto. Las cuentas usan enteros grandes (BigInt) y se verifica que la suma de todas las categorías sea exactamente 100 %.

Powerball: C(69,5) * 26 = 292.201.338 combinaciones posibles. Las 9 categorías premiadas proporcionan una probabilidad total de premio cercana a 1 entre 24,87.
Mega Millions, reglas desde abril de 2025: C(70,5) * 24 = 290.472.336. Sus 9 categorías premiadas suman una posibilidad cercana a 1 entre 23,07.
Virginia Cash 5: C(45,5) = 1.221.759. El cálculo excluye el suplemento opcional EZ Match.
California Fantasy 5 y New York Take 5: C(39,5) = 575.757. No se inventan cantidades monetarias para los premios variables.
Pick 3, Pick 4 y Pick 5 en orden exacto: 10^d resultados, donde d es la cantidad de posiciones. Las formas de acertar exactamente r posiciones son C(d,r)*9^(d-r); las coincidencias de posiciones no se presentan automáticamente como premios.

### Cobertura en varios sorteos

Para m combinaciones distintas en un sorteo entre N resultados posibles, p=m/N. Para t sorteos independientes con la misma cobertura teórica:

P(al menos un acierto completo en t sorteos) = 1-(1-m/N)^t.

El motor evalúa esta expresión numéricamente con -expm1(t*log1p(-p)) para evitar errores de redondeo de números muy pequeños. No recomienda gastar más ni garantiza recuperar lo gastado.

## Capa 2: diagnóstico conservador de fluctuaciones

En un sorteo justo de k números entre n, la probabilidad teórica de que aparezca un número determinado es p0=k/n por sorteo.

Para D sorteos independientes, construimos una banda simultánea conservadora de nivel nominal 95 % utilizando Hoeffding y una unión de eventos:

epsilon = sqrt(log(2*n/alpha)/(2*D)), donde alpha=0,05.

Se evalúa cada frecuencia observada contra el intervalo [p0-epsilon,p0+epsilon] limitado a [0,1]. Estar dentro NO demuestra que el sorteo sea perfecto. Una salida fuera NO demuestra fraude ni capacidad predictiva.

## Capa 3: auditor de Brier, sin mirar futuros sorteos

Para cada número i se calcula ANTES de conocer el siguiente resultado una probabilidad marginal experimental:

q_i = (aciertos_historicos_i + lambda * p0)/(sorteos_vistos + lambda), con lambda=120.

La referencia justa propone q_i=p0. En orden cronológico, el modelo usa solo sorteos anteriores, calcula el Brier Score medio sumando (q_i-y_i)^2 para cada número, y luego incorpora el resultado recién evaluado.

Indicador descriptivo:
Cambio porcentual Brier = 100*(Brier_justo - Brier_historico)/Brier_justo.

Positivo significa una mejora OBSERVADA en la muestra; no es prueba prospectiva de ventaja. Negativo significa que la referencia justa tuvo menos error. Estas probabilidades marginales no equivalen a una distribución completa sobre combinaciones.

## Resultados reales, corte 2026-10-17

| Lotería | Sorteos del régimen | Sorteos evaluados | Cambio de Brier | Números fuera de banda |
|---|---:|---:|---:|---:|
| Powerball | 1.420 | 180 | -0,06006 % | 0 |
| Mega Millions | 160 | 100 | -0,26056 % | 0 |
| New York Take 5 | 12.670 | 180 | -0,00680 % | 0 |

El modelo histórico de frecuencia suavizada NO superó la referencia matemática de sorteo justo en ninguna de las tres bibliotecas. Esto no agota la evaluación de todos los modelos posibles, pero no se ha identificado evidencia de capacidad de pronosticar el próximo sorteo.

El archivo de datos scientific-report.json se regenera cada día junto al historial oficial, guarda fuentes, periodos y resultados reproducibles; la aplicación lo consulta cuando coincide con la biblioteca local y, de lo contrario, realiza el mismo cálculo en el navegador.

## Errores detectados y corregidos

- El antiguo validador de Powerball excluía el 69 en preferencias explícitas.
- Los juegos estatales de cinco bolas podían producir el 0 y omitir el último número válido.
- En algunos juegos los filtros alto/bajo utilizaban 50 en lugar de la mitad del intervalo del juego.

Los nuevos tests exigen números principales entre 1 y n, validan máximos y rechazan ceros, exceptuando juegos explícitos de cifras 00-99 o con dígitos desde 0.

## Límites y fuentes

No se calculan rentabilidades netas ni premios futuros reales. Jackpot, cantidad de ganadores, costos, suplementos, pagos variables, impuestos y descuentos cambian los resultados monetarios. Los valores brutos esperados excluyen el premio mayor y no deben confundirse con la expectativa de rendimiento total.

Referencias oficiales:
- https://www.powerball.com/powerball-prize-chart
- https://www.megamillions.com/Media-Center/MegaMillions_New_Prize_Matrix.aspx
- https://www.valottery.com/data/draw-games/cash5
- https://www.calottery.com/draw-games/fantasy-5

Referencia sobre puntuaciones propias de probabilidades:
- Kartik Waghmare y Johanna Ziegel (2026), Proper Scoring Rules for Estimation and Forecast Evaluation, Annual Review of Statistics and Its Application. https://doi.org/10.1146/annurev-statistics-042424-050626

Reproducir localmente: ejecutar primero la descarga oficial con Python; después ejecutar node lotto-lab/scripts/build_science.mjs lotto-lab/data y node --test lotto-lab/tests/test_*.mjs. GitHub Actions realiza esas operaciones y publica resultados después de las validaciones automáticas.
