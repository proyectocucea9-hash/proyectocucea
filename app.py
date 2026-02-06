"""
=============================================================================
PLATAFORMA DE TRANSPARENCIA PRESUPUESTARIA - CUCEA
Aplicación principal Flask - Seguridad, verificación por correo, likes por usuario.
=============================================================================

Seguridad y verificación:
- Dominio obligatorio: SOLO @alumnos.udg.mx puede registrarse e iniciar sesión.
- Al registrarse se envía un código de 6 dígitos por Flask-Mail; la cuenta solo
  se crea en la BD cuando el usuario introduce el código correcto (tabla PendingRegistro).

Likes anti-spam: tabla VotoPresupuesto vincula usuario_id y presupuesto_id; un voto
por persona (pueden cambiar de Like a Dislike, no duplicar). Contadores en Presupuesto
se actualizan desde esa tabla.

Gamificación: cantidad_gasto por presupuesto (solo al crear); Total Invertido en Navbar.
"""

from datetime import datetime, date, timedelta
from pathlib import Path
import os
import random
import string
import threading

from dotenv import load_dotenv

# Cargar .env; si no existe, crearlo con placeholders para credenciales SMTP
_env_path = Path(__file__).resolve().parent / '.env'
if not _env_path.exists():
    _env_path.write_text(
        '# Credenciales SMTP (obligatorias para enviar el código de verificación)\n'
        'MAIL_USERNAME=\n'
        'MAIL_PASSWORD=\n'
        'MAIL_SERVER=smtp.gmail.com\n'
        'MAIL_PORT=587\n'
        'MAIL_USE_TLS=true\n'
        'MAIL_DEFAULT_SENDER=noreply@cucea.udg.mx\n'
        'SECRET_KEY=clave-secreta-cambiar-en-produccion\n',
        encoding='utf-8'
    )
load_dotenv(_env_path)

from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from sqlalchemy import func

