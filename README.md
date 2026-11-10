# Agenda de Contactos

Proyecto escolar: aplicación web con cuentas individuales para registrar, consultar, modificar y eliminar contactos con **Python, Flask, SQLite o PostgreSQL, HTML y CSS**.

## 1. ¿Qué hace la aplicación?

Permite guardar contactos con estos campos:

- Nombre (obligatorio)
- Teléfono (obligatorio)
- Correo electrónico (opcional)
- Categoría (obligatoria)

Cada persona puede crear una cuenta e iniciar sesión. Sus contactos quedan ligados a su cuenta: otras personas no pueden verlos, editarlos ni eliminarlos. Las contraseñas se guardan como hashes y los formularios POST usan protección CSRF.

Incluye las cuatro operaciones CRUD:

| Operación | Significado | Dónde está |
|---|---|---|
| CREATE | Crear/guardar un contacto | `app.py`, función `agregar()`; `database.py`, función `agregar_contacto()` |
| READ | Consultar y mostrar contactos | `app.py`, función `inicio()`; `database.py`, función `obtener_contactos()` |
| UPDATE | Modificar un contacto | `app.py`, función `editar()`; `database.py`, función `actualizar_contacto()` |
| DELETE | Eliminar un contacto | `app.py`, función `eliminar()`; `database.py`, función `eliminar_contacto()` |

## 2. Estructura del proyecto

```text
AgendaContactos/
├── app.py                 # Aplicación Flask y rutas
├── database.py            # Conexión, cuentas y operaciones SQL
├── migrar_sqlite_a_postgres.py  # Migra contactos a una cuenta concreta
├── contactos.db           # Base de datos SQLite con los contactos
├── requirements.txt       # Dependencias de Python
├── render.yaml            # Configuración de despliegue en Render
├── README.md              # Esta guía
├── .gitignore             # Archivos que no se suben a Git
├── templates/
│   ├── base.html          # Plantilla general compartida
│   ├── iniciar_sesion.html # Formulario de acceso
│   ├── crear_cuenta.html  # Formulario de registro
│   ├── index.html         # Formulario y lista de contactos
│   └── editar.html        # Formulario para editar
└── static/
│   ├── css/
│   │   └── estilos.css    # Colores vivos, cristal líquido, iconos SVG y diseño adaptable
│   ├── js/
│   │   └── app.js         # Búsqueda, filtro, menú móvil y confirmación al borrar
│   └── img/
│       ├── fondo-redbull.png
│       └── image.png         # Logo de la barra de navegación
```

> Conserva `contactos.db` para mantener tus contactos locales. Flask usa SQLite localmente y PostgreSQL cuando se configura `DATABASE_URL`. En Render gratuito, el disco local es temporal; configura PostgreSQL antes de desplegar para no perder los contactos.

## 3. Requisitos

- Python 3 instalado.
- Visual Studio Code.
- Conexión a internet para instalar las dependencias listadas en `requirements.txt` la primera vez.

## 4. Cómo ejecutar en Windows desde VS Code

Abre la carpeta `AgendaContactos` en VS Code. En el menú **Terminal > Nuevo terminal**, ejecuta estos comandos, uno por uno:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Cuando la terminal muestre que Flask está ejecutándose, abre en tu navegador:

```text
http://127.0.0.1:5000
```

Para detener el servidor, vuelve a la terminal y presiona `Ctrl + C`.

## 5. Publicar en Render

El proyecto incluye `render.yaml` con los comandos de construcción e inicio, `gunicorn` como servidor de producción y `/health` como comprobación del servicio. Para conservar contactos y archivos al reiniciar Render, usa PostgreSQL externo; la aplicación cambia automáticamente a PostgreSQL cuando recibe `DATABASE_URL` y sigue usando SQLite para el desarrollo local.

