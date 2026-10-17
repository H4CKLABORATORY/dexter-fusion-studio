# LOTTO LAB — Cobertura de loterías de Estados Unidos

Fecha de revisión: 17 de octubre de 2026.

## Qué se incorporó

- Catálogo de **48 jurisdicciones** donde hay lotería estatal o territorial: **45 estados**, Washington D. C., Puerto Rico e Islas Vírgenes estadounidenses. Fuente: https://www.naspl.org/faq
- Lista oficial con identificador estatal, nombre y enlace a fuente específica únicamente en los casos comprobados; el resto se vincula al directorio NASPL, sin inventar URLs.
- Nuevos juegos con reglas y matrices verificadas: Maryland Pick 3/4/5 exactos; Virginia Pick 3 exacto y Cash 5; California Fantasy 5; New York Take 5. Se mantienen Powerball, Mega Millions y La Chica de Honduras.
- Comparación de **probabilidad exacta de acertar todos los números**, desde el juego con más posibilidades hasta el de menos, sin presentar ese porcentaje como rentabilidad.
- Soporte del motor para números con orden de 3, 4 y 5 dígitos y para combinaciones de 5 números entre 39 o 45. Los números del boleto se pueden generar sin acceso a un historial.

## Historias verificadas y estado de descarga

**Historiales oficiales programados en GitHub Actions**:
1. Powerball: fuente de NY Open Data `d6yy-54nr`, desde 2010.
2. Mega Millions: fuente de NY Open Data `5xaw-6ayf`, desde 2002.
3. New York Take 5: fuente de NY Open Data `dg63-4siq`, desde el 17/01/1992; las sesiones midday y evening se registran separadamente cuando existen.

La acción de GitHub valida las tres bibliotecas, comprueba el catálogo y publica los datos como archivos estáticos JSON, sin servidores de pago. Una ejecución satisfactoria es necesaria para afirmar que el nuevo histórico está desplegado.

**Solo reglas verificadas, sin histórico local todavía**: Maryland Pick 3/4/5, Virginia Pick 3 y Cash 5, California Fantasy 5. No se muestran frecuencias inventadas. Las loterías de las otras jurisdicciones están **catalogadas**, no tienen por ello todas sus modalidades y sorteos importados. Scratch-offs y sorteos retirados no están integrados.

La biblioteca contiene resultados ganadores publicados; **no** contiene números elegidos por todos los compradores, porque esos datos no son públicos en estas fuentes.

## Referencias primarias para verificar reglas

- https://www.mdlottery.com/games/pick-3-pick-4-pick-5/prize-structure/
- https://www.valottery.com/data/draw-games/pick3
- https://www.valottery.com/data/draw-games/cash5
- https://www.calottery.com/es-us/draw-games/fantasy-5
- https://nylottery.ny.gov/draw-game?game=take5
- https://data.ny.gov/Government-Finance/Lottery-Take-5-Winning-Numbers-Beginning-1992/dg63-4siq
- https://www.naspl.org/naspl-lottery-members

## Interpretación matemática

Para un juego de `k` bolas distintas entre `n` sin bola especial: combinaciones `C(n,k)`. Con otra bola de `b` opciones: `C(n,k) × b`. Para un juego ordenado de `d` dígitos entre 0 y 9, `10^d` resultados posibles.

Un boleto tiene probabilidad `1/N` de acertar una combinación concreta. Con `m` boletos **distintos** en el mismo sorteo la cobertura matemática es `m/N` (hasta 100 %). Ningún patrón de números, semilla oculta ni frecuencia pasada garantiza una ventaja sobre un sorteo independiente y justo. Mayor probabilidad de acertar no implica premios mayores ni retorno positivo.

## Pendientes de expansión

- Evaluar fuentes digitales históricas verificables en cada estado y agregar el resultado solo después de validar sus reglas, licencias y datos.
- Ampliar el catálogo con cada modalidad estatal a medida que pueda comprobarse su matriz actual.
- No automatizar raspaditos ni sorteos sin resultados estructurados confiables; evitar prometer una base histórica mundial o nacional completa antes de obtenerla.
