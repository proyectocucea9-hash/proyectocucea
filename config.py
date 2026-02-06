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
    # Regla de oro: SOLO @academicos.mx puede registrarse e iniciar sesión.
    # Cualquier otro dominio (@alumnos.mx, @gmail.com, etc.) queda bloqueado.
    # Los usuarios registrados con este dominio tienen automáticamente es_admin=True.
    # -------------------------------------------------------------------------
    ADMIN_EMAIL_DOMAIN = '@academicos.mx'

    # Google Maps (opcional)
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
    MAP_LATITUDE = os.environ.get('MAP_LATITUDE', '20.7071')
    MAP_LONGITUDE = os.environ.get('MAP_LONGITUDE', '-103.3804')
    MAP_ADDRESS = os.environ.get('MAP_ADDRESS', 'CUCEA, Universidad de Guadalajara')
