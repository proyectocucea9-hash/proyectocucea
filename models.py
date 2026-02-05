"""
Modelos de base de datos para la plataforma de transparencia presupuestaria.
Cada modelo representa una tabla en SQLite mediante SQLAlchemy ORM.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


# =============================================================================
# MODELO: Usuario
# Almacena los datos de usuarios. Solo correos @academicos.mx pueden ser admins.
# =============================================================================

class Usuario(UserMixin, db.Model):
    """
    Tabla de usuarios del sistema.
    - Solo correos que terminen en @academicos.mx pueden registrarse e iniciar sesión.
    - Los usuarios con es_admin=True tienen permisos para agregar/editar presupuestos.
    """
    __tablename__ = 'usuarios'

    # Clave primaria e identificación
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    # Permisos: True si el usuario es administrador (solo @academicos.mx)
    es_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Auditoría
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """
        Hashea la contraseña en texto plano y la guarda en password_hash.
        Usa Werkzeug para un hash seguro (PBKDF2 por defecto).
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Verifica si la contraseña proporcionada coincide con el hash almacenado.
        Retorna True si es correcta, False en caso contrario.
        """
        return check_password_hash(self.password_hash, password)

    @property
    def es_administrador(self):
        """
        Propiedad que indica si el usuario tiene permisos de administrador.
        Usada en plantillas para mostrar/ocultar botones de edición.
        """
        return self.es_admin


# =============================================================================
# MODELO: Presupuesto (Proyecto)
# Representa cada proyecto o ítem presupuestario con imagen, fecha y descripción.
# =============================================================================

class Presupuesto(db.Model):
    """
    Tabla de proyectos/ítems presupuestarios.
    Cada registro muestra un proyecto con su imagen, monto, categoría y descripción.
    - imagen_url: Ruta o URL de la imagen del proyecto (para cards)
    - concepto: Título del proyecto
    - descripcion: Resumen breve del proyecto
    """
    __tablename__ = 'presupuestos'

    # Clave primaria
    id = db.Column(db.Integer, primary_key=True)

    # Contenido del proyecto
    concepto = db.Column(db.String(200), nullable=False)  # Título del proyecto
    descripcion = db.Column(db.Text)  # Resumen breve
    imagen_url = db.Column(db.String(500))  # Ruta o URL de imagen (ej: img/proyecto1.jpg)

    # Datos presupuestarios
    monto = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.Date, nullable=False)  # Fecha de creación del proyecto

    # Auditoría
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        """Representación en consola para debugging."""
        return f'<Presupuesto {self.concepto}: ${self.monto}>'
