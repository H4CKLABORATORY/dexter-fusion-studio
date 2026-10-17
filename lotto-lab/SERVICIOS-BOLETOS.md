# LOTTO LAB — Centro de servicios para boletos y premios

Fecha de implementación: 2026-10-17. Aplicación gratuita y estática para iPhone y escritorio.

## Pestañas y alcance

**Revisar boleto**: el usuario puede ingresar una jugada, elegir su boleto generado o la sugerencia del día, indicar fecha exacta y comparar con resultados oficiales de Powerball, Mega Millions o NY Take 5. New York Take 5 distingue mediodía y noche. Los demás juegos aceptan resultados proporcionados manualmente pero se identifican como ejercicios sin verificación. No se presenta como comprobación de autenticidad, vigencia ni pago.

**Escanear código**: permite fotografiar localmente el código de barras/QR. Usa BarcodeDetector cuando el navegador lo ofrece y descarga bajo demanda la biblioteca MIT @zxing/browser@0.1.5 desde jsDelivr en iPhone/Safari como alternativa. La foto se procesa en el dispositivo: LOTTO LAB no la almacena ni envía a sus servidores. La biblioteca descargada es código de terceros y requiere Internet; puede fallar según formato o navegador. La aplicación enmascara el ID mostrando solo cuatro caracteres al final y no lo registra. IMPORTANTE: un ID leído no implica que el boleto sea válido, premiado, canjeable ni no cobrado; se debe verificar con el servicio central de la lotería. Enlaces oficiales: https://www.mdlottery.com/mobile-apps/ y https://www.valottery.com/aboutus/mobileapp .

**Premios y probabilidades**: compara la categoría de aciertos, la dificultad matemática de acertarla y los pagos oficiales base cuando son constantes. Powerball tiene ocho premios inferiores al jackpot y Power Play opcional; el segundo premio no sube más de 2 millones con Power Play. Mega Millions desde abril de 2025 tiene multiplicador integrado 2, 3, 4, 5 o 10, que debe leerse del boleto para conocer el monto exacto. Virginia Cash 5: 2 aciertos $1, 3 aciertos $5, 4 aciertos $200, jackpot variable; no se incluye EZ Match. Maryland Pick 3/4/5: solo Straight, $1 o $0.50; las modalidades Box, Fireball y Combinación requieren un cálculo distinto. California Fantasy 5 ofrece boleto gratis para 2 aciertos y otros premios variables. En California, Powerball tiene premio pari-mutuel en categorías que pueden variar. Si faltan reglas verificadas, el programa no inventa montos.

**Presupuesto**: dado un presupuesto, se muestra cuántos boletos básicos caben, cuánto costarían, y el valor matemático esperado de pagos fijos, EXCLUYENDO jackpot y pagos variables. Un promedio no significa dinero que el usuario ganará. El resultado esperado puede ser negativo; no es una recomendación de apostar. Los complementos incrementan el costo y no cambian el azar justo.

**Impuestos**: diferencia retención provisional de una estimación final elegida por el usuario. El IRS especifica 24% de retención federal para determinados premios con importe neto del costo de la apuesta superior a US$5,000. Virginia retiene 4% sobre premios pertinentes superiores a US$5,000. Maryland, según su lotería oficial en octubre de 2026, retiene 9,5 % del premio bruto para residentes de Maryland y 8,75 % para no residentes cuando el premio supera US$5.000. El formulario permite elegir residencia. El umbral federal se aplica a los beneficios netos de la apuesta y no debe confundirse con el umbral de Maryland. El cálculo final utiliza tasas federales y estatales editables; NO representa liquidación ni asesoramiento tributario y no incluye el valor en efectivo de un jackpot anunciado en anualidades.

## Fuentes oficiales

- https://www.powerball.com/powerball-prize-chart/
- https://www.megamillions.com/Media-Center/MegaMillions_New_Prize_Matrix.aspx
- https://www.valottery.com/data/draw-games/cash5
- https://www.mdlottery.com/games/pick-3-pick-4-pick-5/prize-structure/
- https://www.calottery.com/draw-games/fantasy-5
- https://www.irs.gov/instructions/iw2g
- https://law.lis.virginia.gov/admincode/title23/agency10/chapter140/section282/
- https://www.mdlottery.com/winners/how-to-claim/
- https://www.mdlottery.com/mobile-apps/
- https://www.valottery.com/aboutus/mobileapp
- https://github.com/zxing-js/browser (licencia MIT)
- https://developer.mozilla.org/en-US/docs/Web/API/BarcodeDetector

## Pruebas y despliegue

Pruebas en tests/test_services.mjs, tests/test_services_ui.mjs y tests/test_barcode.mjs; motor de cálculo assets/payout-engine.mjs; escaneo assets/barcode-reader.mjs; interfaz assets/services-ui.mjs. GitHub Actions verifica Node, Python, historiales descargados, JavaScript y acceso público HTTP. La página nunca valida un boleto contra sistemas privados de operadores ni realiza pagos.
