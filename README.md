# Plataforma de Transparencia Presupuestaria - CUCEA

Web profesional donde el público puede ver en qué se invierte el dinero. Solo correos @alumnos.udg.mx pueden registrarse (con verificación por correo) y editar los datos.

## Tecnologías

- **Backend**: Python, Flask
- **Base de datos**: SQLite (ligera, sin servidor externo)
- **Frontend**: HTML, CSS, JavaScript
- **ORM**: SQLAlchemy
- **Autenticación**: Flask-Login

## Estructura del proyecto

```
proyectocucea/
├── app.py              # Aplicación principal Flask
├── config.py           # Configuración
├── models.py           # Modelos Usuario y Presupuesto
├── extensions.py       # Flask-SQLAlchemy, Flask-Login
├── requirements.txt
├── templates/
│   ├── base/
│   │   └── layout.html # Plantilla maestra (Navbar, Sidebar, Footer)
│   ├── index.html      # Página de inicio
│   ├── auth/
│   │   ├── login.html
│   │   └── registro.html
│   └── presupuesto/
│       ├── lista.html
│       └── formulario.html
├── static/
│   ├── css/main.css
│   └── js/main.js
└── instance/           # Base de datos SQLite (se crea al ejecutar)
```

## Instalación

### Opción 1: Con Docker (mismo entorno para todo el equipo)

```bash
# Copiar credenciales (obligatorio para que se envíe el código de verificación por correo)
cp .env.example .env
# Editar .env y rellenar MAIL_USERNAME, MAIL_PASSWORD, MAIL_SERVER, etc.

# Construir y levantar la aplicación
docker-compose up --build

# Abrir http://localhost:5000
```

La base de datos SQLite se persiste en `./instance`. Para parar: `docker-compose down`.

### Opción 2: Sin Docker

```bash
# Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Copiar .env.example a .env y configurar (sobre todo SMTP para el código de verificación)
# Ejecutar
python app.py
```

Abre http://localhost:5000 en el navegador.

## Uso

- **Visitante**: Puede ver la página de inicio, "Quiénes somos", ubicación (mapa) y el listado de presupuesto. No ve botones de edición ni borrado.

- **Administrador**: Solo correos `@alumnos.udg.mx` pueden registrarse (tras verificar el código enviado por correo) e iniciar sesión. Tienen acceso a crear, editar y eliminar registros de presupuesto.

## Configuración

Copia `.env.example` a `.env` y ajusta:

- `SECRET_KEY`: Clave secreta para sesiones (cambiar en producción)
- **SMTP (obligatorio para que se envíe el código de verificación)**: `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`. Con Gmail, usar "Contraseña de aplicación".
- `MAP_ADDRESS`: Dirección mostrada en el mapa

Si el correo no se envía, en la terminal donde corre la app aparecerá el error de Flask-Mail (revisar credenciales y puerto).

## Imagen "Quiénes somos"

Agrega una imagen en `static/img/cucea.jpg` para que se muestre en la sección "Quiénes somos". Por defecto se muestra un placeholder.
