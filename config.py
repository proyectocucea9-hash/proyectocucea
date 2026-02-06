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

    # Ruta de la base de datos SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR / "instance" / "transparencia.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -------------------------------------------------------------------------
    # Dominio obligatorio: SOLO @alumnos.udg.mx puede registrarse e iniciar sesión.
    # Cualquier otro dominio queda bloqueado.
    # -------------------------------------------------------------------------
    ADMIN_EMAIL_DOMAIN = '@alumnos.udg.mx'

    # -------------------------------------------------------------------------
    # Flask-Mail: envío del código de verificación de 6 dígitos al registrarse.
    # El usuario debe introducir el código correcto para crear la cuenta.
    # En producción usar variables de entorno (MAIL_USERNAME, MAIL_PASSWORD).
    # -------------------------------------------------------------------------
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@cucea.udg.mx')
    # Tiempo de validez del código de verificación (minutos)
    VERIFICATION_CODE_EXPIRY_MINUTES = 15

    # Google Maps (opcional)
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    MAP_LATITUDE = os.environ.get('MAP_LATITUDE', '20.7071')
    MAP_LONGITUDE = os.environ.get('MAP_LONGITUDE', '-103.3804')
    MAP_ADDRESS = os.environ.get('MAP_ADDRESS', 'CUCEA, Universidad de Guadalajara')