1. El código ya está en GitHub. `contactos.db` se conserva en tu computadora y está ignorada por Git.
2. Crea un proyecto PostgreSQL en Neon. Copia la cadena **directa** para migrar una vez los datos, y guarda aparte la cadena **pooled** (su host contiene `-pooler`) para Render. No publiques ni agregues ninguna cadena a Git.
3. En Render, elige **New > Blueprint**, conecta el repositorio y confirma la configuración de `render.yaml`. Cuando Render solicite `DATABASE_URL`, pega la cadena pooled de Neon. Render genera `SECRET_KEY` automáticamente. Espera el despliegue y abre la URL.
4. Crea en el sitio la cuenta que será dueña de los contactos locales y anota exactamente su correo. Si tienes contactos locales que quieres migrar, copia esos registros a esa cuenta. En PowerShell, desde la carpeta `AgendaContactos`, define la cadena directa solo en la terminal:

   ```powershell
   $env:DATABASE_URL = "tu-cadena-de-conexion-directa-de-neon"
   .\venv\Scripts\python.exe migrar_sqlite_a_postgres.py --owner-email "tu-correo@ejemplo.com"
   ```

   El migrador conserva los IDs y se detiene si la tabla destino ya tiene contactos. Verifica que el correo ya exista en el sitio. No borra ni modifica `contactos.db`.

5. Render comprobará `/health`; una respuesta correcta es `{"estado":"ok"}`. Después, cada usuario puede crear su propia cuenta desde la página de acceso.

**Límites importantes:** el plan gratuito de Render apaga el servicio tras 15 minutos sin tráfico y su sistema de archivos es temporal. El servicio puede tardar aproximadamente un minuto en despertar. No garantiza 100 solicitudes activas simultáneas; la configuración inicial atiende hasta 8 solicitudes a la vez con Gunicorn y las demás esperan turno. Neon pooling ayuda a reutilizar conexiones de base de datos, pero no aumenta la capacidad de procesamiento del servidor Render. Para comprometerse con 100 conexiones activas simultáneas hace falta una instancia dimensionada y una prueba de carga. El PostgreSQL gratuito de Render expira a los 30 días, por eso estas instrucciones usan Neon como base persistente.

**Privacidad:** cada contacto está asociado a una cuenta y las operaciones CRUD verifican su propietario. El registro es abierto, pero cada cuenta solo ve sus propios contactos. El correo no se verifica y la recuperación por correo no está configurada; usa una contraseña única y registra solo correos que controles.

**Contactos antiguos en SQLite:** el sistema conserva los registros existentes como contactos sin propietario hasta que se asocien de forma explícita. Para asignarlos localmente, inicia la app con `CONTACTS_OWNER_EMAIL` igual al correo de la cuenta que se registrará o que iniciará sesión:

```powershell
$env:CONTACTS_OWNER_EMAIL = "tu-correo@ejemplo.com"
python app.py
```

Solo esa cuenta podrá reclamar los contactos antiguos. No habilites esta opción con un correo que no controles.

### Si PowerShell bloquea la activación

Si aparece un mensaje de que la ejecución de scripts está deshabilitada, puedes abrir una terminal **Command Prompt (CMD)** en VS Code y ejecutar:

