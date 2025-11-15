from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import os
import sqlite3
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from analizador import detectar_amenazas, init_db
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackaton-seguridad-nacional-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('alertas_frames', exist_ok=True)

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inicializar base de datos al iniciar
init_db()

# ------------------ BASE DE DATOS DE PATRULLAS ------------------ #

def init_patrullas_db():
    """Crea la base de datos de patrullas si no existe"""
    conn = sqlite3.connect('alertas.db')
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patrullas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_patrulla TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            zona TEXT NOT NULL,
            municipio TEXT NOT NULL,
            departamento TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'disponible',
            latitud REAL,
            longitud REAL,
            oficial_encargado TEXT,
            telefono TEXT,
            ultima_actualizacion TEXT,
            observaciones TEXT
        )
    """)
    conn.commit()
    
    # Insertar patrullas de ejemplo si no existen
    cur.execute("SELECT COUNT(*) FROM patrullas")
    if cur.fetchone()[0] == 0:
        patrullas_ejemplo = [
            ('PAT-001', 'Policía Nacional Civil', 'Centro Histórico', 'San Salvador', 'San Salvador', 'activa', 13.6929, -89.2182, 'Oficial Martínez', '2234-5678', datetime.now().isoformat(), 'Patrulla en servicio regular'),
            ('PAT-002', 'Policía Nacional Civil', 'Colonia Escalón', 'San Salvador', 'San Salvador', 'disponible', 13.7000, -89.2500, 'Oficial Rodríguez', '2234-5679', datetime.now().isoformat(), 'Patrulla disponible para asignación'),
            ('PAT-003', 'Policía Nacional Civil', 'Soyapango', 'Soyapango', 'San Salvador', 'en_ruta', 13.7100, -89.1400, 'Oficial Hernández', '2234-5680', datetime.now().isoformat(), 'En ruta hacia incidente reportado'),
            ('PAT-004', 'Policía Nacional Civil', 'Santa Ana Centro', 'Santa Ana', 'Santa Ana', 'activa', 13.9942, -89.5597, 'Oficial López', '2441-1234', datetime.now().isoformat(), 'Patrulla en servicio regular'),
            ('PAT-005', 'Policía Nacional Civil', 'San Miguel Centro', 'San Miguel', 'San Miguel', 'disponible', 13.4833, -88.1833, 'Oficial García', '2661-2345', datetime.now().isoformat(), 'Patrulla disponible'),
            ('PAT-006', 'Policía Nacional Civil', 'La Libertad', 'La Libertad', 'La Libertad', 'activa', 13.4881, -89.3219, 'Oficial Vásquez', '2345-6789', datetime.now().isoformat(), 'Patrulla en servicio regular'),
            ('PAT-007', 'Policía Nacional Civil', 'Apopa', 'Apopa', 'San Salvador', 'en_ruta', 13.8078, -89.1794, 'Oficial Ramírez', '2234-5681', datetime.now().isoformat(), 'Respondiendo a alerta de seguridad'),
            ('PAT-008', 'Policía Nacional Civil', 'Mejicanos', 'Mejicanos', 'San Salvador', 'activa', 13.7400, -89.2100, 'Oficial Torres', '2234-5682', datetime.now().isoformat(), 'Patrulla en servicio regular'),
            ('PAT-009', 'Policía Nacional Civil', 'Ahuachapán', 'Ahuachapán', 'Ahuachapán', 'disponible', 13.9214, -89.8450, 'Oficial Morales', '2443-1234', datetime.now().isoformat(), 'Patrulla disponible'),
            ('PAT-010', 'Policía Nacional Civil', 'Zona Rosa', 'San Salvador', 'San Salvador', 'activa', 13.6900, -89.2400, 'Oficial Castro', '2234-5683', datetime.now().isoformat(), 'Patrulla en servicio regular'),
        ]
        
        for patrulla in patrullas_ejemplo:
            cur.execute("""
                INSERT INTO patrullas 
                (numero_patrulla, tipo, zona, municipio, departamento, estado, latitud, longitud, 
                 oficial_encargado, telefono, ultima_actualizacion, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, patrulla)
        
        conn.commit()
    
    conn.close()

# Inicializar base de datos de patrullas
init_patrullas_db()

# ------------------ AUTENTICACIÓN ------------------ #

def init_users_db():
    """Crea la base de datos de usuarios si no existe"""
    conn = sqlite3.connect('usuarios.db')
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT UNIQUE NOT NULL,
            contraseña TEXT NOT NULL,
            nombre TEXT NOT NULL,
            fecha_registro TEXT NOT NULL,
            rol TEXT DEFAULT 'usuario'
        )
    """)
    conn.commit()
    
    # Migración: agregar columna 'rol' si no existe
    try:
        cur.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT DEFAULT 'usuario'")
        conn.commit()
    except sqlite3.OperationalError:
        # La columna ya existe, no hacer nada
        pass
    
    # Crear usuario por defecto si no existe
    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        # Usuario: admin@vigia.com, Contraseña: admin123, Rol: admin
        password_hash = generate_password_hash('admin123')
        cur.execute("""
            INSERT INTO usuarios (correo, contraseña, nombre, fecha_registro, rol)
            VALUES (?, ?, ?, ?, ?)
        """, ('admin@vigia.com', password_hash, 'Administrador', datetime.now().isoformat(), 'admin'))
        conn.commit()
    else:
        # Asegurar que el usuario admin tenga rol 'admin' (siempre actualizar)
        cur.execute("SELECT id FROM usuarios WHERE correo = 'admin@vigia.com'")
        admin = cur.fetchone()
        if admin:
            # Actualizar siempre el rol del admin a 'admin'
            cur.execute("UPDATE usuarios SET rol = 'admin' WHERE correo = 'admin@vigia.com'")
            conn.commit()
            print("[INIT] Usuario admin actualizado con rol 'admin'")
        else:
            # Si no existe el admin, crearlo
            password_hash = generate_password_hash('admin123')
            cur.execute("""
                INSERT INTO usuarios (correo, contraseña, nombre, fecha_registro, rol)
                VALUES (?, ?, ?, ?, ?)
            """, ('admin@vigia.com', password_hash, 'Administrador', datetime.now().isoformat(), 'admin'))
            conn.commit()
            print("[INIT] Usuario admin creado con rol 'admin'")
    
    conn.close()

def login_required(f):
    """Decorador para proteger rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorador para proteger rutas que requieren rol de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        if session.get('user_rol') != 'admin':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Inicializar base de datos de usuarios
init_users_db()

# ------------------ REPORTES DE USUARIOS AUTORIZADOS ------------------ #

def init_reportes_usuarios_db():
    """Crea la tabla de reportes para usuarios autorizados"""
    conn = sqlite3.connect('alertas.db')
    cur = conn.cursor()
    
    # Tabla de reportes de usuarios autorizados
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reportes_usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            imagen TEXT NOT NULL,
            descripcion TEXT,
            ubicacion TEXT,
            tipo_reporte TEXT,
            fecha_hora TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)
    
    conn.commit()
    conn.close()

# Inicializar base de datos de reportes de usuarios
init_reportes_usuarios_db()

# ------------------ USUARIOS DE LA POBLACIÓN ------------------ #

