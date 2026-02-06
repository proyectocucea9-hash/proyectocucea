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
# Almacena los datos de usuarios. Solo correos @alumnos.udg.mx pueden registrarse
# (tras verificar el código enviado por correo). Contraseñas encriptadas con Werkzeug.
# =============================================================================

class Usuario(UserMixin, db.Model):
    """
    Tabla de usuarios del sistema.
    - Solo correos @alumnos.udg.mx pueden registrarse e iniciar sesión.
    - Registro con verificación: se envía código de 6 dígitos por Flask-Mail;
      la cuenta solo se crea al introducir el código correcto.
    - password_hash: contraseña encriptada (Werkzeug PBKDF2), nunca en texto plano.
    """
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    es_admin = db.Column(db.Boolean, default=False, nullable=False)

    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    votos = db.relationship('VotoPresupuesto', backref='usuario', lazy='dynamic')

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

    # Gasto (gamificación): solo se define al crear la tarjeta; no editable después.
    cantidad_gasto = db.Column(db.Float, default=0, nullable=False)

    # Contadores de likes/dislikes: se actualizan desde la tabla VotoPresupuesto
    # (un voto por usuario; pueden cambiar de like a dislike pero no duplicar).
    likes = db.Column(db.Integer, default=0, nullable=False)
    dislikes = db.Column(db.Integer, default=0, nullable=False)

    # Auditoría
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    comentarios = db.relationship('Comentario', backref='presupuesto', lazy='dynamic', order_by='Comentario.fecha_creacion')
    votos = db.relationship('VotoPresupuesto', backref='presupuesto', lazy='dynamic', foreign_keys='VotoPresupuesto.presupuesto_id')

    def __repr__(self):
        """Representación en consola para debugging."""
        return f'<Presupuesto {self.concepto}: ${self.monto}>'


# =============================================================================
# MODELO: Comentario
# Comentarios por presupuesto. Admin puede eliminar (moderación).
# =============================================================================

class Comentario(db.Model):
    __tablename__ = 'comentarios'

    id = db.Column(db.Integer, primary_key=True)
    presupuesto_id = db.Column(db.Integer, db.ForeignKey('presupuestos.id'), nullable=False)
    autor = db.Column(db.String(120), default='Anónimo')
    contenido = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# MODELO: PendingRegistro
# Registros pendientes de verificación por correo (código de 6 dígitos).
# La cuenta solo se crea en Usuario cuando el usuario introduce el código correcto.
# =============================================================================

class PendingRegistro(db.Model):
    __tablename__ = 'pending_registro'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    codigo = db.Column(db.String(6), nullable=False)  # Código de 6 dígitos enviado por correo
    creado_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# MODELO: VotoPresupuesto
# Relación usuario-presupuesto para likes/dislikes. Anti-spam: un solo voto por persona.
# El usuario puede cambiar de Like a Dislike (se actualiza la fila), pero no duplicar.
# Los contadores Presupuesto.likes y Presupuesto.dislikes se recalculan desde esta tabla.
# =============================================================================

class VotoPresupuesto(db.Model):
    __tablename__ = 'votos_presupuesto'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    presupuesto_id = db.Column(db.Integer, db.ForeignKey('presupuestos.id'), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'like' o 'dislike'
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('usuario_id', 'presupuesto_id', name='uq_usuario_presupuesto'),)


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