```bat
py -m venv venv
venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

## 6. ¿Dónde está cada parte del código?

### `app.py`
Es el archivo principal. Define el registro, el inicio/cierre de sesión, la protección de las rutas y las operaciones CRUD. Verifica contraseñas con hash, crea la sesión y vincula cada acción con el ID de la cuenta autenticada.

### `database.py`
Contiene las funciones que se comunican con SQLite local o PostgreSQL configurado con `DATABASE_URL`:
- `conectar()`: abre la conexión al archivo de base de datos.
- `verificar_conexion()`: confirma que la base de datos responde al control de salud de Render.
- `crear_tabla()`: crea `usuarios` y `contactos`, y adapta la tabla antigua.
- `obtener_usuario_por_correo(...)` y `crear_usuario(...)`: buscan y crean cuentas.
- `obtener_contactos(usuario_id)`: consulta solo los contactos de esa cuenta.
- `obtener_contacto(id, usuario_id)`: busca un contacto que pertenezca a esa cuenta.
- `agregar_contacto(...)`, `actualizar_contacto(...)` y `eliminar_contacto(...)`: ejecutan CRUD ligado al propietario.

Cada contacto tiene además `usuario_id`, que identifica a su propietario; las consultas y cambios siempre verifican ese ID.

### `templates/`
Aquí se guardan los archivos HTML que Flask muestra:
- `base.html`: estructura común, encabezado, mensajes y pie.
- `iniciar_sesion.html` y `crear_cuenta.html`: pantallas de autenticación con la temática de carreras.
- `index.html`: formulario para agregar y tarjetas para consultar.
- `editar.html`: formulario que carga los datos actuales de un contacto.

### `static/`
Contiene recursos que no son plantillas:
- `css/estilos.css`: colores de competición, paneles de cristal líquido translúcido, iconos SVG, fondo global y adaptación a pantallas pequeñas.
- `js/app.js`: búsqueda en tiempo real, filtro por categorías existentes, menú adaptable y confirmación antes de eliminar.

### Imagen de fondo

El logo de la navegación se carga desde `static/img/image.png` y se presenta dentro de un avatar circular con borde luminoso. El fondo global se carga desde `static/img/fondo-redbull.png`. En computadoras se adapta con `background-size: cover`; en celulares se muestra una capa nítida ajustada al ancho para conservar la imagen completa, sobre una capa de fondo suavizada. Ambas capas incorporan sombras para facilitar la lectura.

### `migrar_sqlite_a_postgres.py`
Migra los contactos locales a una cuenta existente en PostgreSQL, preservando IDs y datos originales. Requiere `--owner-email`; se ejecuta después de desplegar y crear esa cuenta. No elimina ni cambia el archivo SQLite local.

## 7. Conceptos que debes poder explicar

- **Flask:** herramienta de Python para crear aplicaciones web.
- **SQLite/PostgreSQL:** SQLite guarda la información localmente; PostgreSQL aloja la base persistente al publicar.
- **CRUD:** las cuatro acciones básicas para administrar registros: crear, leer, actualizar y eliminar.
- **ID:** número único que identifica cada contacto; permite editar o borrar el registro correcto.
- **`commit()`:** confirma y guarda los cambios realizados en la base de datos.
- **GET:** solicita o muestra información, como abrir la página o el formulario de edición.
- **POST:** envía datos para realizar una acción, como agregar, actualizar o eliminar.
- **Consultas parametrizadas (`?` / `%s`):** separan los valores de la instrucción SQL y ayudan a evitar inyección SQL en ambos motores.

## 8. Pruebas que debes realizar

1. Abre la aplicación y registra dos contactos de prueba.
2. Comprueba que aparezcan en la tabla.
3. Usa el buscador para localizar uno.
4. Edita el correo o el teléfono de un contacto y guarda.
5. Elimina el otro contacto y confirma la acción.
6. Detén Flask con `Ctrl + C` y vuelve a iniciar con `python app.py`.
7. Comprueba que el contacto que no eliminaste siga guardado.

## 9. Dos ampliaciones incluidas

El manual propone elegir dos desafíos de ampliación. Esta base incluye:
1. **Búsqueda:** el campo de búsqueda filtra los contactos por los datos visibles en la tabla.
2. **Mejora visual:** interfaz oscura, adaptable a celular y computadora.

## 10. Preguntas para preparar tu explicación

1. ¿Qué diferencia hay entre CREATE y UPDATE?
2. ¿Por qué cada contacto tiene un ID?
3. ¿Para qué sirve `commit()`?
4. ¿Qué sucede al eliminar un contacto?
5. ¿Cuál es la diferencia entre GET y POST?
6. ¿Por qué se usan consultas parametrizadas?
7. ¿En qué archivo se define la tabla?
8. ¿En qué carpeta se encuentra el diseño?

**Consejo:** abre los archivos en VS Code y practica explicar con tus propias palabras qué hace cada función. No basta con que la aplicación funcione: debes poder ubicar cada parte del código.
