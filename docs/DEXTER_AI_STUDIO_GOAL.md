# DEXTER AI STUDIO — especificacion minima para OpenCode Goal

## Producto
Aplicacion audiovisual propia, inspirada en la facilidad de los generadores de imagen/video, sin copiar codigo, marca ni interfaz protegida. Debe operar en Cloudflare y permitir cuentas, generaciones y eventual cobro de creditos.

## Estado confirmado al crear este documento
- Vista previa interactiva descrita en ChatGPT; **no es codigo desplegado**.
- Todavia no hay un repositorio separado confirmado con el nombre DEXTER AI STUDIO. Buscar antes de crear.
- No hay prueba de Stripe Checkout ni de generaciones Higgsfield funcionando en produccion.
- El editor independiente DEXTER Fusion Studio en este GitHub usa Python/Qt/FFmpeg. **No modificarlo al crear la web**.

## Tecnologias propuestas
Frontend React/TypeScript/Tailwind; Workers para API, D1 para datos, R2 para renders, colas asincronas donde corresponda; Stripe Checkout en modo test. API de generacion por adaptadores de proveedor autorizados; sesiones y controles de costes.

## Fases con evidencia
1. **MVP local:** base compilable, interfaz oscura/violeta responsive, rutas, cuenta, trabajos y galeria; pruebas de build y flujos basicos. Sin funciones simuladas presentadas como reales.
2. **IA:** verificar API oficial, autenticacion, limites, precios y derechos de reventa antes de generar contenido; adaptador, trabajo asincrono, polling/webhook y almacenamiento con controles.
3. **Pagos:** Stripe en modo test, firma de webhooks, idempotencia, transacciones de credito, limites de gasto y autorizacion comercial.
4. **Despliegue:** configurar secretos en Cloudflare y probar URL real solo con permiso y credenciales del propietario.
5. **Fusion Studio:** integrar por API separada tras verificar la app web.

## Restricciones
- No exponer ningun secreto recibido por chat. Rotar claves que ya se hayan compartido.
- Higgsfield solo si la licencia/contrato vigente autoriza ese tipo de producto y reventa; si no, dejar desactivado comercialmente y proponer proveedor autorizado.
- No declarar `funcional` por haber creado botones ni `publicado` sin URL probada.
- Antes de editar, inspeccionar Git, ramas, checkpoints y directorio de trabajo real.
- Cambios en rama separada, pruebas y CHECKPOINT.md con SHA, error, siguiente tarea y evidencia.

## Contrato de finalizacion del primer objetivo
- Directorio independiente para DEXTER AI STUDIO, sin tocar los archivos de Fusion Studio.
- Frontend que se compile realmente, arranque de manera local, validacion basica y vistas de proyectos y generacion.
- API con rutas reales aunque proveedor externo aun se mantenga deshabilitado hasta configurar credenciales.
- CHECKPOINT.md que diga que esta verificado y que sigue faltando, sin afirmar ventas ni generacion de videos.
