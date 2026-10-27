# HERMES Mobile Agent — ejecución desde iPhone (presupuesto $0)

Este módulo prepara una ruta **sin pago obligatorio** para dirigir OpenCode desde iOS. El iPhone es un cliente: el agente necesita un host activo (PC propia o runner temporal). Claude por API **no es ilimitado ni gratis**. Configurar Claude es opcional y no se habilita automáticamente.

## Arquitectura

iPhone (OpenCode iOS Client) → servidor OpenCode protegido → proveedor de modelo configurado → repositorios GitHub → pruebas y pull requests.

- No publicar el puerto de OpenCode abiertamente en Internet.
- Usar túnel autenticado y HTTPS. No guardar tokens en el repositorio.
- Crear ramas por tarea y PR para revisión; no hacer push directo a `main`.
- Establecer límite de iteraciones, tiempo, permisos y costo; detenerse ante fallos reiterados.
- Guardar progreso en `HERMES_CHECKPOINT.md` y registrar pruebas verificables.
- No declarar funciones terminadas sin pruebas.

## Proveedores

1. **Gratis y local:** Ollama + modelo de código disponible en la PC. La PC debe estar encendida.
2. **Gratis y remoto, sujeto a cuotas:** proveedor que ofrezca una cuota gratuita compatible con OpenCode. Verificar términos y límites antes de configurarlo. No garantiza ejecución continua.
3. **Claude (opcional):** solo si el propietario habilita credenciales y acepta el precio o un acceso gratuito válido. Nunca solicitar claves por chat ni incluirlas en commits.

## Ejecución inicial (en el host, no en el iPhone)

1. Instalar OpenCode siguiendo la documentación oficial de la versión elegida.
2. Configurar el proveedor de modelo desde OpenCode.
3. Probar una tarea pequeña en una rama y comprobar que se genera un PR.
4. Iniciar el servidor OpenCode en una interfaz privada, protegida con autenticación.
5. Conectar el cliente iOS mediante un túnel seguro.
6. Probar desconexión/reconexión y recuperación desde checkpoint.

## Definición de terminado

- Cambios reales en GitHub y PR revisable.
- Pruebas ejecutadas y resultados registrados.
- Documentación para ejecutar y desplegar.
- Limitaciones y pasos manuales explícitos.
- Ninguna suscripción ni recurso facturable activado sin aprobación.

## Primer objetivo

Conseguir que el cliente iPhone pueda ordenar una modificación pequeña a un repositorio de prueba, y recibir el enlace a un PR. Después conectar objetivos persistentes y los proyectos 1UP Anime, DEXTER HERMES y Logistics Studio.

**Estado:** plan y protocolo preparados. No hay servidor ni modelo remoto conectado todavía.