from config import Config
from extensions import db, login_manager
from models import Usuario, Presupuesto, Comentario, CarruselSlide, ContenidoSite, PendingRegistro, VotoPresupuesto


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
    # Flask-Mail: configuración hardcoded para Gmail (cambiar TU_CORREO y TU_CLAVE).
    # En Docker, las variables de entorno sobrescriben si se pasan en .env.
    # -------------------------------------------------------------------------
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') or 'TU_CORREO@gmail.com'  # Yo lo cambiaré
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD') or 'TU_CLAVE_16_DIGITOS'   # Yo lo cambiaré
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') or app.config['MAIL_USERNAME']
    mail = Mail(app)

    # -------------------------------------------------------------------------
    # Inicializar extensiones: SQLAlchemy, Flask-Login, CSRF (Mail ya creado arriba)
    # -------------------------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    CSRFProtect(app)

    # -------------------------------------------------------------------------
    # Flask-Login: Callback para cargar usuario desde la base de datos.
    # Se ejecuta tras el login (la sesión guarda el id del usuario) y al acceder a current_user.
    # Corrección: el id puede llegar como string desde la sesión JSON; convertimos a int de forma
    # segura para evitar que falle el login tras crear la cuenta.
    # -------------------------------------------------------------------------
    @login_manager.user_loader
    def load_user(id):
        """Retorna el Usuario con el id dado, o None si no existe o el id es inválido."""
        if id is None:
            return None
        try:
            return Usuario.query.get(int(id))
        except (TypeError, ValueError):
            return None

    # Configuración de Flask-Login
    login_manager.login_view = 'auth_login'
    login_manager.login_message = 'Inicia sesión para acceder a esta sección.'
    login_manager.login_message_category = 'info'

    # -------------------------------------------------------------------------
    # Ciberseguridad: solo correos @alumnos.udg.mx pueden acceder a rutas de Admin.
    # Uso: @admin_required bajo @login_required. Si el dominio no es alumnos.udg.mx -> 403.
    # -------------------------------------------------------------------------
    def admin_required(f):
        from functools import wraps
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth_login'))
            email = getattr(current_user, 'email', '') or ''
            if not email or email.split('@')[-1].lower() != 'alumnos.udg.mx':
                abort(403)
            return f(*args, **kwargs)
        return decorated

    # -------------------------------------------------------------------------
    # Context processor: total_invertido = suma real de cantidad_gasto (SQLAlchemy func.sum).
    # Se muestra en la Navbar como "Total de Gastos" a la derecha con icono de dinero.
    # -------------------------------------------------------------------------
    @app.context_processor
    def inject_globals():
        total = db.session.query(func.coalesce(func.sum(Presupuesto.cantidad_gasto), 0)).scalar()
        total_invertido = float(total) if total is not None else 0.0
        return {
            'current_year': datetime.now().year,
            'map_address': app.config.get('MAP_ADDRESS', 'CUCEA, Universidad de Guadalajara'),
            'total_invertido': total_invertido,
        }

    # =========================================================================
    # RUTAS PÚBLICAS - Accesibles sin autenticación
    # =========================================================================

    @app.route('/')
    def index():
        """
        Página de inicio.
        Franjas: Presentación (textos + carrusel de imágenes editables), Ubicación,
        Carrusel de 3 cards de presupuestos (centro resaltado), Footer.
        Pasa slides del carrusel y textos desde BD para edición in-place por Admin.
        """
        # Carrusel de imágenes (franja 1): desde BD o URLs por defecto
        slides = CarruselSlide.query.order_by(CarruselSlide.orden).all()
        if not slides:
            slides = [
                {'orden': 0, 'imagen_url': 'https://images.unsplash.com/photo-1562774053-701939374585?w=800&h=500&fit=crop', 'titulo_alt': 'Campus'},
                {'orden': 1, 'imagen_url': 'https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=800&h=500&fit=crop', 'titulo_alt': 'Estudiantes'},
                {'orden': 2, 'imagen_url': 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&h=500&fit=crop', 'titulo_alt': 'Biblioteca'},
            ]
        else:
            slides = [{'orden': s.orden, 'imagen_url': s.imagen_url, 'titulo_alt': s.titulo_alt or ''} for s in slides]

        # Textos editables de la franja 1 (clave-valor)
        def get_content(key, default):
            c = ContenidoSite.query.get(key)
            return c.valor if c else default

        contenido_franja1 = {
            'titulo': get_content('index_franja1_titulo', 'Transparencia Presupuestaria'),
            'subtitulo': get_content('index_franja1_subtitulo', 'Centro Universitario de Ciencias Económico Administrativas'),
            'parrafo1': get_content('index_franja1_parrafo1', 'El CUCEA es una de las divisiones más importantes de la Universidad de Guadalajara, dedicada a la formación de profesionales en áreas económicas y administrativas.'),
            'parrafo2': get_content('index_franja1_parrafo2', 'En cumplimiento con los principios de transparencia y rendición de cuentas, ponemos a disposición del público esta plataforma donde puedes consultar de manera clara y accesible cómo se invierten los recursos de nuestra institución.'),
        }
        # Imagen de fondo editable por Admin (clave index_fondo_url)
        fondo_url = get_content('index_fondo_url', 'https://images.unsplash.com/photo-1562774053-701939374585?w=1920&h=1080&fit=crop')

        # Presupuestos ordenados de mayor a menor número de likes (gamificación)
        presupuestos = Presupuesto.query.order_by(Presupuesto.likes.desc(), Presupuesto.fecha.desc()).limit(12).all()
        return render_template(
            'index.html',
            presupuestos=presupuestos,
            carousel_slides=slides,
            contenido_franja1=contenido_franja1,
            fondo_url=fondo_url,
        )

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

        # Orden dinámico: mayor a menor número de likes (respeta filtros por categoría/año)
        presupuestos = query.order_by(Presupuesto.likes.desc(), Presupuesto.fecha.desc()).all()
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

    # -------------------------------------------------------------------------
    # API para el modal de detalle (Index): datos JSON, like, dislike, comentarios
    # El modal bloquea el scroll del fondo y tiene scroll interno.
    # -------------------------------------------------------------------------

    def _recalcular_likes_dislikes(presupuesto):
        """
        Actualiza presupuesto.likes y presupuesto.dislikes desde la tabla VotoPresupuesto.
        Relación en BD: VotoPresupuesto tiene (usuario_id, presupuesto_id, tipo) con
        UNIQUE(usuario_id, presupuesto_id). Así cada persona solo puede tener un voto
        por presupuesto (like o dislike); puede cambiar de uno al otro pero no duplicar.
        Los contadores en Presupuesto se mantienen sincronizados para ordenar las
        tarjetas por número de likes (orden dinámico en index y en filtros).
        """
        likes = VotoPresupuesto.query.filter_by(presupuesto_id=presupuesto.id, tipo='like').count()
        dislikes = VotoPresupuesto.query.filter_by(presupuesto_id=presupuesto.id, tipo='dislike').count()
        presupuesto.likes = likes
        presupuesto.dislikes = dislikes

    @app.route('/api/presupuesto/<int:id>')
    def api_presupuesto_detalle(id):
        """
        Retorna JSON con detalle del presupuesto para el modal.
        Incluye comentarios (con id para que Admin pueda eliminar) y cantidad_gasto.
        """
        presupuesto = Presupuesto.query.get_or_404(id)
        comentarios = [
            {'id': c.id, 'autor': c.autor or 'Anónimo', 'contenido': c.contenido, 'fecha': c.fecha_creacion.isoformat() if c.fecha_creacion else ''}
            for c in presupuesto.comentarios.all()
        ]
        # Estado de voto del usuario actual (para mostrar like/dislike activo)
        mi_voto = None
        if current_user.is_authenticated:
            v = VotoPresupuesto.query.filter_by(usuario_id=current_user.id, presupuesto_id=presupuesto.id).first()
            if v:
                mi_voto = v.tipo
        return jsonify({
            'id': presupuesto.id,
            'concepto': presupuesto.concepto,
            'descripcion': presupuesto.descripcion or '',
            'descripcion_corta': presupuesto.descripcion_corta or (presupuesto.descripcion[:80] + '...' if presupuesto.descripcion and len(presupuesto.descripcion) > 80 else (presupuesto.descripcion or '')),
            'imagen_url': presupuesto.imagen_url or '',
            'fecha': presupuesto.fecha.isoformat() if presupuesto.fecha else '',
            'categoria': presupuesto.categoria,
            'monto': presupuesto.monto,
            'cantidad_gasto': getattr(presupuesto, 'cantidad_gasto', 0) or 0,
            'likes': presupuesto.likes or 0,
            'dislikes': presupuesto.dislikes or 0,
            'mi_voto': mi_voto,
            'comentarios': comentarios,
            'es_admin': current_user.is_authenticated and current_user.es_administrador,
        })

    @app.route('/api/presupuesto/<int:id>/like', methods=['POST'])
    @login_required
    def api_presupuesto_like(id):
        """
        Registra like en tabla VotoPresupuesto. Un voto por usuario: si ya votó,
        se cambia a like (o se mantiene). Anti-spam: no se duplican votos.
        """
        presupuesto = Presupuesto.query.get_or_404(id)
        voto = VotoPresupuesto.query.filter_by(usuario_id=current_user.id, presupuesto_id=presupuesto.id).first()
        if voto:
            voto.tipo = 'like'
        else:
            db.session.add(VotoPresupuesto(usuario_id=current_user.id, presupuesto_id=presupuesto.id, tipo='like'))
        _recalcular_likes_dislikes(presupuesto)
        db.session.commit()
        return jsonify({'likes': presupuesto.likes, 'dislikes': presupuesto.dislikes})

    @app.route('/api/presupuesto/<int:id>/dislike', methods=['POST'])
    @login_required
    def api_presupuesto_dislike(id):
        """Registra dislike; un voto por usuario (ver comentario en api_presupuesto_like)."""
        presupuesto = Presupuesto.query.get_or_404(id)
        voto = VotoPresupuesto.query.filter_by(usuario_id=current_user.id, presupuesto_id=presupuesto.id).first()
        if voto:
            voto.tipo = 'dislike'
        else:
            db.session.add(VotoPresupuesto(usuario_id=current_user.id, presupuesto_id=presupuesto.id, tipo='dislike'))
        _recalcular_likes_dislikes(presupuesto)
        db.session.commit()
        return jsonify({'likes': presupuesto.likes, 'dislikes': presupuesto.dislikes})

    @app.route('/api/comentario/<int:id>/eliminar', methods=['POST'])
    @login_required
    def api_comentario_eliminar(id):
        """Elimina un comentario. Solo correos @alumnos.udg.mx; 403 si no."""
        email = getattr(current_user, 'email', '') or ''
        if not email or email.split('@')[-1].lower() != 'alumnos.udg.mx':
            abort(403)
        c = Comentario.query.get_or_404(id)
        presupuesto_id = c.presupuesto_id
        db.session.delete(c)
        db.session.commit()
        return jsonify({'ok': True, 'presupuesto_id': presupuesto_id})

    @app.route('/api/presupuesto/<int:id>/comentarios', methods=['POST'])
    def api_presupuesto_comentarios(id):
        """
        Añade un comentario al presupuesto (estilo Facebook).
        Body JSON o form: autor (opcional), contenido (obligatorio).
        Retorna el comentario creado para mostrarlo en el modal sin recargar.
        """
        presupuesto = Presupuesto.query.get_or_404(id)
        if request.is_json:
            data = request.get_json() or {}
            autor = (data.get('autor') or '').strip() or 'Anónimo'
            contenido = (data.get('contenido') or '').strip()
        else:
            autor = (request.form.get('autor') or '').strip() or 'Anónimo'
            contenido = (request.form.get('contenido') or '').strip()
        if not contenido:
            return jsonify({'error': 'El comentario no puede estar vacío.'}), 400
        c = Comentario(presupuesto_id=presupuesto.id, autor=autor, contenido=contenido)
        db.session.add(c)
        db.session.commit()
        return jsonify({
            'id': c.id,
            'autor': c.autor,
            'contenido': c.contenido,
            'fecha': c.fecha_creacion.isoformat() if c.fecha_creacion else '',
        })

    # =========================================================================
    # RUTAS DE AUTENTICACIÓN - Solo @alumnos.udg.mx + verificación por correo
    # =========================================================================

    def send_async_email(app_instance, mail_instance, msg):
        """Envía el correo en segundo plano para evitar timeouts. Muestra error real en terminal."""
        with app_instance.app_context():
            try:
                print('[SISTEMA] Intentando enviar código...', flush=True)
                mail_instance.send(msg)
                print('[SISTEMA] Correo enviado correctamente.', flush=True)
            except Exception as e:
                print(f'[ERROR CRÍTICO]: {e}', flush=True)

    def _enviar_codigo_verificacion(email_destino, codigo):
        """Genera el mensaje y lo envía en un hilo para no bloquear la app."""
        msg = Message(
            subject='Código de verificación - CUCEA Transparencia',
            recipients=[email_destino],
            body=f'Tu código de verificación es: {codigo}\n\nVálido por {app.config.get("VERIFICATION_CODE_EXPIRY_MINUTES", 15)} minutos.\n\nSi no solicitaste este registro, ignora este correo.',
            sender=app.config.get('MAIL_DEFAULT_SENDER'),
        )
        thread = threading.Thread(target=send_async_email, args=(app, mail, msg))
        thread.start()

    @app.route('/auth/login', methods=['GET', 'POST'])
    def auth_login():
        """Inicio de sesión. Solo correos @alumnos.udg.mx."""
        if current_user.is_authenticated:
            return redirect(url_for('presupuestos_lista'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            # Validación estricta: solo dominio exacto @alumnos.udg.mx (no subdominios falsos)
            dominio_permitido = 'alumnos.udg.mx'
            if not email or '@' not in email or email.split('@')[-1].lower() != dominio_permitido:
                flash(f'Solo correos @{dominio_permitido} pueden iniciar sesión.', 'error')
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
        Registro: solo @alumnos.udg.mx. No crea la cuenta aquí; guarda en PendingRegistro,
        genera código de 6 dígitos, lo envía por correo (Flask-Mail) y redirige a verificar.
        La cuenta se crea en auth_verificar cuando el usuario introduce el código correcto.
        """
        if current_user.is_authenticated:
            return redirect(url_for('presupuestos_lista'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            nombre = request.form.get('nombre', '').strip()
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')

            # Validación estricta: solo @alumnos.udg.mx (dominio exacto, sin subdominios)
            dominio_permitido = 'alumnos.udg.mx'
            if not email or '@' not in email or email.split('@')[-1].lower() != dominio_permitido:
                flash(f'Solo correos @{dominio_permitido} pueden registrarse.', 'error')
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

            codigo = ''.join(random.choices(string.digits, k=6))
            usuario_temp = Usuario(email=email, nombre=nombre, es_admin=True)
            usuario_temp.set_password(password)

            # Guardar en PendingRegistro (no en Usuario hasta verificar)
            pend = PendingRegistro(
                email=email,
                nombre=nombre,
                password_hash=usuario_temp.password_hash,
                codigo=codigo,
            )
            db.session.add(pend)
            db.session.commit()

            # Guardar en sesión (temporalmente) para verificación sin parámetros en URL
            session['pending_verification_email'] = email
            session['pending_verification_codigo'] = codigo
            _enviar_codigo_verificacion(email, codigo)
            flash('Revisa tu correo: te enviamos un código de 6 dígitos. Introducelo a continuación.', 'success')
            return redirect(url_for('auth_verificar'))

        return render_template('auth/registro.html')

    @app.route('/auth/verificar', methods=['GET', 'POST'])
    def auth_verificar():
        """
        Verificación por POST: el correo viene de la sesión (no de la URL).
        El usuario introduce el código de 6 dígitos; si es correcto, se crea la cuenta en la BD.
        """
        email = session.get('pending_verification_email', '').strip().lower()
        if not email:
            flash('Sesión de verificación no encontrada. Completa el registro de nuevo.', 'error')
            return redirect(url_for('auth_registro'))

        if request.method == 'POST':
            codigo = request.form.get('codigo', '').strip()
            if len(codigo) != 6 or not codigo.isdigit():
                flash('El código debe tener 6 dígitos.', 'error')
                return render_template('auth/verificar.html', email=email)

            # Validar código: sesión o PendingRegistro
            codigo_ok = (session.get('pending_verification_codigo') == codigo)
            pend = PendingRegistro.query.filter_by(email=email).order_by(PendingRegistro.creado_at.desc()).first()
            if not codigo_ok and pend:
                codigo_ok = (pend.codigo == codigo)
            if not codigo_ok:
                flash('Código incorrecto.', 'error')
                return render_template('auth/verificar.html', email=email)
            if not pend:
                flash('No hay registro pendiente para ese correo. Regístrate de nuevo.', 'error')
                session.pop('pending_verification_email', None)
                session.pop('pending_verification_codigo', None)
                return redirect(url_for('auth_registro'))

            # Solo si el código coincide: crear usuario en la BD y limpiar sesión
            usuario = Usuario(email=pend.email, nombre=pend.nombre, es_admin=True)
            usuario.password_hash = pend.password_hash
            db.session.add(usuario)
            db.session.delete(pend)
            db.session.commit()
            session.pop('pending_verification_email', None)
            session.pop('pending_verification_codigo', None)
            flash('Cuenta verificada correctamente. Inicia sesión.', 'success')
            return redirect(url_for('auth_login'))

        return render_template('auth/verificar.html', email=email)

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
    @admin_required
    def presupuesto_nuevo():
        """
        Crear nuevo proyecto presupuestario.
        Solo correos @alumnos.udg.mx (validado por admin_required); 403 en caso contrario.
        """

        if request.method == 'POST':
            concepto = request.form.get('concepto', '').strip()
            monto = request.form.get('monto')
            categoria = request.form.get('categoria', '').strip()
            fecha_str = request.form.get('fecha')
            descripcion_corta = request.form.get('descripcion_corta', '').strip() or None
            descripcion = request.form.get('descripcion', '').strip() or None
            imagen_url = request.form.get('imagen_url', '').strip() or None
            cantidad_gasto = request.form.get('cantidad_gasto')

            if not concepto or not monto or not categoria or not fecha_str:
                flash('Completa todos los campos obligatorios.', 'error')
                return render_template('presupuesto/formulario.html', presupuesto=None, categorias=CATEGORIAS)

            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                monto_val = float(monto)
                cantidad_gasto_val = float(cantidad_gasto) if cantidad_gasto else 0
            except (ValueError, TypeError):
                flash('Datos inválidos.', 'error')
                return render_template('presupuesto/formulario.html', presupuesto=None, categorias=CATEGORIAS)

            # cantidad_gasto solo se define al crear; después no es editable (integridad del presupuesto).
            p = Presupuesto(
                concepto=concepto,
                monto=monto_val,
                categoria=categoria,
                fecha=fecha,
                descripcion_corta=descripcion_corta,
                descripcion=descripcion or None,
                imagen_url=imagen_url,
                cantidad_gasto=cantidad_gasto_val,
            )
            db.session.add(p)
            db.session.commit()
            flash('Proyecto guardado correctamente.', 'success')
            return redirect(url_for('presupuestos_lista'))

        return render_template('presupuesto/formulario.html', presupuesto=None, categorias=CATEGORIAS)

    @app.route('/presupuesto/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def presupuesto_editar(id):
        """
        Editar proyecto existente.
        Solo @alumnos.udg.mx; 403 si no.
        """

        presupuesto = Presupuesto.query.get_or_404(id)

        if request.method == 'POST':
            presupuesto.concepto = request.form.get('concepto', '').strip()
            presupuesto.categoria = request.form.get('categoria', '').strip()
            presupuesto.descripcion_corta = request.form.get('descripcion_corta', '').strip() or None
            presupuesto.descripcion = request.form.get('descripcion', '').strip() or None
            presupuesto.imagen_url = request.form.get('imagen_url', '').strip() or None
            # cantidad_gasto NO se edita: solo se define al crear la tarjeta (regla de integridad).
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
    @admin_required
    def presupuesto_eliminar(id):
        """Eliminar proyecto. Solo @alumnos.udg.mx; 403 si no."""
        presupuesto = Presupuesto.query.get_or_404(id)
        db.session.delete(presupuesto)
        db.session.commit()
        flash('Proyecto eliminado.', 'info')
        return redirect(url_for('presupuestos_lista'))

    # -------------------------------------------------------------------------
    # Borrar presupuesto: ruta solicitada para el botón "Borrar" (ícono basura) del Admin.
    # Funcionamiento: POST con CSRF; se elimina el registro y se redirige al listado.
    # Solo administradores (@academicos.mx) pueden ejecutar esta acción.
    # -------------------------------------------------------------------------
    @app.route('/borrar_presupuesto/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def borrar_presupuesto(id):
        """
        Elimina un presupuesto por id. Solo @alumnos.udg.mx (admin_required); 403 si no.
        Usado desde el botón Borrar en cards y detalle.
        """
        presupuesto = Presupuesto.query.get_or_404(id)
        db.session.delete(presupuesto)
        db.session.commit()
        flash('Presupuesto eliminado correctamente.', 'info')
        return redirect(url_for('presupuestos_lista'))

    # -------------------------------------------------------------------------
    # RUTAS ADMIN: Edición in-place (carrusel, textos). Solo @academicos.mx.
    # -------------------------------------------------------------------------

    def seed_data():
        """
        Datos de prueba: crea exactamente 5 presupuestos ficticios.
        Se ejecuta UNA SOLA VEZ al arrancar la app (cuando no hay presupuestos).
        Usa imágenes placeholder de https://picsum.photos/400/300 y fechas actuales/recientes.
        Incluye categorías para probar filtros y descripción larga para el modal.
        """
        if Presupuesto.query.count() > 0:
            return False
        hoy = date.today()
        # 5 presupuestos con cantidad_gasto para verificar suma en Navbar (Total Invertido)
        registros = [
            {'concepto': 'Laboratorio de Química', 'descripcion_corta': 'Equipamiento y reactivos para prácticas.', 'descripcion': 'Proyecto de equipamiento del laboratorio de química del edificio B. Incluye mesas de trabajo resistentes a ácidos, campanas de extracción y dotación de reactivos.', 'categoria': 'Equipamiento', 'monto': 450000.00, 'cantidad_gasto': 50000.00, 'fecha': hoy - timedelta(days=30), 'imagen_url': 'https://picsum.photos/400/300?random=1'},
            {'concepto': 'Canchas Deportivas', 'descripcion_corta': 'Mantenimiento y mejora de canchas.', 'descripcion': 'Refacción de canchas: pintado de líneas, reparación de mallas y mejoras en drenaje.', 'categoria': 'Infraestructura', 'monto': 280000.00, 'cantidad_gasto': 120000.00, 'fecha': hoy - timedelta(days=15), 'imagen_url': 'https://picsum.photos/400/300?random=2'},
            {'concepto': 'Servicios de limpieza', 'descripcion_corta': 'Contrato de limpieza.', 'descripcion': 'Contrato semestral de limpieza para oficinas y pasillos de edificios A y C.', 'categoria': 'Servicios', 'monto': 120000.00, 'cantidad_gasto': 85000.00, 'fecha': hoy - timedelta(days=7), 'imagen_url': 'https://picsum.photos/400/300?random=3'},
            {'concepto': 'Material didáctico contabilidad', 'descripcion_corta': 'Libros y licencias.', 'descripcion': 'Adquisición de libros y licencias de software para contabilidad y auditoría.', 'categoria': 'Material didáctico', 'monto': 95000.00, 'cantidad_gasto': 72000.00, 'fecha': hoy, 'imagen_url': 'https://picsum.photos/400/300?random=4'},
            {'concepto': 'Capacitación en seguridad', 'descripcion_corta': 'Talleres de prevención.', 'descripcion': 'Capacitación en seguridad y primeros auxilios para intendencia y vigilancia.', 'categoria': 'Capacitación', 'monto': 65000.00, 'cantidad_gasto': 43000.00, 'fecha': hoy, 'imagen_url': 'https://picsum.photos/400/300?random=5'},
        ]
        for d in registros:
            p = Presupuesto(
                concepto=d['concepto'],
                descripcion_corta=d['descripcion_corta'],
                descripcion=d['descripcion'],
                categoria=d['categoria'],
                monto=d['monto'],
                cantidad_gasto=d['cantidad_gasto'],
                fecha=d['fecha'],
                imagen_url=d['imagen_url'],
            )
            db.session.add(p)
        db.session.commit()
        return True

    @app.route('/admin/seed')
    @login_required
    @admin_required
    def admin_seed():
        """Insertar 5 presupuestos de prueba. Solo @alumnos.udg.mx."""
        if seed_data():
            flash('Se insertaron 5 presupuestos de prueba.', 'success')
        else:
            flash('Ya existen presupuestos. No se insertaron duplicados.', 'info')
        return redirect(url_for('presupuestos_lista'))

    @app.route('/admin/carrusel', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_carrusel():
        """
        Administración del carrusel (franja 1). Solo @alumnos.udg.mx.
        GET: Lista slides. POST: Crear o actualizar slide.
        """
        if request.method == 'POST':
            accion = request.form.get('accion', 'crear')
            if accion == 'crear':
                max_orden = db.session.query(db.func.max(CarruselSlide.orden)).scalar()
                orden = (max_orden or -1) + 1
                slide = CarruselSlide(
                    orden=orden,
                    imagen_url=request.form.get('imagen_url', '').strip() or 'https://via.placeholder.com/800x500',
                    titulo_alt=request.form.get('titulo_alt', '').strip() or None,
                )
                db.session.add(slide)
                db.session.commit()
                flash('Imagen del carrusel añadida.', 'success')
            else:
                # actualizar
                sid = request.form.get('slide_id', type=int)
                slide = CarruselSlide.query.get(sid)
                if slide:
                    slide.imagen_url = request.form.get('imagen_url', '').strip() or slide.imagen_url
                    slide.titulo_alt = request.form.get('titulo_alt', '').strip() or None
                    db.session.commit()
                    flash('Slide actualizado.', 'success')
            return redirect(url_for('admin_carrusel'))
        slides = CarruselSlide.query.order_by(CarruselSlide.orden).all()
        return render_template('admin/carrusel.html', slides=slides)

    @app.route('/admin/carrusel/<int:id>/eliminar', methods=['POST'])
    @login_required
    @admin_required
    def admin_carrusel_eliminar(id):
        """Elimina un slide del carrusel. Solo @alumnos.udg.mx."""
        slide = CarruselSlide.query.get_or_404(id)
        db.session.delete(slide)
        db.session.commit()
        flash('Imagen eliminada del carrusel.', 'info')
        return redirect(url_for('admin_carrusel'))

    @app.route('/admin/contenido', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_contenido():
        """
        Edición de textos de la franja 1. Solo @alumnos.udg.mx.
        Valores en ContenidoSite por clave.
        """
        claves = ['index_franja1_titulo', 'index_franja1_subtitulo', 'index_franja1_parrafo1', 'index_franja1_parrafo2', 'index_fondo_url']
        if request.method == 'POST':
            for key in claves:
                val = request.form.get(key, '').strip()
                rec = ContenidoSite.query.get(key)
                if val:
                    if rec:
                        rec.valor = val
                    else:
                        db.session.add(ContenidoSite(clave=key, valor=val))
                elif rec:
                    db.session.delete(rec)
            db.session.commit()
            flash('Textos actualizados.', 'success')
            return redirect(url_for('index'))
        contenido = {k: (ContenidoSite.query.get(k).valor if ContenidoSite.query.get(k) else '') for k in claves}
        return render_template('admin/contenido.html', contenido=contenido, claves=claves)

    # -------------------------------------------------------------------------
    # Crear tablas y migrar columnas si no existen (compatibilidad con BD antiguas)
    # -------------------------------------------------------------------------
    with app.app_context():
        import os
        from sqlalchemy import text
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()

        # Migración presupuestos: cantidad_gasto y columnas previas
        try:
            result = db.session.execute(text("PRAGMA table_info(presupuestos)"))
            columns = [row[1] for row in result.fetchall()]
            for col, def_sql in [
                ('imagen_url', 'ALTER TABLE presupuestos ADD COLUMN imagen_url VARCHAR(500)'),
                ('descripcion_corta', 'ALTER TABLE presupuestos ADD COLUMN descripcion_corta VARCHAR(300)'),
                ('likes', 'ALTER TABLE presupuestos ADD COLUMN likes INTEGER DEFAULT 0'),
                ('dislikes', 'ALTER TABLE presupuestos ADD COLUMN dislikes INTEGER DEFAULT 0'),
                ('cantidad_gasto', 'ALTER TABLE presupuestos ADD COLUMN cantidad_gasto REAL DEFAULT 0'),
            ]:
                if columns and col not in columns:
                    db.session.execute(text(def_sql))
                    db.session.commit()
        except Exception:
            db.session.rollback()

        # ---------------------------------------------------------------------
        # Datos de prueba: ejecutar seed_data() UNA SOLA VEZ al arrancar.
        # Si ya existen presupuestos, no se inserta nada (evita duplicados).
        # ---------------------------------------------------------------------
        seed_data()

    return app


# =============================================================================
# Punto de entrada - Ejecutar con: python app.py
# =============================================================================
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
