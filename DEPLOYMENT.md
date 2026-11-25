# Publicar TutorLoreto AI

Esta copia queda preparada para desplegar como servicio Docker en Railway. El despliegue público sirve la misma app por Internet; no reemplaza el servidor local del colegio. La biblioteca precargada seguirá disponible desde la app, pero las funciones de IA requieren configurar un servicio Ollama accesible desde el alojamiento.

## Antes de crear el servicio

- El `Dockerfile` está en la raíz del repositorio de esta aplicación. Si Railway conecta este repositorio, deja la raíz del servicio en `.`.
- No subas `.env` ni compartas sus claves. `.env` está excluido del contexto Docker y de Git.
- Usa únicamente cuentas de demostración y datos ficticios mientras configuras el alojamiento.

## Servicios y variables

1. Instala Railway CLI con `npm i -g @railway/cli` (requiere Node.js 16 o superior). Abre PowerShell en la carpeta `PMV1_codigo` y ejecuta `railway up`. La primera vez abre el inicio de sesión y puede crear el proyecto y servicio. El comando sube el código de esta carpeta y Railway compila el `Dockerfile`; respeta `.gitignore`, donde `.env` está excluido.
2. Añade un servicio MySQL al mismo proyecto. En las variables del servicio web configura `DATABASE_URL` como referencia privada al `MYSQL_URL` del servicio MySQL, por ejemplo `${{MySQL.MYSQL_URL}}` (usa el nombre exacto que aparezca en Railway).
3. Define `COOKIE_SECURE=true` en el servicio web. El dominio público de Railway usa HTTPS; esta opción hace que la cookie de sesión solo viaje por conexiones seguras.
4. Enlaza la carpeta con el proyecto y servicio creados. Desde PowerShell ejecuta `railway ssh --service <servicio-web> -- python -m app.infrastructure.inicializar_esquema_hosted`; la primera conexión puede pedir registrar una clave SSH. El script aplica el esquema sin borrar registros. Luego ejecuta `railway ssh --service <servicio-web> -- python -m app.infrastructure.crear_directivo` para crear el primer directivo; ingresa sus credenciales en la terminal interactiva.
5. En el servicio web configura la comprobación de salud como `/healthz`. El proceso escucha el puerto que entrega Railway mediante `PORT`.

La aplicación acepta tanto `mysql+pymysql://...` como `mysql://...` en `DATABASE_URL`. El archivo `.env` local no se necesita en Railway.

## IA

La configuración actual apunta a Ollama local (`127.0.0.1`), que dentro de un contenedor no es el Ollama de tu computadora. Para habilitar explicaciones y ejercicios en el sitio público, configura una URL de Ollama alcanzable desde el servicio, un modelo cloud compatible y `OLLAMA_API_KEY` como variable secreta del proveedor. No publiques esa clave en GitHub, en el código ni en capturas.

Las solicitudes académicas enviadas a un modelo cloud salen del servidor escolar. No ingreses nombres, correos, contraseñas ni información identificable de alumnos en las consultas de prueba.

## Dirección temporal y dominio propio

Después de desplegar, crea el dominio temporal con `railway domain` o desde Networking en el panel. `railway up` por sí solo no expone el servicio públicamente. El plan gratuito suspende servicios inactivos, limita los recursos mensuales y no permite dominios personalizados. El plan Hobby figura desde US$5 al mes, con consumo adicional si excede el crédito incluido. Un dominio `.com` se compra por separado.

Cuando tengas el dominio, añádelo en la sección Networking del servicio y registra exactamente los registros DNS CNAME y TXT que Railway indique. Railway aprovisiona HTTPS después de verificar el dominio.

## Comprobaciones después del despliegue

- Abre `/healthz` y confirma `{"status":"ok"}`.
- Abre `/api/estado` y `/api/asignaturas` para comprobar la app y MySQL.
- Abre `/api/ia/estado` para revisar si el servicio y modelo de IA están configurados.
- Crea un directivo y una cuenta de prueba; valida inicio, cambio de contraseña, biblioteca y prácticas con datos ficticios.
- Descarga una copia de seguridad de MySQL antes de cargar datos reales del colegio.

Referencias: [Dockerfiles en Railway](https://docs.railway.com/builds/dockerfiles), [MySQL en Railway](https://docs.railway.com/databases/mysql), [dominios](https://docs.railway.com/networking/domains/working-with-domains), [precios](https://docs.railway.com/pricing).
