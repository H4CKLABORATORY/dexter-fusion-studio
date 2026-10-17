# LOTTO LAB — Investigación comparativa y estudio de sorteos animado

**Fecha:** 2026-10-17. **Propósito:** mejorar un laboratorio educativo y gratuito, manteniendo pruebas científicas y respeto por fuentes originales. La interfaz, código y animaciones de LOTTO LAB son desarrollos propios, no código de terceros copiado.

## 1. Qué ofrece Lotto Predictions

Fuentes investigadas:
- Página principal: https://lotto-predictions.com/es/
- Guía de predicciones: https://www.lotto-predictions.com/es/player-guide/lottery-predictions/
- Simulador y ruedas: https://www.lotto-predictions.com/es/player-guide/lottery-simulator/
- Cómo puntúa los números: https://www.lotto-predictions.com/es/player-guide/number-predictions/
- Modelado IA en dos etapas: https://www.lotto-predictions.com/es/blog/ai-lottery-predictions-explained/
- Ruedas combinatorias: https://lotto-predictions.com/es/wheels/

En su presentación comercial y documentación, la plataforma describe: cuatro métodos de pronóstico (equilibrio, IA, consenso comunitario, usuarios), análisis de frecuencias y ausencias, comparación de ventanas de 200 a 500 sorteos, patrones alto/bajo par/impar, distintas ruedas de cobertura, predicciones archivadas y un simulador. Parte del simulador y las ruedas avanzadas requieren suscripción premium.

**Lo que sí se puede reproducir legítimamente:** fórmulas combinatorias, análisis de datos publicados, experimentación con simuladores, pruebas retrospectivas antes de emitir una predicción y visualizaciones propias. No se recopilan datos privados de usuarios ni se extrae ni copia código, diseño, modelos propios o bibliotecas protegidas por derechos de terceros.

**Lo que NO está demostrado:** que una bola "atrasada" tenga más probabilidad física de salir. El propio sitio separa su P_BASE teórica de un indicador ajustado P_EFF que aumenta con la ausencia. P_EFF es una puntuación heurística de su sistema; no constituye una ventaja demostrada ante sorteos justos independientes. Los patrones estructurales pueden ser más frecuentes simplemente porque corresponden a un mayor número de combinaciones posibles, no por una fuerza que atraiga esos resultados. Garantías de ruedas solo se aplican bajo condiciones explícitas sobre los números ganadores.

## 2. Páginas similares contrastadas

- Lottery USA: https://www.lotteryusa.com/ — resultados, archivo por jurisdicción, comprobación de números anteriores y quick picks. Se toma la idea funcional de ofrecer acceso rápido a los resultados y comparar boletos. Sus estadísticas y datos no se copian: LOTTO LAB usa sus archivos oficiales verificados.
- The Lottery Lab: https://www.thelotterylab.com/tools — simulador educativo, frecuencia, pruebas chi-cuadrado, ruedas y cotejo de resultados. Es un referente de separación entre herramientas descriptivas y resultados de apuestas ficticias.
- LottoMetrics: https://www.lottometrics.app/ — varias loterías, archivos, descargas CSV/JSON y análisis histórico; referencia para transparencia de fuentes.
- Lotalytics: https://lotalytics.com/ — estudio de frecuencias y generador configurable; explícitamente reconoce que no predice sorteos justos.
- LotteryHeat: https://lotteryheat.com/ — comprobación de boletos, ventanas temporales y distribución de frecuencias.

La investigación no es una verificación independiente de que sus modelos mejoren las probabilidades. No se reproduce material privado, no se depende de sus servidores y LOTTO LAB no requiere cuentas ni pagos.

## 3. Funciones originales añadidas a LOTTO LAB

**Estudio de sorteos animado**, archivos assets/draw-simulator.mjs y assets/draw-ui.mjs:
- Presentador ilustrado con CSS, vestuario de estudio, una máquina transparente con bolas giratorias y animaciones de extracción una por una.
- Dos modos claramente separados: sorteo virtual nuevo y reproducción de un resultado histórico ya publicado.
- Botones para probar la combinación del generador, los números de la suerte del día o números introducidos manualmente. Reglas distintas para juegos de dígitos, bolas principales y bola especial.
- Evaluación de coincidencias, niveles de premio cuando existen tablas documentadas, y énfasis explícito en que ninguna simulación significa premio real.
- 1.000 sorteos virtuales y resultados acumulados para demostrar el comportamiento de la distribución, además de comprobar un boleto contra el archivo histórico disponible.
- Comparador de 50, 200 y 500 sorteos con frecuencias y paridad. Solo descriptivo.
- Compatible con el teléfono: sin imágenes pesadas ni cuentas; movimiento reducido y animación cancelable cuando el juego cambia.

**Motor científico del sorteo virtual:** cada posición se obtiene de crypto.getRandomValues a través de rechazo para eliminar el sesgo de módulo. Para bolas distintas se aplica Fisher–Yates parcial sin reemplazo. La bola especial se obtiene de un grupo independiente. El resultado queda fijado ANTES de comenzar la animación; el presentador únicamente lo revela.

**Modo histórico:** escoge un registro del historial oficial y muestra la fecha de aquel sorteo. No se considera una predicción; se verifica la matriz actual para evitar mezclar reglas antiguas.

**Experimento por repetición:** el motor de 1.000 sorteos calcula coincidencias y compara la frecuencia observada con la esperanza matemática de un sorteo uniforme. Está limitado para evitar bloqueos en iPhone.

## 4. Verificación y límites

Archivos de test: tests/test_draw_simulator.mjs. El CI de GitHub comprueba mezclas válidas, rango de cada lotería, ausencia de bolas principales repetidas, separación de la especial, parseo manual, resultados históricos y formatos de simulación.

La reproducibilidad de pruebas se logra inyectando fuentes pseudoaleatorias controladas; **solo en las pruebas**, nunca en el sorteo virtual del navegador, que utiliza crypto.getRandomValues cuando está disponible.

No hay servidor nuevo, integración comercial con terceros, copia de la animación de otros sitios, ni apuestas reales. Una lotería justa no se vuelve predecible al simular millones de resultados: la simulación sirve para comprender las probabilidades.

## 5. Posibles mejoras futuras condicionadas a evidencia

- Gráficas visuales de coocurrencias y patrones por ventana con pruebas de calibración, sin atribuir causalidad a ruido estadístico.
- Ruedas completas y abreviadas con garantías condicionales calculadas exhaustivamente y documentación de requisitos; sin afirmar un porcentaje de jackpot mayor que su cobertura real.
- Registro local optativo de pronósticos previos, bloqueados por fecha, y evaluación posterior contra fuentes oficiales; antes de afirmar cualquier ventaja se necesitarían resultados suficientes fuera de muestra y ajustes por múltiples pruebas.
- No implementar "predicciones" o "P_EFF" como probabilidad real sin evidencia cuantitativa validada.
