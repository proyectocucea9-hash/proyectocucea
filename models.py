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
    - Cualquier otro dominio (@alumnos.mx, etc.) está bloqueado en login y registro.
    - Los usuarios registrados con @academicos.mx tienen es_admin=True automáticamente.
    """
    __tablename__ = 'usuarios'

    # Clave primaria e identificación
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    # Permisos: True si el usuario es administrador (solo correos @academicos.mx)
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
# Representa cada proyecto o ítem presupuestario con imagen, fecha, descripción y reacciones.
# =============================================================================

class Presupuesto(db.Model):
    """
    Tabla de proyectos/ítems presupuestarios.
    - imagen_url: Ruta o URL de la imagen (para cards y modal).
    - concepto: Título del proyecto.
    - descripcion_corta: Texto breve para la tarjeta (card) en carrusel y grid.
    - descripcion: Descripción larga para el modal detallado.
    - likes / dislikes: Contadores de reacciones (públicos, sin restricción por usuario).
    """
    __tablename__ = 'presupuestos'

    # Clave primaria
    id = db.Column(db.Integer, primary_key=True)

    # Contenido del proyecto
    concepto = db.Column(db.String(200), nullable=False)  # Título del proyecto
    descripcion_corta = db.Column(db.String(300))  # Resumen breve para la card (si vacío se trunca descripcion)
    descripcion = db.Column(db.Text)  # Descripción larga para el modal
    imagen_url = db.Column(db.String(500))  # Ruta o URL de imagen (ej: img/proyecto1.jpg)

    # Datos presupuestarios
    monto = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.Date, nullable=False)  # Fecha del proyecto

    # Reacciones (públicas: cualquier visitante puede sumar like/dislike)
    likes = db.Column(db.Integer, default=0, nullable=False)
    dislikes = db.Column(db.Integer, default=0, nullable=False)

    # Auditoría
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación con comentarios (estilo Facebook): un presupuesto tiene muchos comentarios
    comentarios = db.relationship('Comentario', backref='presupuesto', lazy='dynamic', order_by='Comentario.fecha_creacion')

    def __repr__(self):
        """Representación en consola para debugging."""
        return f'<Presupuesto {self.concepto}: ${self.monto}>'


# =============================================================================
# MODELO: Comentario
# Comentarios por presupuesto (estilo Facebook): autor + contenido + fecha.
# =============================================================================

class Comentario(db.Model):
    """
    Comentarios asociados a un presupuesto.
    Se muestran en el modal detallado; cualquier visitante puede escribir (autor opcional).
    """
    __tablename__ = 'comentarios'

    id = db.Column(db.Integer, primary_key=True)
    presupuesto_id = db.Column(db.Integer, db.ForeignKey('presupuestos.id'), nullable=False)
    autor = db.Column(db.String(120), default='Anónimo')  # Nombre o "Anónimo"
    contenido = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# MODELO: CarruselSlide (Edición in-place - Franja 1)
# Imágenes del carrusel de la página de inicio; el admin puede Editar/Subir.
# =============================================================================

class CarruselSlide(db.Model):
    """
    Cada slide del carrusel de la franja de presentación (index).
    orden: posición en el carrusel (0, 1, 2...).
    imagen_url: URL o ruta de la imagen.
    """
    __tablename__ = 'carrusel_slides'

    id = db.Column(db.Integer, primary_key=True)
    orden = db.Column(db.Integer, default=0, nullable=False)
    imagen_url = db.Column(db.String(500), nullable=False)
    titulo_alt = db.Column(db.String(200))  # Texto alternativo para accesibilidad


# =============================================================================
# MODELO: ContenidoSite (Edición in-place - Textos de descripción)
# Textos editables de la página de inicio (título, párrafos).
# =============================================================================

class ContenidoSite(db.Model):
    """
    Contenido editable por clave (key-value).
    Claves ejemplo: index_franja1_titulo, index_franja1_parrafo1, index_franja1_parrafo2.
    Si no existe la clave, la plantilla usa texto por defecto.
    """
    __tablename__ = 'contenido_site'

    clave = db.Column(db.String(80), primary_key=True)
    valor = db.Column(db.Text, nullable=False)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