def init_poblacion_db():
    """Crea la base de datos de usuarios de la población y sus reportes"""
    conn = sqlite3.connect('poblacion.db')
    cur = conn.cursor()
    
    # Tabla de usuarios de la población
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_poblacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT UNIQUE NOT NULL,
            contraseña TEXT NOT NULL,
            nombre TEXT NOT NULL,
            telefono TEXT,
            fecha_registro TEXT NOT NULL,
            ultima_sesion TEXT
        )
    """)
    
    # Tabla de reportes de la población
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reportes_poblacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            imagen TEXT NOT NULL,
            descripcion TEXT,
            ubicacion TEXT,
            tipo_reporte TEXT,
            fecha_hora TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY (usuario_id) REFERENCES usuarios_poblacion(id)
        )
    """)
    
    conn.commit()
    conn.close()

# Inicializar base de datos de población
init_poblacion_db()

def poblacion_login_required(f):
    """Decorador para proteger rutas que requieren autenticación de población"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'poblacion_user_id' not in session:
            flash('Por favor, inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('poblacion_login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------ GESTIÓN DE DESTINATARIOS DE ALERTAS ------------------ #

def init_destinatarios_db():
    """Crea la base de datos de destinatarios de alertas si no existe"""
    conn = sqlite3.connect('alertas.db')
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS destinatarios_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ubicacion TEXT NOT NULL,
            nombre TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            activo INTEGER DEFAULT 1,
            fecha_creacion TEXT NOT NULL
        )
    """)
    
    # Crear tabla de historial de envíos si no existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historial_envios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alerta_id INTEGER,
            destinatario_id INTEGER,
            ubicacion TEXT NOT NULL,
            tipo_alerta TEXT NOT NULL,
            fecha_envio TEXT NOT NULL,
            estado TEXT DEFAULT 'enviado',
            FOREIGN KEY (destinatario_id) REFERENCES destinatarios_alertas(id)
        )
    """)
    
    conn.commit()
    conn.close()

# Inicializar base de datos de destinatarios
init_destinatarios_db()

def crear_servicio_emergencia(tipo_servicio, ubicacion):
    """
    Crea un destinatario automático de servicio de emergencia si no existe.
    
    Args:
        tipo_servicio: 'bomberos' o 'policia'
        ubicacion: Ubicación donde se necesita el servicio
    """
    conn = sqlite3.connect('alertas.db')
    cur = conn.cursor()
    
    # Verificar si ya existe (buscar por ubicación y tipo de servicio)
    cur.execute("""
        SELECT id FROM destinatarios_alertas 
        WHERE ubicacion = ? AND nombre LIKE ?
    """, (ubicacion, f'%{tipo_servicio}%'))
    
    if cur.fetchone():
        conn.close()
        print(f"[INFO] Servicio de {tipo_servicio} ya existe para {ubicacion}")
        return
    
    # Crear servicio de emergencia
    nombre = f"Servicio de {tipo_servicio.capitalize()} - {ubicacion}"
    if tipo_servicio == 'bomberos':
        email = "bomberos@emergencias.gov"
        telefono = "911"
    else:  # policia
        email = "policia@emergencias.gov"
        telefono = "911"
    
    cur.execute("""
        INSERT INTO destinatarios_alertas (ubicacion, nombre, email, telefono, activo, fecha_creacion)
        VALUES (?, ?, ?, ?, 1, ?)
    """, (ubicacion, nombre, email, telefono, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print(f"[SERVICIO CREADO] {nombre} para {ubicacion}")

def enviar_alerta_ubicacion(ubicacion, tipo_alerta, objeto, confianza, imagen_path):
    """
    Envía alerta a todos los destinatarios configurados para una ubicación específica.
    Si la confianza es >= 80%, también envía a servicios de emergencia automáticamente.
    
    Args:
        ubicacion: Ubicación donde se detectó la alerta
        tipo_alerta: Tipo de alerta (arma, incendio, etc.)
        objeto: Objeto detectado
        confianza: Nivel de confianza
        imagen_path: Ruta de la imagen de la alerta
    """
    if not ubicacion:
        return
    
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Si confianza >= 80%, enviar a servicios de emergencia automáticamente
    if confianza >= 0.80:
        if tipo_alerta == 'incendio':
            # Crear y enviar a bomberos
            crear_servicio_emergencia('bomberos', ubicacion)
            print(f"🚨 ALERTA CRÍTICA (Confianza: {confianza*100:.1f}%): Enviando a BOMBEROS - {ubicacion}")
        elif tipo_alerta == 'arma':
            # Crear y enviar a policía
            crear_servicio_emergencia('policia', ubicacion)
            print(f"🚨 ALERTA CRÍTICA (Confianza: {confianza*100:.1f}%): Enviando a POLICÍA - {ubicacion}")
    
    # Buscar destinatarios activos para esta ubicación (incluyendo servicios de emergencia recién creados)
    cur.execute("""
        SELECT * FROM destinatarios_alertas 
        WHERE ubicacion = ? AND activo = 1
    """, (ubicacion,))
    
    destinatarios = cur.fetchall()
    conn.close()
    
    if not destinatarios:
        print(f"[INFO] No hay destinatarios configurados para la ubicación: {ubicacion}")
        # Aunque no haya destinatarios, si se creó un servicio de emergencia, registrarlo en historial
        if confianza >= 0.80:
            # Buscar el servicio de emergencia recién creado
            conn = sqlite3.connect('alertas.db')
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            tipo_servicio = 'bomberos' if tipo_alerta == 'incendio' else 'policia'
            cur.execute("""
                SELECT * FROM destinatarios_alertas 
                WHERE ubicacion = ? AND nombre LIKE ? AND activo = 1
            """, (ubicacion, f'%{tipo_servicio}%'))
            servicio_emergencia = cur.fetchone()
            conn.close()
            
            if servicio_emergencia:
                # Registrar envío al servicio de emergencia
                conn = sqlite3.connect('alertas.db')
                cur = conn.cursor()
                cur.execute("SELECT id FROM alertas ORDER BY id DESC LIMIT 1")
                ultima_alerta = cur.fetchone()
                alerta_id = ultima_alerta[0] if ultima_alerta else None
                
                cur.execute("""
                    INSERT INTO historial_envios 
                    (alerta_id, destinatario_id, ubicacion, tipo_alerta, fecha_envio, estado)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    alerta_id,
                    servicio_emergencia['id'],
                    ubicacion,
                    tipo_alerta,
                    datetime.now().isoformat(),
                    'enviado'
                ))
                conn.commit()
                conn.close()
                print(f"[ALERTA ENVIADA] 🚨 SERVICIO DE EMERGENCIA {servicio_emergencia['nombre']} - {tipo_alerta.upper()} - Ubicación: {ubicacion}")
        return
    
    # Registrar envío de alertas (tabla de historial)
    conn = sqlite3.connect('alertas.db')
    cur = conn.cursor()
    
    # Obtener el ID de la última alerta guardada
    cur.execute("SELECT id FROM alertas ORDER BY id DESC LIMIT 1")
    ultima_alerta = cur.fetchone()
    alerta_id = ultima_alerta[0] if ultima_alerta else None
    
    # Registrar cada envío
    fecha_envio = datetime.now().isoformat()
    for destinatario in destinatarios:
        cur.execute("""
            INSERT INTO historial_envios 
            (alerta_id, destinatario_id, ubicacion, tipo_alerta, fecha_envio, estado)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            alerta_id,
            destinatario['id'],
            ubicacion,
            tipo_alerta,
            fecha_envio,
            'enviado'
        ))
        
        # Aquí se podría integrar envío por email/SMS
        servicio_emergencia = "🚨 SERVICIO DE EMERGENCIA" if "bomberos" in destinatario['nombre'].lower() or "policia" in destinatario['nombre'].lower() else ""
        print(f"[ALERTA ENVIADA] {servicio_emergencia} {destinatario['nombre']} ({destinatario.get('email', 'N/A')}) - {tipo_alerta.upper()} - Ubicación: {ubicacion}")
    
    conn.commit()
    conn.close()

# ------------------ RUTAS DE AUTENTICACIÓN ------------------ #

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        contraseña = request.form.get('contraseña', '')
        
        if not correo or not contraseña:
            flash('Por favor, completa todos los campos', 'danger')
            return render_template('login.html')
        
        conn = sqlite3.connect('usuarios.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE correo = ?", (correo,))
        usuario = cur.fetchone()
        conn.close()
        
        if usuario and check_password_hash(usuario['contraseña'], contraseña):
            session['user_id'] = usuario['id']
            session['user_email'] = usuario['correo']
            session['user_name'] = usuario['nombre']
            # Guardar rol en sesión (convertir Row a dict para usar .get())
            usuario_dict = dict(usuario)
            session['user_rol'] = usuario_dict.get('rol', 'usuario')
            flash(f'¡Bienvenido, {usuario["nombre"]}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """Página de registro de nuevos usuarios (solo para usuarios normales)"""
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        contraseña = request.form.get('contraseña', '')
        confirmar_contraseña = request.form.get('confirmar_contraseña', '')
        nombre = request.form.get('nombre', '').strip()
        rol = request.form.get('rol', 'usuario').strip()  # Por defecto 'usuario'
        
        # Validaciones
        if not correo or not contraseña or not nombre:
            flash('Por favor, completa todos los campos', 'danger')
            return render_template('registro.html')
        
        if contraseña != confirmar_contraseña:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('registro.html')
        
        if len(contraseña) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return render_template('registro.html')
        
        # Solo admins pueden crear usuarios con rol admin
        if rol == 'admin' and session.get('user_rol') != 'admin':
            flash('No tienes permisos para crear usuarios administradores', 'danger')
            return render_template('registro.html')
        
        # Verificar si el correo ya existe
        conn = sqlite3.connect('usuarios.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE correo = ?", (correo,))
        if cur.fetchone():
            conn.close()
            flash('Este correo ya está registrado', 'danger')
            return render_template('registro.html')
        
        # Crear nuevo usuario
        password_hash = generate_password_hash(contraseña)
        cur.execute("""
            INSERT INTO usuarios (correo, contraseña, nombre, fecha_registro, rol)
            VALUES (?, ?, ?, ?, ?)
        """, (correo, password_hash, nombre, datetime.now().isoformat(), rol))
        conn.commit()
        conn.close()
        
        flash('¡Registro exitoso! Por favor, inicia sesión', 'success')
        return redirect(url_for('login'))
    
    # Si está logueado como admin, puede elegir rol, si no, solo usuario
    es_admin = session.get('user_rol') == 'admin'
    return render_template('registro.html', es_admin=es_admin)

@app.route('/usuarios/gestionar', methods=['GET', 'POST'])
@admin_required
def gestionar_usuarios():
    """Página para que los admins gestionen usuarios"""
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        if accion == 'crear':
            correo = request.form.get('correo', '').strip()
            contraseña = request.form.get('contraseña', '')
            nombre = request.form.get('nombre', '').strip()
            rol = request.form.get('rol', 'usuario').strip()
            
            if not correo or not contraseña or not nombre:
                flash('Por favor, completa todos los campos', 'danger')
            else:
                # Verificar si el correo ya existe
                cur.execute("SELECT id FROM usuarios WHERE correo = ?", (correo,))
                if cur.fetchone():
                    flash('Este correo ya está registrado', 'danger')
                else:
                    password_hash = generate_password_hash(contraseña)
                    cur.execute("""
                        INSERT INTO usuarios (correo, contraseña, nombre, fecha_registro, rol)
                        VALUES (?, ?, ?, ?, ?)
                    """, (correo, password_hash, nombre, datetime.now().isoformat(), rol))
                    conn.commit()
                    flash(f'Usuario {nombre} creado exitosamente', 'success')
        
        elif accion == 'eliminar':
            usuario_id = request.form.get('usuario_id')
            if usuario_id and int(usuario_id) != session['user_id']:
                cur.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
                conn.commit()
                flash('Usuario eliminado exitosamente', 'success')
            else:
                flash('No puedes eliminar tu propio usuario', 'danger')
        
        elif accion == 'cambiar_rol':
            usuario_id = request.form.get('usuario_id')
            nuevo_rol = request.form.get('nuevo_rol', 'usuario')
            if usuario_id and int(usuario_id) != session['user_id']:
                cur.execute("UPDATE usuarios SET rol = ? WHERE id = ?", (nuevo_rol, usuario_id))
                conn.commit()
                flash('Rol actualizado exitosamente', 'success')
            else:
                flash('No puedes cambiar tu propio rol', 'danger')
    
    # Obtener todos los usuarios
    cur.execute("SELECT * FROM usuarios ORDER BY fecha_registro DESC")
    usuarios = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    return render_template('gestionar_usuarios.html', usuarios=usuarios)

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

@app.route('/perfil')
@login_required
def perfil():
    """Perfil del usuario autorizado"""
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Obtener información del usuario
    cur.execute("SELECT * FROM usuarios WHERE id = ?", (session['user_id'],))
    usuario = dict(cur.fetchone())
    
    # Estadísticas del usuario (alertas procesadas, etc.)
    conn_alertas = sqlite3.connect('alertas.db')
    conn_alertas.row_factory = sqlite3.Row
    cur_alertas = conn_alertas.cursor()
    
    # Total de alertas en el sistema
    cur_alertas.execute("SELECT COUNT(*) as total FROM alertas")
    total_alertas_sistema = cur_alertas.fetchone()['total']
    
    # Alertas de las últimas 24 horas
    hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    cur_alertas.execute("SELECT COUNT(*) as total FROM alertas WHERE fecha_hora >= ?", (hace_24h,))
    alertas_24h = cur_alertas.fetchone()['total']
    
    # Alertas críticas
    cur_alertas.execute("""
        SELECT COUNT(*) as total 
        FROM alertas 
        WHERE fecha_hora >= ? 
        AND (confianza >= 0.50 OR (confianza IS NULL AND tipo IN ('arma', 'incendio', 'agresion')))
    """, (hace_24h,))
    alertas_criticas_24h = cur_alertas.fetchone()['total']
    
    # Reportes del usuario
    cur_alertas.execute("""
        SELECT * FROM reportes_usuarios 
        WHERE usuario_id = ? 
        ORDER BY fecha_hora DESC 
        LIMIT 10
    """, (session['user_id'],))
    reportes = [dict(row) for row in cur_alertas.fetchall()]
    
    cur_alertas.execute("SELECT COUNT(*) as total FROM reportes_usuarios WHERE usuario_id = ?", (session['user_id'],))
    total_reportes = cur_alertas.fetchone()['total']
    
    conn_alertas.close()
    conn.close()
    
    return render_template('perfil.html',
                         usuario=usuario,
                         total_alertas_sistema=total_alertas_sistema,
                         alertas_24h=alertas_24h,
                         alertas_criticas_24h=alertas_criticas_24h,
                         reportes=reportes,
                         total_reportes=total_reportes)

@app.route('/perfil/cambiar-contraseña', methods=['POST'])
@login_required
def cambiar_contraseña():
    """Cambiar contraseña del usuario"""
    contraseña_actual = request.form.get('contraseña_actual', '')
    nueva_contraseña = request.form.get('nueva_contraseña', '')
    confirmar_contraseña = request.form.get('confirmar_contraseña', '')
    
    if not contraseña_actual or not nueva_contraseña or not confirmar_contraseña:
        flash('Por favor, completa todos los campos', 'danger')
        return redirect(url_for('perfil'))
    
    if nueva_contraseña != confirmar_contraseña:
        flash('Las nuevas contraseñas no coinciden', 'danger')
        return redirect(url_for('perfil'))
    
    if len(nueva_contraseña) < 6:
        flash('La nueva contraseña debe tener al menos 6 caracteres', 'danger')
        return redirect(url_for('perfil'))
    
    # Verificar contraseña actual
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT contraseña FROM usuarios WHERE id = ?", (session['user_id'],))
    usuario = cur.fetchone()
    
    if not usuario or not check_password_hash(usuario['contraseña'], contraseña_actual):
        conn.close()
        flash('La contraseña actual es incorrecta', 'danger')
        return redirect(url_for('perfil'))
    
    # Actualizar contraseña
    nueva_contraseña_hash = generate_password_hash(nueva_contraseña)
    cur.execute("UPDATE usuarios SET contraseña = ? WHERE id = ?", 
                (nueva_contraseña_hash, session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Contraseña actualizada exitosamente', 'success')
    return redirect(url_for('perfil'))

# ------------------ RUTAS ------------------ #

@app.route('/')
def index():
    """Página principal del portal"""
    # Si el usuario está autenticado, redirigir según su rol
    if 'user_id' in session:
        if session.get('user_rol') == 'admin':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('usuario_alertas'))
    # Si no está autenticado, redirigir al login
    return redirect(url_for('login'))

@app.route('/usuario/alertas')
@login_required
def usuario_alertas():
    """Vista simplificada para usuarios normales: solo alertas graves con ubicación"""
    # Solo usuarios normales pueden acceder (no admins)
    if session.get('user_rol') == 'admin':
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Solo alertas MUY GRAVES (confianza >= 80%) de las últimas 24 horas con ubicación
    hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    
    cur.execute("""
        SELECT tipo, ubicacion, fecha_hora
        FROM alertas 
        WHERE fecha_hora >= ?
        AND (
            confianza >= 0.80
            OR (confianza IS NULL AND tipo IN ('arma', 'incendio', 'agresion'))
        )
        AND ubicacion IS NOT NULL
        AND ubicacion != ''
        ORDER BY id DESC 
        LIMIT 50
    """, (hace_24h,))
    
    alertas_raw = cur.fetchall()
    alertas_lista = [dict(row) for row in alertas_raw]
    
    cur.execute("""
        SELECT COUNT(*) as total 
        FROM alertas 
        WHERE fecha_hora >= ?
        AND (
            confianza >= 0.80
            OR (confianza IS NULL AND tipo IN ('arma', 'incendio', 'agresion'))
        )
        AND ubicacion IS NOT NULL
        AND ubicacion != ''
    """, (hace_24h,))
    total_criticas = cur.fetchone()['total']
    
    conn.close()
    
    return render_template('usuario_alertas.html', 
                         alertas=alertas_lista, 
                         total_criticas=total_criticas)

@app.route('/usuario/mapa')
@login_required
def usuario_mapa():
    """Mapa simplificado para usuarios normales (solo visualización)"""
    # Solo usuarios normales pueden acceder (no admins)
    if session.get('user_rol') == 'admin':
        return redirect(url_for('mapa_vigilancia'))
    
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Solo alertas graves con ubicación y coordenadas (si las hay)
    hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    
    cur.execute("""
        SELECT tipo, ubicacion, fecha_hora
        FROM alertas 
        WHERE fecha_hora >= ?
        AND (
            confianza >= 0.80
            OR (confianza IS NULL AND tipo IN ('arma', 'incendio', 'agresion'))
        )
        AND ubicacion IS NOT NULL
        AND ubicacion != ''
        ORDER BY id DESC 
        LIMIT 30
    """, (hace_24h,))
    
    alertas_graves = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    return render_template('usuario_mapa.html', alertas=alertas_graves)

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal con estadísticas y alertas recientes (SOLO ADMIN)"""
    # Solo admins pueden acceder al dashboard completo
    if session.get('user_rol') != 'admin':
        return redirect(url_for('usuario_alertas'))
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Estadísticas generales
    cur.execute("SELECT COUNT(*) as total FROM alertas")
    total_alertas = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM alertas WHERE tipo = 'arma'")
    total_armas = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM alertas WHERE tipo = 'incendio'")
    total_incendios = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM alertas WHERE tipo = 'agresion'")
    total_agresiones = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM alertas WHERE tipo = 'vehiculo'")
    total_vehiculos = cur.fetchone()['total']
    
    # Alertas de las últimas 24 horas clasificadas por nivel de confianza
    hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    
    # Total de alertas en las últimas 24 horas
    cur.execute("""
        SELECT COUNT(*) as total 
        FROM alertas 
        WHERE fecha_hora >= ?
    """, (hace_24h,))
    alertas_24h = cur.fetchone()['total']
    
    # Alertas CRÍTICAS (confianza >= 50% o tipo crítico con confianza NULL) de las últimas 24 horas
    cur.execute("""
        SELECT COUNT(*) as total
        FROM alertas
        WHERE fecha_hora >= ?
        AND (
            confianza >= 0.50
            OR (confianza IS NULL AND tipo IN ('arma', 'incendio', 'agresion'))
        )
    """, (hace_24h,))
    alertas_criticas_24h = cur.fetchone()['total']
    
    # Alertas INTERMEDIAS (confianza >= 20% y < 50%) de las últimas 24 horas
    cur.execute("""
        SELECT COUNT(*) as total 
        FROM alertas 
        WHERE fecha_hora >= ? 
        AND confianza IS NOT NULL 
        AND confianza >= 0.20 
        AND confianza < 0.50
    """, (hace_24h,))
    alertas_intermedias_24h = cur.fetchone()['total']
    
    # Alertas BAJAS (confianza < 20%) de las últimas 24 horas
    cur.execute("""
        SELECT COUNT(*) as total 
        FROM alertas 
        WHERE fecha_hora >= ? 
        AND confianza IS NOT NULL 
        AND confianza < 0.20
    """, (hace_24h,))
    alertas_bajas_24h = cur.fetchone()['total']
    
    # Alertas recientes (últimas 10)
    cur.execute("""
        SELECT * FROM alertas 
        ORDER BY id DESC 
        LIMIT 10
    """)
    alertas_raw = cur.fetchall()
    # Asegurar que confianza no sea None
    alertas_recientes = []
    for row in alertas_raw:
        alerta_dict = dict(row)
        if alerta_dict.get('confianza') is None:
            alerta_dict['confianza'] = 0.0
        alertas_recientes.append(alerta_dict)
    
    # Gráfico de alertas por día (últimos 7 días)
    cur.execute("""
        SELECT DATE(fecha_hora) as fecha, COUNT(*) as cantidad
        FROM alertas
        WHERE fecha_hora >= datetime('now', '-7 days')
        GROUP BY DATE(fecha_hora)
        ORDER BY fecha
    """)
    alertas_por_dia = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    return render_template('dashboard.html',
                         total_alertas=total_alertas,
                         total_armas=total_armas,
                         total_incendios=total_incendios,
                         total_agresiones=total_agresiones,
                         total_vehiculos=total_vehiculos,
                         alertas_24h=alertas_24h,
                         alertas_criticas_24h=alertas_criticas_24h,
                         alertas_intermedias_24h=alertas_intermedias_24h,
                         alertas_bajas_24h=alertas_bajas_24h,
                         alertas_recientes=alertas_recientes,
                         alertas_por_dia=alertas_por_dia)

@app.route('/analizar', methods=['GET', 'POST'])
@admin_required
def analizar():
    """Página para subir y analizar imágenes"""
    if request.method == 'POST':
        if 'imagen' not in request.files:
            return jsonify({'error': 'No se proporcionó ninguna imagen'}), 400
        
        file = request.files['imagen']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
            filename = timestamp + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Obtener ubicación del formulario
            ubicacion = request.form.get('ubicacion', 'Ubicación no especificada').strip()
            
            # Analizar imagen
            try:
                detectar_amenazas(filepath, generar_imagen_anotada=True, ubicacion=ubicacion)
                
                # Obtener las alertas generadas para esta imagen
                conn = sqlite3.connect('alertas.db')
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("""
                    SELECT * FROM alertas 
                    WHERE imagen LIKE ? 
                    ORDER BY id DESC 
                    LIMIT 5
                """, (f'%{filename}%',))
                alertas = cur.fetchall()
                conn.close()
                
                if alertas:
                    # Retornar todas las alertas encontradas
                    return jsonify({
                        'success': True,
                        'alertas': [dict(a) for a in alertas],
                        'imagen': filename,
                        'total': len(alertas)
                    })
                else:
                    return jsonify({
                        'success': True,
                        'mensaje': 'Imagen analizada: No se detectaron amenazas',
                        'imagen': filename,
                        'alertas': []
                    })
            except Exception as e:
                import traceback
                return jsonify({'error': f'Error al analizar imagen: {str(e)}', 'traceback': traceback.format_exc()}), 500
    
    return render_template('analizar.html')

@app.route('/alertas')
@admin_required
def alertas():
    """Página con lista completa de alertas"""
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Filtros
    tipo_filtro = request.args.get('tipo', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    
    query = "SELECT * FROM alertas WHERE 1=1"
    params = []
    
    if tipo_filtro:
        query += " AND tipo = ?"
        params.append(tipo_filtro)
    
    if fecha_desde:
        query += " AND fecha_hora >= ?"
        params.append(fecha_desde)
    
    if fecha_hasta:
        query += " AND fecha_hora <= ?"
        params.append(fecha_hasta)
    
    query += " ORDER BY id DESC LIMIT 100"
    
    cur.execute(query, params)
    alertas_raw = cur.fetchall()
    
    # Convertir a diccionarios y asegurar que valores numéricos no sean None
    alertas_lista = []
    for row in alertas_raw:
        alerta_dict = dict(row)
        # Asegurar que confianza tenga un valor válido
        if alerta_dict.get('confianza') is None:
            alerta_dict['confianza'] = 0.0
        # Asegurar que coordenadas sean números o None explícito
        for coord in ['x1', 'y1', 'x2', 'y2']:
            if alerta_dict.get(coord) is not None:
                try:
                    alerta_dict[coord] = float(alerta_dict[coord])
                except (ValueError, TypeError):
                    alerta_dict[coord] = None
        alertas_lista.append(alerta_dict)
    
    conn.close()
    
    return render_template('alertas.html', alertas=alertas_lista, tipo_filtro=tipo_filtro)

@app.route('/alertas-publicas')
def alertas_publicas():
    """Página pública para que la población vea alertas sin login - Solo alertas muy graves"""
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Solo mostrar alertas MUY GRAVES (confianza >= 80%) de las últimas 24 horas
    hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    
    cur.execute("""
        SELECT tipo, ubicacion, fecha_hora
        FROM alertas 
        WHERE fecha_hora >= ?
        AND (
            confianza >= 0.80
            OR (confianza IS NULL AND tipo IN ('arma', 'incendio', 'agresion'))
        )
        AND ubicacion IS NOT NULL
        AND ubicacion != ''
        ORDER BY id DESC 
        LIMIT 30
    """, (hace_24h,))
    
    alertas_raw = cur.fetchall()
    
    # Convertir a diccionarios simplificados (solo tipo, ubicación, fecha)
    alertas_lista = []
    for row in alertas_raw:
        alerta_dict = {
            'tipo': row['tipo'],
            'ubicacion': row['ubicacion'],
            'fecha_hora': row['fecha_hora']
        }
        alertas_lista.append(alerta_dict)
    
    # Estadísticas públicas (solo alertas muy graves)
    cur.execute("""
        SELECT COUNT(*) as total 
        FROM alertas 
        WHERE fecha_hora >= ?
        AND (
            confianza >= 0.80
            OR (confianza IS NULL AND tipo IN ('arma', 'incendio', 'agresion'))
        )
        AND ubicacion IS NOT NULL
        AND ubicacion != ''
    """, (hace_24h,))
    total_criticas = cur.fetchone()['total']
    
    conn.close()
    
    return render_template('alertas_publicas.html', 
                         alertas=alertas_lista, 
                         total_criticas=total_criticas)

@app.route('/api/alertas')
def api_alertas():
    """API para obtener alertas en formato JSON"""
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    limit = request.args.get('limit', 50, type=int)
    tipo = request.args.get('tipo', '')
    
    query = "SELECT * FROM alertas WHERE 1=1"
    params = []
    
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
    
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    
    cur.execute(query, params)
    alertas_raw = cur.fetchall()
    # Asegurar que confianza no sea None
    alertas = []
    for row in alertas_raw:
        alerta_dict = dict(row)
        if alerta_dict.get('confianza') is None:
            alerta_dict['confianza'] = 0.0
        alertas.append(alerta_dict)
    conn.close()
    
    return jsonify(alertas)

@app.route('/api/estadisticas')
def api_estadisticas():
    """API para obtener estadísticas"""
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Total por tipo
    cur.execute("""
        SELECT tipo, COUNT(*) as cantidad 
        FROM alertas 
        GROUP BY tipo
    """)
    por_tipo = {row['tipo']: row['cantidad'] for row in cur.fetchall()}
    
    # Alertas últimas 24 horas
    hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
    cur.execute("""
        SELECT COUNT(*) as total 
        FROM alertas 
        WHERE fecha_hora >= ?
    """, (hace_24h,))
    ultimas_24h = cur.fetchone()['total']
    
    conn.close()
    
    return jsonify({
        'por_tipo': por_tipo,
        'ultimas_24h': ultimas_24h
    })

@app.route('/configurar_alertas', methods=['GET', 'POST'])
@admin_required
def configurar_alertas():
    """Página para configurar destinatarios de alertas por ubicación"""
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        if accion == 'agregar':
            ubicacion = request.form.get('ubicacion', '').strip()
            nombre = request.form.get('nombre', '').strip()
            email = request.form.get('email', '').strip()
            telefono = request.form.get('telefono', '').strip()
            
            if not ubicacion or not nombre:
                flash('Ubicación y nombre son obligatorios', 'danger')
                return redirect(url_for('configurar_alertas'))
            
            conn = sqlite3.connect('alertas.db')
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO destinatarios_alertas (ubicacion, nombre, email, telefono, fecha_creacion)
                VALUES (?, ?, ?, ?, ?)
            """, (ubicacion, nombre, email or None, telefono or None, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            
            flash(f'Destinatario {nombre} agregado para {ubicacion}', 'success')
            
        elif accion == 'eliminar':
            destinatario_id = request.form.get('id')
            if destinatario_id:
                conn = sqlite3.connect('alertas.db')
                cur = conn.cursor()
                cur.execute("DELETE FROM destinatarios_alertas WHERE id = ?", (destinatario_id,))
                conn.commit()
                conn.close()
                flash('Destinatario eliminado', 'success')
        
        elif accion == 'toggle':
            destinatario_id = request.form.get('id')
            if destinatario_id:
                conn = sqlite3.connect('alertas.db')
                cur = conn.cursor()
                cur.execute("SELECT activo FROM destinatarios_alertas WHERE id = ?", (destinatario_id,))
                resultado = cur.fetchone()
                if resultado:
                    nuevo_estado = 0 if resultado[0] == 1 else 1
                    cur.execute("UPDATE destinatarios_alertas SET activo = ? WHERE id = ?", 
                              (nuevo_estado, destinatario_id))
                    conn.commit()
                conn.close()
                flash('Estado actualizado', 'success')
        
        return redirect(url_for('configurar_alertas'))
    
    # Obtener todos los destinatarios
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM destinatarios_alertas ORDER BY ubicacion, nombre")
    destinatarios = cur.fetchall()
    
    # Obtener servicios de emergencia separadamente para debug
    cur.execute("""
        SELECT * FROM destinatarios_alertas 
        WHERE nombre LIKE '%bomberos%' OR nombre LIKE '%policia%' OR nombre LIKE '%Bomberos%' OR nombre LIKE '%Policia%'
        ORDER BY fecha_creacion DESC
    """)
    servicios_emergencia = cur.fetchall()
    
    # Obtener ubicaciones únicas
    cur.execute("SELECT DISTINCT ubicacion FROM alertas WHERE ubicacion IS NOT NULL ORDER BY ubicacion")
    ubicaciones_existentes = [row[0] for row in cur.fetchall()]
    
    # Obtener historial de envíos recientes (si la tabla existe)
    try:
        cur.execute("""
            SELECT h.*, d.nombre as destinatario_nombre, d.email
            FROM historial_envios h
            LEFT JOIN destinatarios_alertas d ON h.destinatario_id = d.id
            ORDER BY h.fecha_envio DESC
            LIMIT 20
        """)
        historial = cur.fetchall()
    except sqlite3.OperationalError:
        # Si la tabla no existe aún, retornar lista vacía
        historial = []
    
    conn.close()
    
    return render_template('configurar_alertas.html',
                         destinatarios=destinatarios,
                         ubicaciones_existentes=ubicaciones_existentes,
                         historial=historial,
                         servicios_emergencia=servicios_emergencia)

@app.route('/imagen/<path:filename>')
def imagen(filename):
    """Servir imágenes subidas"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/imagen_anotada/<path:filename>')
def imagen_anotada(filename):
    """Servir imágenes anotadas"""
    # Buscar en diferentes ubicaciones posibles
    posibles_rutas = [
        os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.jpg', '_anotada.jpg').replace('.png', '_anotada.jpg')),
        os.path.join('alertas_frames', filename),
        filename
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return send_file(ruta)
    
    return "Imagen no encontrada", 404

@app.route('/patrullas')
@admin_required
def patrullas():
    """Panel de patrullas en El Salvador"""
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Obtener todas las patrullas
    cur.execute("""
        SELECT * FROM patrullas 
        ORDER BY departamento, municipio, numero_patrulla
    """)
    patrullas_lista = [dict(row) for row in cur.fetchall()]
    
    # Estadísticas
    cur.execute("SELECT COUNT(*) as total FROM patrullas")
    total_patrullas = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM patrullas WHERE estado = 'activa'")
    patrullas_activas = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM patrullas WHERE estado = 'disponible'")
    patrullas_disponibles = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM patrullas WHERE estado = 'en_ruta'")
    patrullas_en_ruta = cur.fetchone()['total']
    
    # Patrullas por departamento
    cur.execute("""
        SELECT departamento, COUNT(*) as cantidad
        FROM patrullas
        GROUP BY departamento
        ORDER BY cantidad DESC
    """)
    patrullas_por_departamento = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    return render_template('patrullas.html',
                         patrullas=patrullas_lista,
                         total_patrullas=total_patrullas,
                         patrullas_activas=patrullas_activas,
                         patrullas_disponibles=patrullas_disponibles,
                         patrullas_en_ruta=patrullas_en_ruta,
                         patrullas_por_departamento=patrullas_por_departamento)

@app.route('/mapa-vigilancia')
@admin_required
def mapa_vigilancia():
    """Mapa de zonas con menos patrullas o vigilancia"""
    conn = sqlite3.connect('alertas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Obtener todas las patrullas con coordenadas
    cur.execute("""
        SELECT zona, municipio, departamento, latitud, longitud, estado, COUNT(*) as cantidad_patrullas
        FROM patrullas
        WHERE latitud IS NOT NULL AND longitud IS NOT NULL
        GROUP BY zona, municipio, departamento, latitud, longitud
    """)
    zonas_con_patrullas = [dict(row) for row in cur.fetchall()]
    
    # Contar patrullas activas por zona
    cur.execute("""
        SELECT zona, municipio, departamento, 
               COUNT(*) as total_patrullas,
               SUM(CASE WHEN estado = 'activa' THEN 1 ELSE 0 END) as patrullas_activas,
               SUM(CASE WHEN estado = 'disponible' THEN 1 ELSE 0 END) as patrullas_disponibles,
               SUM(CASE WHEN estado = 'en_ruta' THEN 1 ELSE 0 END) as patrullas_en_ruta
        FROM patrullas
        GROUP BY zona, municipio, departamento
        ORDER BY patrullas_activas ASC, total_patrullas ASC
    """)
    zonas_analisis = [dict(row) for row in cur.fetchall()]
    
    # Identificar zonas con menos vigilancia (menos de 2 patrullas activas)
    zonas_baja_vigilancia = []
    for zona in zonas_analisis:
        if zona['patrullas_activas'] < 2 or zona['total_patrullas'] < 2:
            # Buscar coordenadas promedio de la zona
            cur.execute("""
                SELECT AVG(latitud) as lat_promedio, AVG(longitud) as lon_promedio
                FROM patrullas
                WHERE zona = ? AND municipio = ? AND departamento = ?
                AND latitud IS NOT NULL AND longitud IS NOT NULL
            """, (zona['zona'], zona['municipio'], zona['departamento']))
            coords = cur.fetchone()
            
            if coords and coords['lat_promedio']:
                zona_info = {
                    'zona': zona['zona'],
                    'municipio': zona['municipio'],
                    'departamento': zona['departamento'],
                    'total_patrullas': zona['total_patrullas'],
                    'patrullas_activas': zona['patrullas_activas'],
                    'patrullas_disponibles': zona['patrullas_disponibles'],
                    'patrullas_en_ruta': zona['patrullas_en_ruta'],
                    'latitud': coords['lat_promedio'],
                    'longitud': coords['lon_promedio'],
                    'nivel_riesgo': 'alto' if zona['patrullas_activas'] == 0 else 'medio'
                }
                zonas_baja_vigilancia.append(zona_info)
    
    # Obtener todas las patrullas para mostrar en el mapa
    cur.execute("""
        SELECT numero_patrulla, zona, municipio, departamento, 
               latitud, longitud, estado, oficial_encargado
        FROM patrullas
        WHERE latitud IS NOT NULL AND longitud IS NOT NULL
    """)
    todas_patrullas = [dict(row) for row in cur.fetchall()]
    
    # Estadísticas generales
    cur.execute("SELECT COUNT(DISTINCT zona || municipio || departamento) as total_zonas FROM patrullas")
    total_zonas = cur.fetchone()['total_zonas']
    
    conn.close()
    
    return render_template('mapa_vigilancia.html',
                         zonas_baja_vigilancia=zonas_baja_vigilancia,
                         todas_patrullas=todas_patrullas,
                         total_zonas=total_zonas)

# ------------------ RUTAS PARA POBLACIÓN ------------------ #

@app.route('/poblacion/registro', methods=['GET', 'POST'])
def poblacion_registro():
    """Registro de usuarios de la población"""
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        contraseña = request.form.get('contraseña', '')
        confirmar_contraseña = request.form.get('confirmar_contraseña', '')
        nombre = request.form.get('nombre', '').strip()
        telefono = request.form.get('telefono', '').strip()
        
        # Validaciones
        if not correo or not contraseña or not nombre:
            flash('Por favor, completa todos los campos obligatorios', 'danger')
            return render_template('poblacion_registro.html')
        
        if contraseña != confirmar_contraseña:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('poblacion_registro.html')
        
        if len(contraseña) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return render_template('poblacion_registro.html')
        
        # Verificar si el correo ya existe
        conn = sqlite3.connect('poblacion.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios_poblacion WHERE correo = ?", (correo,))
        if cur.fetchone():
            conn.close()
            flash('Este correo ya está registrado', 'danger')
            return render_template('poblacion_registro.html')
        
        # Crear nuevo usuario
        password_hash = generate_password_hash(contraseña)
        cur.execute("""
            INSERT INTO usuarios_poblacion (correo, contraseña, nombre, telefono, fecha_registro)
            VALUES (?, ?, ?, ?, ?)
        """, (correo, password_hash, nombre, telefono or None, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        flash('¡Registro exitoso! Por favor, inicia sesión', 'success')
        return redirect(url_for('poblacion_login'))
    
    return render_template('poblacion_registro.html')

@app.route('/poblacion/login', methods=['GET', 'POST'])
def poblacion_login():
    """Login de usuarios de la población"""
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        contraseña = request.form.get('contraseña', '')
        
        if not correo or not contraseña:
            flash('Por favor, completa todos los campos', 'danger')
            return render_template('poblacion_login.html')
        
        conn = sqlite3.connect('poblacion.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios_poblacion WHERE correo = ?", (correo,))
        usuario = cur.fetchone()
        
        if usuario and check_password_hash(usuario['contraseña'], contraseña):
            # Actualizar última sesión
            cur.execute("""
                UPDATE usuarios_poblacion 
                SET ultima_sesion = ? 
                WHERE id = ?
            """, (datetime.now().isoformat(), usuario['id']))
            conn.commit()
            conn.close()
            
            # Guardar en sesión
            session['poblacion_user_id'] = usuario['id']
            session['poblacion_user_name'] = usuario['nombre']
            session['poblacion_user_email'] = usuario['correo']
            
            flash(f'¡Bienvenido, {usuario["nombre"]}!', 'success')
            return redirect(url_for('poblacion_perfil'))
        else:
            conn.close()
            flash('Correo o contraseña incorrectos', 'danger')
    
    return render_template('poblacion_login.html')

@app.route('/poblacion/logout')
def poblacion_logout():
    """Cerrar sesión de población"""
    session.pop('poblacion_user_id', None)
    session.pop('poblacion_user_name', None)
    session.pop('poblacion_user_email', None)
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('poblacion_login'))

@app.route('/poblacion/perfil')
@poblacion_login_required
def poblacion_perfil():
    """Perfil del usuario de la población"""
    conn = sqlite3.connect('poblacion.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Obtener información del usuario
    cur.execute("SELECT * FROM usuarios_poblacion WHERE id = ?", (session['poblacion_user_id'],))
    usuario = dict(cur.fetchone())
    
    # Obtener reportes del usuario
    cur.execute("""
        SELECT * FROM reportes_poblacion 
        WHERE usuario_id = ? 
        ORDER BY fecha_hora DESC 
        LIMIT 20
    """, (session['poblacion_user_id'],))
    reportes = [dict(row) for row in cur.fetchall()]
    
    # Estadísticas
    cur.execute("SELECT COUNT(*) as total FROM reportes_poblacion WHERE usuario_id = ?", (session['poblacion_user_id'],))
    total_reportes = cur.fetchone()['total']
    
    cur.execute("""
        SELECT COUNT(*) as total 
        FROM reportes_poblacion 
        WHERE usuario_id = ? AND estado = 'pendiente'
    """, (session['poblacion_user_id'],))
    reportes_pendientes = cur.fetchone()['total']
    
    conn.close()
    
    return render_template('poblacion_perfil.html',
                         usuario=usuario,
                         reportes=reportes,
                         total_reportes=total_reportes,
                         reportes_pendientes=reportes_pendientes)

@app.route('/poblacion/reportar', methods=['GET', 'POST'])
@poblacion_login_required
def poblacion_reportar():
    """Página para reportar con cámara en tiempo real"""
    if request.method == 'POST':
        # Recibir imagen en base64 desde la cámara
        imagen_base64 = request.form.get('imagen', '')
        descripcion = request.form.get('descripcion', '').strip()
        ubicacion = request.form.get('ubicacion', '').strip()
        tipo_reporte = request.form.get('tipo_reporte', 'general')
        
        if not imagen_base64:
            flash('No se capturó ninguna imagen', 'danger')
            return redirect(url_for('poblacion_reportar'))
        
        # Guardar imagen
        try:
            import base64
            # Decodificar imagen base64
            imagen_data = base64.b64decode(imagen_base64.split(',')[1])
            
            # Crear carpeta si no existe
            os.makedirs('reportes_poblacion', exist_ok=True)
            
            # Guardar imagen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reporte_{session['poblacion_user_id']}_{timestamp}.jpg"
            ruta_imagen = os.path.join('reportes_poblacion', filename)
            
            with open(ruta_imagen, 'wb') as f:
                f.write(imagen_data)
            
            # Guardar reporte en BD
            conn = sqlite3.connect('poblacion.db')
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO reportes_poblacion 
                (usuario_id, imagen, descripcion, ubicacion, tipo_reporte, fecha_hora, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['poblacion_user_id'], filename, descripcion or None, 
                  ubicacion or None, tipo_reporte, datetime.now().isoformat(), 'pendiente'))
            conn.commit()
            conn.close()
            
            flash('¡Reporte enviado exitosamente!', 'success')
            return redirect(url_for('poblacion_perfil'))
            
        except Exception as e:
            flash(f'Error al guardar el reporte: {str(e)}', 'danger')
            return redirect(url_for('poblacion_reportar'))
    
    return render_template('poblacion_reportar.html')

@app.route('/poblacion/imagen/<filename>')
@poblacion_login_required
def poblacion_imagen(filename):
    """Servir imágenes de reportes de población"""
    ruta = os.path.join('reportes_poblacion', filename)
    if os.path.exists(ruta):
        return send_file(ruta)
    return "Imagen no encontrada", 404

@app.route('/usuario/reportar', methods=['GET', 'POST'])
@login_required
def usuario_reportar():
    """Página para que usuarios autorizados reporten con cámara en tiempo real"""
    if request.method == 'POST':
        # Recibir imagen en base64 desde la cámara
        imagen_base64 = request.form.get('imagen', '')
        descripcion = request.form.get('descripcion', '').strip()
        ubicacion = request.form.get('ubicacion', '').strip()
        tipo_reporte = request.form.get('tipo_reporte', 'general')
        
        if not imagen_base64:
            flash('No se capturó ninguna imagen', 'danger')
            return redirect(url_for('usuario_reportar'))
        
        # Guardar imagen
        try:
            import base64
            # Decodificar imagen base64
            imagen_data = base64.b64decode(imagen_base64.split(',')[1])
            
            # Crear carpeta si no existe
            os.makedirs('reportes_usuarios', exist_ok=True)
            
            # Guardar imagen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reporte_{session['user_id']}_{timestamp}.jpg"
            ruta_imagen = os.path.join('reportes_usuarios', filename)
            
            with open(ruta_imagen, 'wb') as f:
                f.write(imagen_data)
            
            # Guardar reporte en BD
            conn = sqlite3.connect('alertas.db')
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO reportes_usuarios 
                (usuario_id, imagen, descripcion, ubicacion, tipo_reporte, fecha_hora, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], filename, descripcion or None, 
                  ubicacion or None, tipo_reporte, datetime.now().isoformat(), 'pendiente'))
            conn.commit()
            conn.close()
            
            # Analizar automáticamente con IA
            try:
                import analizador
                print(f"\n[ANÁLISIS AUTOMÁTICO] Analizando reporte: {filename}")
                detecciones = analizador.detectar_amenazas(ruta_imagen, ubicacion=ubicacion or "Ubicación no especificada")
                
                if detecciones:
                    print(f"[ANÁLISIS AUTOMÁTICO] ⚠️ Se detectaron {len(detecciones)} amenaza(s) en el reporte")
                    # Actualizar estado del reporte a "en_revision" si hay amenazas
                    conn = sqlite3.connect('alertas.db')
                    cur = conn.cursor()
                    cur.execute("UPDATE reportes_usuarios SET estado = 'en_revision' WHERE imagen = ?", (filename,))
                    conn.commit()
                    conn.close()
                else:
                    print(f"[ANÁLISIS AUTOMÁTICO] ✅ No se detectaron amenazas en el reporte")
            except Exception as e:
                print(f"[ANÁLISIS AUTOMÁTICO] Error al analizar reporte: {str(e)}")
                # No fallar el reporte si el análisis falla
            
            flash('¡Reporte enviado exitosamente! La imagen está siendo analizada automáticamente.', 'success')
            return redirect(url_for('perfil'))
            
        except Exception as e:
            flash(f'Error al guardar el reporte: {str(e)}', 'danger')
            return redirect(url_for('usuario_reportar'))
    
    return render_template('usuario_reportar.html')

@app.route('/usuario/imagen/<filename>')
@login_required
def usuario_imagen(filename):
    """Servir imágenes de reportes de usuarios autorizados"""
    ruta = os.path.join('reportes_usuarios', filename)
    if os.path.exists(ruta):
        return send_file(ruta)
    return "Imagen no encontrada", 404

@app.route('/admin/reportes')
@admin_required
def admin_reportes():
    """Página para que administradores vean todos los reportes de usuarios"""
    # Obtener reportes de alertas.db
    conn_alertas = sqlite3.connect('alertas.db')
    conn_alertas.row_factory = sqlite3.Row
    cur_alertas = conn_alertas.cursor()
    
    # Obtener todos los reportes
    cur_alertas.execute("SELECT * FROM reportes_usuarios ORDER BY fecha_hora DESC")
    reportes_raw = [dict(row) for row in cur_alertas.fetchall()]
    
    # Estadísticas
    cur_alertas.execute("SELECT COUNT(*) as total FROM reportes_usuarios")
    total_reportes = cur_alertas.fetchone()['total']
    
    cur_alertas.execute("SELECT COUNT(*) as total FROM reportes_usuarios WHERE estado = 'pendiente'")
    reportes_pendientes = cur_alertas.fetchone()['total']
    
    cur_alertas.execute("SELECT COUNT(*) as total FROM reportes_usuarios WHERE estado = 'en_revision'")
    reportes_en_revision = cur_alertas.fetchone()['total']
    
    cur_alertas.execute("SELECT COUNT(*) as total FROM reportes_usuarios WHERE estado = 'resuelto'")
    reportes_resueltos = cur_alertas.fetchone()['total']
    
    conn_alertas.close()
    
    # Obtener información de usuarios de usuarios.db
    conn_usuarios = sqlite3.connect('usuarios.db')
    conn_usuarios.row_factory = sqlite3.Row
    cur_usuarios = conn_usuarios.cursor()
    cur_usuarios.execute("SELECT id, nombre, correo FROM usuarios")
    usuarios_dict = {row['id']: dict(row) for row in cur_usuarios.fetchall()}
    conn_usuarios.close()
    
    # Combinar datos: agregar información de usuario a cada reporte
    reportes = []
    for reporte in reportes_raw:
        usuario_id = reporte.get('usuario_id')
        if usuario_id and usuario_id in usuarios_dict:
            reporte['usuario_nombre'] = usuarios_dict[usuario_id]['nombre']
            reporte['usuario_correo'] = usuarios_dict[usuario_id]['correo']
        else:
            reporte['usuario_nombre'] = 'Usuario eliminado'
            reporte['usuario_correo'] = 'N/A'
        reportes.append(reporte)
    
    # Obtener lista de usuarios para el select (si se necesita)
    usuarios = list(usuarios_dict.values())
    
    return render_template('admin_reportes.html',
                         reportes=reportes,
                         total_reportes=total_reportes,
                         reportes_pendientes=reportes_pendientes,
                         reportes_en_revision=reportes_en_revision,
                         reportes_resueltos=reportes_resueltos,
                         usuarios=usuarios)

@app.route('/admin/reportes/cambiar-estado', methods=['POST'])
@admin_required
def cambiar_estado_reporte():
    """Cambiar el estado de un reporte"""
    reporte_id = request.form.get('reporte_id')
    nuevo_estado = request.form.get('nuevo_estado')
    
    if reporte_id and nuevo_estado:
        conn = sqlite3.connect('alertas.db')
        cur = conn.cursor()
        cur.execute("UPDATE reportes_usuarios SET estado = ? WHERE id = ?", (nuevo_estado, reporte_id))
        conn.commit()
        conn.close()
        flash('Estado del reporte actualizado exitosamente', 'success')
    else:
        flash('Datos inválidos', 'danger')
    
    return redirect(url_for('admin_reportes'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

