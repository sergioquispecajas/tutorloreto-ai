# TutorLoreto AI — PMV1, PMV2 y PMV3 · 

**Proyecto independiente de prueba.** Están implementados en `frontend/index.html`, `styles.css`, `app.js` con navegación móvil. El proyecto incluye FastAPI, arquitectura hexagonal, repositorio MySQL y un adaptador para explicaciones, prácticas y recomendaciones mediante **Ollama local u Ollama Cloud**.

## Ejecutar esta copia en Windows desde `PMV1_codigo`

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8002
```

Navega a **http://127.0.0.1:8002**. Se usa otro puerto para no confundir esta versión con la original que estaba en el 8000. La barra del móvil permite recorrer Inicio, Áreas, Biblioteca, Consulta y Ayuda.

- Si quieres acceder a la **misma base de datos MySQL**, copia **localmente** tu `.env` original a esta nueva carpeta `PMV1_codigo`; el archivo **no** está incluido en el ZIP. Esto hará registros reales en esa base. Mantén una copia de seguridad y no compartas contraseñas.
- Una instalación nueva registra las 11 áreas base desde `sql/schema.sql`. En una base ya existente, ejecuta `sql/ampliar_asignaturas_opcional.sql` para agregar las que falten; usa `INSERT IGNORE`, así conserva los cursos y registros anteriores. Revisa la lista con tu escuela.
- Para IA local, instala Ollama y descarga el modelo configurado. En Railway usa Ollama Cloud con `OLLAMA_BASE_URL=https://ollama.com`, un modelo cloud disponible y `OLLAMA_API_KEY` guardada como variable secreta; los detalles están en `DEPLOYMENT.md`. El endpoint `POST /api/consultas/{id}/explicacion` produce y almacena la respuesta solo si el servicio responde; de lo contrario presenta un mensaje de error, **sin inventar una explicación**.
- El archivo `.env.example` contiene solo datos de ejemplo, no credenciales reales.
- Comprueba `GET /api/estado` y `GET /api/ia/estado` desde la pantalla **Conexión**.
- Para probar acceso escolar mediante LAN, usa `--host 0.0.0.0 --port 8002` únicamente en la red del colegio y abre desde el segundo dispositivo `http://IP-DEL-SERVIDOR:8002`.

## PMV 2 y PMV 3

La extensión agrega perfiles de aprendizaje asociados a la cuenta del alumno, práctica adaptada con ejercicios creados por Ollama, revisión de respuestas e historial por tema con avance y recomendaciones de IA. La dificultad sugerida empieza en básico; con menos de 60% de aciertos se mantiene básica, entre 60% y 84% pasa a intermedia, y desde 85% propone reto. También se puede elegir el nivel manualmente.

- Para una base que ya usaba PMV1, ejecuta `sql/pmv2_3.sql` en MySQL Workbench antes de abrir **Mi grado**, **Practicar** o **Mi progreso**. El script crea tablas y agrega una columna nullable; conserva todas las filas de consultas existentes.
- Para una instalación nueva, `sql/schema.sql` ya incluye las tablas de PMV2 y PMV3.
- Ollama local o Cloud debe estar activo y el modelo configurado para generar ejercicios y el análisis de avance. Si el servicio no responde o devuelve datos inválidos, la aplicación informa el error y no inventa ejercicios ni recomendaciones.
- Las consultas y prácticas nuevas quedan asociadas al perfil de la cuenta del alumno, por lo que su historial se conserva al iniciar sesión desde otro dispositivo conectado al servidor escolar.
- Las estadísticas de progreso usan respuestas efectivamente registradas. Los intentos sin responder no cuentan como acierto o error.

## Biblioteca de cursos

La Biblioteca muestra los 11 cursos devueltos por `/api/asignaturas` y 20 temas locales por curso (220 en total), organizados en cuatro temas para cada grado de secundaria. Cada tema ofrece teoría, práctica precargada que puede guardarse en el seguimiento PMV3, opción de crear otro ejercicio con Ollama y búsqueda de videos en YouTube. El filtro inicia en el grado del alumno y permite explorar los demás. Es una ruta amplia vinculada a las competencias del Currículo Nacional: el CNEB establece competencias, capacidades, estándares y desempeños, mientras cada institución organiza su programación anual y puede contextualizar o ampliar los temas. La teoría y las prácticas precargadas funcionan desde el servidor escolar sin conexión externa; YouTube requiere Internet.

## Acceso escolar

Los directivos y docentes crean las cuentas desde **Cuentas del colegio** con correo, grado, fecha de vigencia y contraseña temporal. El alumno cambia la contraseña temporal al iniciar por primera vez. Al vencer la fecha o desactivarse una cuenta, se rechaza el inicio de sesión. Las contraseñas se guardan con PBKDF2 y las sesiones se guardan como hashes en MySQL.

- Para una base ya preparada con PMV2/PMV3, ejecuta `sql/usuarios_login.sql` en MySQL Workbench. El script agrega tablas; no borra perfiles, consultas ni prácticas.
- Desde la consola abierta en `PMV1_codigo` y con `.venv` activado, crea el primer directivo con `python -m app.infrastructure.crear_directivo`. El programa solicita correo y contraseña sin mostrarlos en pantalla.
- Luego inicia sesión con la cuenta directiva para crear cuentas docentes y de alumnos. El correo y contraseña temporal se entregan al usuario por el colegio.
- Los perfiles anónimos y consultas anteriores se conservan; las nuevas cuentas de alumno tienen su propio perfil y progreso asociado a la cuenta.

## Alcance y pruebas

Este ZIP conserva las **14 vistas base de PMV1**, agrega las pantallas de perfil, práctica y seguimiento para PMV2/PMV3, y mantiene aparte la pantalla de demostración predictiva de S9. Las pruebas automáticas de lógica usan repositorios simulados, sin MySQL ni Ollama real. El sistema **no** puede acreditar aún HU07 sin Internet externo ni HU08 en LAN hasta realizar pruebas físicas, ni calidad pedagógica de HU04/HU-IA01/HU-IA02/HU-IA03 hasta conectar Ollama real. La PoC original de Colab de S9 sigue siendo un artefacto separado del flujo adaptativo.

Consulta el archivo `LEER_PRIMERO_WINDOWS.txt` del directorio raíz y `documentacion/` para la matriz de pruebas y las instrucciones de evidencia por CA y escenario. Las evidencias oficiales se capturarán cuando hayas terminado de validar el diseño y la funcionalidad.
