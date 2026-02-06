"""
=============================================================================
PLATAFORMA DE TRANSPARENCIA PRESUPUESTARIA - CUCEA
Aplicación principal Flask - Plataforma escolar de transparencia informativa
=============================================================================

Regla de oro de autenticación:
- SOLO los correos que terminen en @academicos.mx pueden registrarse e iniciar sesión.
- Se bloquea cualquier intento con @alumnos.mx o cualquier otro dominio.
- Los usuarios registrados con @academicos.mx tienen automáticamente permisos de ADMIN.

Gestión de presupuestos: Admin puede Editar y Borrar (ruta borrar_presupuesto/<id>).
Datos de prueba: seed_data() se ejecuta una sola vez al arrancar la app (5 presupuestos).
"""

from datetime import datetime, date, timedelta
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect

from config import Config
from extensions import db, login_manager
from models import Usuario, Presupuesto, Comentario, CarruselSlide, ContenidoSite


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

        # Presupuestos para el carrusel de cards (se muestran 3 en vista, centro resaltado)
        presupuestos = Presupuesto.query.order_by(Presupuesto.fecha.desc()).limit(12).all()
        return render_template(
            'index.html',
            presupuestos=presupuestos,
            carousel_slides=slides,
            contenido_franja1=contenido_franja1,
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

    # -------------------------------------------------------------------------
    # API para el modal de detalle (Index): datos JSON, like, dislike, comentarios
    # El modal bloquea el scroll del fondo y tiene scroll interno.
    # -------------------------------------------------------------------------

    @app.route('/api/presupuesto/<int:id>')
    def api_presupuesto_detalle(id):
        """
        Retorna JSON con detalle del presupuesto para llenar el modal.
        Incluye descripción larga, likes, dislikes y lista de comentarios.
        """
        presupuesto = Presupuesto.query.get_or_404(id)
        comentarios = [
            {'id': c.id, 'autor': c.autor or 'Anónimo', 'contenido': c.contenido, 'fecha': c.fecha_creacion.isoformat() if c.fecha_creacion else ''}
            for c in presupuesto.comentarios.all()
        ]
        return jsonify({
            'id': presupuesto.id,
            'concepto': presupuesto.concepto,
            'descripcion': presupuesto.descripcion or '',
            'descripcion_corta': presupuesto.descripcion_corta or (presupuesto.descripcion[:80] + '...' if presupuesto.descripcion and len(presupuesto.descripcion) > 80 else (presupuesto.descripcion or '')),
            'imagen_url': presupuesto.imagen_url or '',
            'fecha': presupuesto.fecha.isoformat() if presupuesto.fecha else '',
            'categoria': presupuesto.categoria,
            'monto': presupuesto.monto,
            'likes': presupuesto.likes or 0,
            'dislikes': presupuesto.dislikes or 0,
            'comentarios': comentarios,
        })

    @app.route('/api/presupuesto/<int:id>/like', methods=['POST'])
    def api_presupuesto_like(id):
        """Incrementa el contador de likes y retorna el nuevo valor (para actualizar el modal)."""
        presupuesto = Presupuesto.query.get_or_404(id)
        presupuesto.likes = (presupuesto.likes or 0) + 1
        db.session.commit()
        return jsonify({'likes': presupuesto.likes})

    @app.route('/api/presupuesto/<int:id>/dislike', methods=['POST'])
    def api_presupuesto_dislike(id):
        """Incrementa el contador de dislikes y retorna el nuevo valor."""
        presupuesto = Presupuesto.query.get_or_404(id)
        presupuesto.dislikes = (presupuesto.dislikes or 0) + 1
        db.session.commit()
        return jsonify({'dislikes': presupuesto.dislikes})

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

            # Validación estricta: SOLO @academicos.mx. Bloqueamos @alumnos.mx y cualquier otro dominio.
            if not email.endswith(dominio):
                flash(f'Solo correos institucionales ({dominio}) pueden iniciar sesión. Otros dominios están bloqueados.', 'error')
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

            # Bloqueo explícito: solo @academicos.mx. @alumnos.mx y el resto no pueden registrarse.
            if not email.endswith(dominio):
                flash(f'El registro está restringido. Solo correos {dominio} pueden registrarse. Otros dominios están bloqueados.', 'error')
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
            descripcion_corta = request.form.get('descripcion_corta', '').strip() or None
            descripcion = request.form.get('descripcion', '').strip() or None
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
                descripcion_corta=descripcion_corta,
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
            presupuesto.descripcion_corta = request.form.get('descripcion_corta', '').strip() or None
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
        Eliminar proyecto (alias interno).
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
    # Borrar presupuesto: ruta solicitada para el botón "Borrar" (ícono basura) del Admin.
    # Funcionamiento: POST con CSRF; se elimina el registro y se redirige al listado.
    # Solo administradores (@academicos.mx) pueden ejecutar esta acción.
    # -------------------------------------------------------------------------
    @app.route('/borrar_presupuesto/<int:id>', methods=['POST'])
    @login_required
    def borrar_presupuesto(id):
        """
        Elimina un presupuesto por id. Solo Admin.
        Se usa desde el botón 'Borrar' (ícono de basura) en cada card y en detalle.
        El borrado es definitivo: se elimina el registro de la base de datos y sus
        comentarios asociados (por FK en cascada o manualmente según el modelo).
        """
        if not current_user.es_administrador:
            abort(403)
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
        registros = [
            {
                'concepto': 'Laboratorio de Química',
                'descripcion_corta': 'Equipamiento y reactivos para prácticas de química orgánica.',
                'descripcion': 'Proyecto de equipamiento del laboratorio de química del edificio B. Incluye mesas de trabajo resistentes a ácidos, campanas de extracción, y dotación de reactivos para el ciclo actual. La descripción larga se muestra en el modal al hacer clic en la tarjeta.',
                'categoria': 'Equipamiento',
                'monto': 450000.00,
                'fecha': hoy - timedelta(days=30),
                'imagen_url': 'https://picsum.photos/400/300?random=1',
            },
            {
                'concepto': 'Canchas Deportivas',
                'descripcion_corta': 'Mantenimiento y mejora de canchas de fútbol y básquetbol.',
                'descripcion': 'Refacción de las canchas deportivas del campus: pintado de líneas, reparación de mallas y mejoras en el drenaje. Se priorizan las canchas de uso común para torneos interdivisionales.',
                'categoria': 'Infraestructura',
                'monto': 280000.00,
                'fecha': hoy - timedelta(days=15),
                'imagen_url': 'https://picsum.photos/400/300?random=2',
            },
            {
                'concepto': 'Servicios de limpieza',
                'descripcion_corta': 'Contrato de limpieza para edificios administrativos.',
                'descripcion': 'Contrato semestral de servicios de limpieza para oficinas, pasillos y baños de los edificios A y C. Incluye suministro de material y supervisión.',
                'categoria': 'Servicios',
                'monto': 120000.00,
                'fecha': hoy - timedelta(days=7),
                'imagen_url': 'https://picsum.photos/400/300?random=3',
            },
            {
                'concepto': 'Material didáctico para contabilidad',
                'descripcion_corta': 'Libros y licencias de software contable.',
                'descripcion': 'Adquisición de libros de texto actualizados y licencias de software educativo para las materias de contabilidad y auditoría. Beneficia a los alumnos de la división de Contaduría.',
                'categoria': 'Material didáctico',
                'monto': 95000.00,
                'fecha': hoy,
                'imagen_url': 'https://picsum.photos/400/300?random=4',
            },
            {
                'concepto': 'Capacitación en seguridad',
                'descripcion_corta': 'Talleres de prevención y primeros auxilios.',
                'descripcion': 'Programa de capacitación en seguridad y primeros auxilios para personal de intendencia y vigilancia. Incluye material impreso y certificación por Protección Civil.',
                'categoria': 'Capacitación',
                'monto': 65000.00,
                'fecha': hoy,
                'imagen_url': 'https://picsum.photos/400/300?random=5',
            },
        ]
        for d in registros:
            p = Presupuesto(
                concepto=d['concepto'],
                descripcion_corta=d['descripcion_corta'],
                descripcion=d['descripcion'],
                categoria=d['categoria'],
                monto=d['monto'],
                fecha=d['fecha'],
                imagen_url=d['imagen_url'],
            )
            db.session.add(p)
        db.session.commit()
        return True

    @app.route('/admin/seed')
    @login_required
    def admin_seed():
        """Opcional: insertar 5 presupuestos de prueba manualmente (solo Admin)."""
        if not current_user.es_administrador:
            abort(403)
        if seed_data():
            flash('Se insertaron 5 presupuestos de prueba.', 'success')
        else:
            flash('Ya existen presupuestos. No se insertaron duplicados.', 'info')
        return redirect(url_for('presupuestos_lista'))

    @app.route('/admin/carrusel', methods=['GET', 'POST'])
    @login_required
    def admin_carrusel():
        """
        Administración del carrusel de imágenes de la franja 1 (index).
        GET: Lista de slides con botones Editar/Subir (añadir).
        POST: Crear o actualizar slide (imagen_url, titulo_alt, orden).
        """
        if not current_user.es_administrador:
            abort(403)
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
    def admin_carrusel_eliminar(id):
        """Elimina un slide del carrusel (solo Admin)."""
        if not current_user.es_administrador:
            abort(403)
        slide = CarruselSlide.query.get_or_404(id)
        db.session.delete(slide)
        db.session.commit()
        flash('Imagen eliminada del carrusel.', 'info')
        return redirect(url_for('admin_carrusel'))

    @app.route('/admin/contenido', methods=['GET', 'POST'])
    @login_required
    def admin_contenido():
        """
        Edición de textos de la franja 1 (título, párrafos).
        Los valores se guardan en ContenidoSite por clave.
        """
        if not current_user.es_administrador:
            abort(403)
        claves = ['index_franja1_titulo', 'index_franja1_subtitulo', 'index_franja1_parrafo1', 'index_franja1_parrafo2']
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

        # Migración presupuestos: columnas imagen_url, descripcion_corta, likes, dislikes
        try:
            result = db.session.execute(text("PRAGMA table_info(presupuestos)"))
            columns = [row[1] for row in result.fetchall()]
            for col, def_sql in [
                ('imagen_url', 'ALTER TABLE presupuestos ADD COLUMN imagen_url VARCHAR(500)'),
                ('descripcion_corta', 'ALTER TABLE presupuestos ADD COLUMN descripcion_corta VARCHAR(300)'),
                ('likes', 'ALTER TABLE presupuestos ADD COLUMN likes INTEGER DEFAULT 0'),
                ('dislikes', 'ALTER TABLE presupuestos ADD COLUMN dislikes INTEGER DEFAULT 0'),
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
