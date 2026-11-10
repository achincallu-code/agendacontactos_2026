# Agenda de Contactos

Proyecto escolar: aplicación web para registrar, consultar, modificar y eliminar contactos con **Python, Flask, SQLite o PostgreSQL, HTML y CSS**.

## 1. ¿Qué hace la aplicación?

Permite guardar contactos con estos campos:

- Nombre (obligatorio)
- Teléfono (obligatorio)
- Correo electrónico (opcional)
- Categoría (obligatoria)

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
├── database.py            # Conexión SQLite/PostgreSQL y operaciones SQL
├── migrar_sqlite_a_postgres.py  # Conserva los contactos al cambiar a PostgreSQL
├── contactos.db           # Base de datos SQLite con los contactos
├── requirements.txt       # Dependencias de Python
├── render.yaml            # Configuración de despliegue en Render
├── README.md              # Esta guía
├── .gitignore             # Archivos que no se suben a Git
├── templates/
│   ├── base.html          # Plantilla general compartida
│   ├── index.html         # Formulario y lista de contactos
│   └── editar.html        # Formulario para editar
└── static/
│   ├── css/
│   │   └── estilos.css    # Colores vivos, cristal líquido, iconos SVG y diseño adaptable
│   ├── js/
│   │   └── app.js         # Búsqueda, filtro, menú móvil y confirmación al borrar
│   └── img/
│       ├── fondo-redbull.png
│       ├── image.png         # Logo de la barra de navegación
│       └── findo_f1.jpeg     # Imagen original conservada
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

1. Sube la carpeta `AgendaContactos` a un repositorio privado en GitHub. `contactos.db` se conserva en tu computadora y está ignorada por Git.
2. Crea un proyecto PostgreSQL en Neon. Copia la cadena **directa** para migrar una vez los datos, y guarda aparte la cadena **pooled** (su host contiene `-pooler`) para Render. No publiques ni agregues ninguna cadena a Git.
3. Antes del primer despliegue, copia los contactos locales a la base PostgreSQL vacía. En PowerShell, desde la carpeta `AgendaContactos`, define la cadena directa solo en la terminal:

   ```powershell
   $env:DATABASE_URL = "tu-cadena-de-conexion-directa-de-neon"
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   .\venv\Scripts\python.exe migrar_sqlite_a_postgres.py
   ```

   El migrador conserva los IDs y se detiene si la tabla destino ya tiene datos. No borra ni modifica `contactos.db`.

4. En Render, elige **New > Blueprint**, conecta tu repositorio y confirma la configuración de `render.yaml`. Cuando Render solicite `DATABASE_URL`, pega la cadena pooled de Neon. Render genera `SECRET_KEY` automáticamente.
5. Espera el despliegue y abre la URL `.onrender.com`. Render comprobará `/health`; una respuesta correcta es `{"estado":"ok"}`.

**Límites importantes:** el plan gratuito de Render apaga el servicio tras 15 minutos sin tráfico y su sistema de archivos es temporal. El servicio puede tardar aproximadamente un minuto en despertar. No garantiza 100 solicitudes activas simultáneas; la configuración inicial atiende hasta 8 solicitudes a la vez con Gunicorn y las demás esperan turno. Neon pooling ayuda a reutilizar conexiones de base de datos, pero no aumenta la capacidad de procesamiento del servidor Render. Para comprometerse con 100 conexiones activas simultáneas hace falta una instancia dimensionada y una prueba de carga. El PostgreSQL gratuito de Render expira a los 30 días, por eso estas instrucciones usan Neon como base persistente.

**Privacidad:** esta aplicación todavía no tiene cuentas ni inicio de sesión; todas las personas que visiten la URL verán y podrán modificar o borrar los mismos contactos. No guardes contactos privados o sensibles en la versión publicada.

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
Es el archivo principal. Crea la aplicación Flask y define las direcciones (rutas) que atienden las acciones del navegador. Recibe los datos de los formularios, revisa los campos obligatorios, llama a las funciones de `database.py` y redirige al inicio.

### `database.py`
Contiene las funciones que se comunican con SQLite local o PostgreSQL configurado con `DATABASE_URL`:
- `conectar()`: abre la conexión al archivo de base de datos.
- `verificar_conexion()`: confirma que la base de datos responde al control de salud de Render.
- `crear_tabla()`: crea la tabla `contactos` si no existe.
- `obtener_contactos()`: consulta todos los registros.
- `obtener_contacto(id)`: busca un registro por su identificador.
- `agregar_contacto(...)`: inserta un registro.
- `actualizar_contacto(...)`: modifica un registro.
- `eliminar_contacto(id)`: borra un registro.

La tabla tiene las columnas `id`, `nombre`, `telefono`, `correo` y `categoria`. El `id` es la clave primaria y se genera automáticamente.

### `templates/`
Aquí se guardan los archivos HTML que Flask muestra:
- `base.html`: estructura común, encabezado, mensajes y pie.
- `index.html`: formulario para agregar y tarjetas para consultar.
- `editar.html`: formulario que carga los datos actuales de un contacto.

### `static/`
Contiene recursos que no son plantillas:
- `css/estilos.css`: colores de competición, paneles de cristal líquido translúcido, iconos SVG, fondo global y adaptación a pantallas pequeñas.
- `js/app.js`: búsqueda en tiempo real, filtro por categorías existentes, menú adaptable y confirmación antes de eliminar.

### Imagen de fondo

El logo de la navegación se carga desde `static/img/image.png` y se presenta dentro de un avatar circular con borde luminoso. El fondo global se carga desde `static/img/fondo-redbull.png`. Se creó a partir de la imagen `static/img/findo_f1.jpeg`, que se conserva intacta. En computadoras se adapta con `background-size: cover`; en celulares se muestra una capa nítida ajustada al ancho para conservar la imagen completa, sobre una capa de fondo suavizada. Ambas capas incorporan sombras para facilitar la lectura.

### `migrar_sqlite_a_postgres.py`
Migra los contactos locales a una base PostgreSQL vacía, preservando IDs y datos originales. La migración se ejecuta manualmente antes de publicar; no elimina ni cambia el archivo SQLite local.

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
