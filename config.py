"""
=============================================================================
CONFIGURACIÓN DE LA APLICACIÓN
Variables de entorno y configuración base para la plataforma de transparencia
=============================================================================
"""
import os
from pathlib import Path

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """
    Configuración base de la aplicación Flask.
    Lee variables de entorno o usa valores por defecto.
    """
    # Clave secreta para sesiones y CSRF (cambiar en producción)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clave-secreta-cambiar-en-produccion')

    # Base de datos local SQLite (sin XAMPP/MySQL). Se crea automáticamente si no existe (db.create_all).
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR / "instance" / "escuela.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -------------------------------------------------------------------------
    # Dominios permitidos: @alumnos.udg.mx y @academicos.udg.mx.
    # Cualquier otro dominio queda bloqueado.
    # -------------------------------------------------------------------------
    DOMINIOS_PERMITIDOS = ('alumnos.udg.mx', 'academicos.udg.mx')

    # -------------------------------------------------------------------------
    # SMTP (Flask-Mail) - Envío real del código de 6 dígitos.
    # Configuración técnica: smtp.gmail.com, puerto 587, TLS = True.
    # Credenciales desde .env vía python-dotenv: MAIL_USERNAME y MAIL_PASSWORD.
    # Si el envío falla, app.py imprime el error en terminal (try/except).
    # -------------------------------------------------------------------------
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('true', '1', 'yes')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '').strip()
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '').strip()
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@cucea.udg.mx')
    VERIFICATION_CODE_EXPIRY_MINUTES = 15

    # Google Maps (opcional)
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    MAP_LATITUDE = os.environ.get('MAP_LATITUDE', '20.7071')
    MAP_LONGITUDE = os.environ.get('MAP_LONGITUDE', '-103.3804')
    MAP_ADDRESS = os.environ.get('MAP_ADDRESS', 'CUCEA, Universidad de Guadalajara')
