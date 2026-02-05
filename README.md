# Plataforma de Transparencia Presupuestaria - CUCEA

Web profesional donde el público puede ver en qué se invierte el dinero, y solo el personal autorizado (@academicos.mx) puede editar los datos.

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

```bash
# Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python app.py
```

Abre http://localhost:5000 en el navegador.

## Uso

- **Visitante**: Puede ver la página de inicio, "Quiénes somos", ubicación (mapa) y el listado de presupuesto. No ve botones de edición ni borrado.

- **Administrador**: Solo correos que terminen en `@academicos.mx` pueden registrarse e iniciar sesión. Tienen acceso a crear, editar y eliminar registros de presupuesto.

## Configuración

Copia `.env.example` a `.env` y ajusta:

- `SECRET_KEY`: Clave secreta para sesiones (cambiar en producción)
- `ADMIN_EMAIL_DOMAIN`: Dominio permitido para admins (por defecto @academicos.mx)
- `MAP_ADDRESS`: Dirección mostrada en el mapa

## Imagen "Quiénes somos"

Agrega una imagen en `static/img/cucea.jpg` para que se muestre en la sección "Quiénes somos". Por defecto se muestra un placeholder.
