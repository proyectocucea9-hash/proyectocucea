"""
=============================================================================
PLATAFORMA DE TRANSPARENCIA PRESUPUESTARIA - CUCEA
Aplicación principal Flask - Plataforma escolar de transparencia informativa
=============================================================================

Este módulo define la aplicación web, rutas, autenticación y lógica de negocio.
- Solo correos @academicos.mx pueden registrarse e iniciar sesión como admin.
- Visitantes: solo lectura. Administradores: pueden agregar y editar proyectos.
"""

from datetime import datetime, date
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect

from config import Config
from extensions import db, login_manager
from models import Usuario, Presupuesto


# =============================================================================
# CONFIGURACIÓN - Categorías predefinidas para proyectos presupuestarios
# =============================================================================
CATEGORIAS = [
    'Infraestructura',
    'Equipamiento',
    'Servicios',
    'Material didáctico',
    'Mantenimiento',
    'Capacitación',
    'Otros',
]


def create_app(config_class=Config):
    """
    Factory de la aplicación Flask.
    Crea y configura la instancia de la aplicación, extensiones y rutas.
    Retorna la aplicación configurada.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # -------------------------------------------------------------------------
    # Inicializar extensiones: SQLAlchemy, Flask-Login, CSRF
    # -------------------------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    CSRFProtect(app)

    # -------------------------------------------------------------------------
    # Flask-Login: Callback para cargar usuario desde la base de datos
    # Se ejecuta cuando se accede a current_user
    # -------------------------------------------------------------------------
    @login_manager.user_loader
    def load_user(id):
        """Retorna el Usuario con el id dado, o None si no existe."""
        return Usuario.query.get(int(id))

    # Configuración de Flask-Login
    login_manager.login_view = 'auth_login'
    login_manager.login_message = 'Inicia sesión para acceder a esta sección.'
    login_manager.login_message_category = 'info'

    # -------------------------------------------------------------------------
    # Context processor: Variables disponibles en todas las plantillas
    # current_year: año actual para el footer
    # map_address: dirección mostrada en el mapa (si se usa)
    # -------------------------------------------------------------------------
    @app.context_processor
    def inject_globals():
        return {
            'current_year': datetime.now().year,
            'map_address': app.config.get('MAP_ADDRESS', 'CUCEA, Universidad de Guadalajara'),
        }

    # =========================================================================
    # RUTAS PÚBLICAS - Accesibles sin autenticación
    # =========================================================================

    @app.route('/')
    def index():
        """
        Página de inicio.
        4 franjas: Presentación (2 cols), Ubicación (mapa), Carrusel de cards, Footer.
        """
        presupuestos = Presupuesto.query.order_by(Presupuesto.fecha.desc()).limit(12).all()
        return render_template('index.html', presupuestos=presupuestos)

    @app.route('/presupuestos')
    def presupuestos_lista():
        """
        Lista de proyectos presupuestarios en cuadrícula de cards.
        Soporta filtros por categoría y año.
        Visitantes: solo lectura. Administradores: ven botón Agregar.
        """
        query = Presupuesto.query
        categoria = request.args.get('categoria')
        anio = request.args.get('anio')

        if categoria:
            query = query.filter(Presupuesto.categoria == categoria)
        if anio:
            try:
                anio_int = int(anio)
                query = query.filter(
                    Presupuesto.fecha >= date(anio_int, 1, 1),
                    Presupuesto.fecha <= date(anio_int, 12, 31)
                )
            except ValueError:
                pass

        presupuestos = query.order_by(Presupuesto.fecha.desc()).all()
        return render_template(
            'presupuestos.html',
            presupuestos=presupuestos,
            categorias=CATEGORIAS,
        )

    @app.route('/presupuesto/<int:id>')
    def presupuesto_detalle(id):
        """
        Página de detalle de un proyecto.
        Muestra imagen, título, resumen, monto y categoría.
        Administradores ven botones Editar y Eliminar.
        """
        presupuesto = Presupuesto.query.get_or_404(id)
        return render_template('presupuesto/detalle.html', presupuesto=presupuesto)

    # =========================================================================
    # RUTAS DE AUTENTICACIÓN - Login y registro restringidos a @academicos.mx
    # =========================================================================

    @app.route('/auth/login', methods=['GET', 'POST'])
    def auth_login():
        """
        Inicio de sesión.
        POST: Valida credenciales. Solo correos que terminen en ADMIN_EMAIL_DOMAIN
        pueden iniciar sesión.
        """
        if current_user.is_authenticated:
            return redirect(url_for('presupuestos_lista'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            dominio = app.config['ADMIN_EMAIL_DOMAIN']

            # Validación estricta: solo @academicos.mx
            if not email.endswith(dominio):
                flash(f'Solo correos institucionales ({dominio}) pueden iniciar sesión.', 'error')
                return render_template('auth/login.html')

            usuario = Usuario.query.filter_by(email=email).first()
            if usuario and usuario.check_password(password):
                login_user(usuario)
                flash(f'Bienvenido, {usuario.nombre}.', 'success')
                next_page = request.args.get('next', url_for('presupuestos_lista'))
                return redirect(next_page)

            flash('Correo o contraseña incorrectos.', 'error')

        return render_template('auth/login.html')

    @app.route('/auth/registro', methods=['GET', 'POST'])
    def auth_registro():
        """
        Registro de administradores.
        Solo correos que terminen en ADMIN_EMAIL_DOMAIN pueden registrarse.
        Al registrarse, es_admin=True automáticamente.
        """
        if current_user.is_authenticated:
            return redirect(url_for('presupuestos_lista'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            nombre = request.form.get('nombre', '').strip()
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')
            dominio = app.config['ADMIN_EMAIL_DOMAIN']

            if not email.endswith(dominio):
                flash(f'El registro está restringido. Solo correos {dominio} pueden registrarse.', 'error')
                return render_template('auth/registro.html')
            if password != password_confirm:
                flash('Las contraseñas no coinciden.', 'error')
                return render_template('auth/registro.html')
            if len(password) < 8:
                flash('La contraseña debe tener al menos 8 caracteres.', 'error')
                return render_template('auth/registro.html')
            if Usuario.query.filter_by(email=email).first():
                flash('Ya existe una cuenta con ese correo.', 'error')
                return render_template('auth/registro.html')

            usuario = Usuario(email=email, nombre=nombre, es_admin=True)
            usuario.set_password(password)
            db.session.add(usuario)
            db.session.commit()
            flash('Cuenta creada correctamente. Inicia sesión.', 'success')
            return redirect(url_for('auth_login'))

        return render_template('auth/registro.html')

    @app.route('/auth/logout')
    @login_required
    def auth_logout():
        """Cierra la sesión del usuario y redirige al inicio."""
        logout_user()
        flash('Sesión cerrada.', 'info')
        return redirect(url_for('index'))

    # =========================================================================
    # RUTAS DE ADMINISTRACIÓN - Solo usuarios con es_admin=True
    # =========================================================================

    @app.route('/presupuesto/nuevo', methods=['GET', 'POST'])
    @login_required
    def presupuesto_nuevo():
        """
        Crear nuevo proyecto presupuestario.
        Requiere autenticación y es_administrador=True.
        """
        if not current_user.es_administrador:
            abort(403)

        if request.method == 'POST':
            concepto = request.form.get('concepto', '').strip()
            monto = request.form.get('monto')
            categoria = request.form.get('categoria', '').strip()
            fecha_str = request.form.get('fecha')
            descripcion = request.form.get('descripcion', '').strip()
            imagen_url = request.form.get('imagen_url', '').strip() or None

            if not concepto or not monto or not categoria or not fecha_str:
                flash('Completa todos los campos obligatorios.', 'error')
                return render_template('presupuesto/formulario.html', presupuesto=None, categorias=CATEGORIAS)

            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                monto_val = float(monto)
            except (ValueError, TypeError):
                flash('Datos inválidos.', 'error')
                return render_template('presupuesto/formulario.html', presupuesto=None, categorias=CATEGORIAS)

            p = Presupuesto(
                concepto=concepto,
                monto=monto_val,
                categoria=categoria,
                fecha=fecha,
                descripcion=descripcion or None,
                imagen_url=imagen_url,
            )
            db.session.add(p)
            db.session.commit()
            flash('Proyecto guardado correctamente.', 'success')
            return redirect(url_for('presupuestos_lista'))

        return render_template('presupuesto/formulario.html', presupuesto=None, categorias=CATEGORIAS)

    @app.route('/presupuesto/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def presupuesto_editar(id):
        """
        Editar proyecto existente.
        Requiere autenticación y es_administrador=True.
        """
        if not current_user.es_administrador:
            abort(403)

        presupuesto = Presupuesto.query.get_or_404(id)

        if request.method == 'POST':
            presupuesto.concepto = request.form.get('concepto', '').strip()
            presupuesto.categoria = request.form.get('categoria', '').strip()
            presupuesto.descripcion = request.form.get('descripcion', '').strip() or None
            presupuesto.imagen_url = request.form.get('imagen_url', '').strip() or None
            try:
                presupuesto.monto = float(request.form.get('monto', 0))
                presupuesto.fecha = datetime.strptime(request.form.get('fecha', ''), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                flash('Datos inválidos.', 'error')
                return render_template('presupuesto/formulario.html', presupuesto=presupuesto, categorias=CATEGORIAS)
            db.session.commit()
            flash('Proyecto actualizado.', 'success')
            return redirect(url_for('presupuesto_detalle', id=presupuesto.id))

        return render_template('presupuesto/formulario.html', presupuesto=presupuesto, categorias=CATEGORIAS)

    @app.route('/presupuesto/eliminar/<int:id>', methods=['POST'])
    @login_required
    def presupuesto_eliminar(id):
        """
        Eliminar proyecto.
        Requiere autenticación y es_administrador=True.
        """
        if not current_user.es_administrador:
            abort(403)

        presupuesto = Presupuesto.query.get_or_404(id)
        db.session.delete(presupuesto)
        db.session.commit()
        flash('Proyecto eliminado.', 'info')
        return redirect(url_for('presupuestos_lista'))

    # -------------------------------------------------------------------------
    # Crear tablas y migrar imagen_url si no existe (para bases de datos antiguas)
    # -------------------------------------------------------------------------
    with app.app_context():
        import os
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()

        # Migración: agregar columna imagen_url si no existe (para BD creadas antes)
        try:
            from sqlalchemy import text
            result = db.session.execute(text("PRAGMA table_info(presupuestos)"))
            columns = [row[1] for row in result.fetchall()]
            if columns and 'imagen_url' not in columns:
                db.session.execute(text("ALTER TABLE presupuestos ADD COLUMN imagen_url VARCHAR(500)"))
                db.session.commit()
        except Exception:
            db.session.rollback()

    return app


# =============================================================================
# Punto de entrada - Ejecutar con: python app.py
# =============================================================================
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
