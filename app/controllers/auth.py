# app/routes_auth.py
from flask import render_template, request, jsonify, session, url_for, redirect, current_app, flash, abort
from cryptography.fernet import Fernet # Para encriptar/desencriptar
from functools import wraps
# Importamos las funciones de base de datos que necesitamos
from .db import find_user_by_email, create_new_user # Asegúrate que db.py esté en el mismo directorio (app) o ajusta la importación

def init_auth_routes(app):
    """
    Inicializa las rutas para la autenticación de usuarios.
    """

    cipher_suite = None
    try:
        # Es importante que app.config['FERNET_KEY'] ya esté en formato bytes.
        # Si no, Fernet(app.config['FERNET_KEY'].encode('utf-8')) podría ser necesario
        # si la clave está como string en la configuración.
        if app.config.get('FERNET_KEY'):
            key_bytes = app.config['FERNET_KEY']
            if isinstance(key_bytes, str):
                key_bytes = key_bytes.encode('utf-8') # Asegurar que sea bytes
            cipher_suite = Fernet(key_bytes)
        else:
            app.logger.critical("FERNET_KEY no está configurada en la aplicación.")
            # Considera no registrar las rutas o lanzar una excepción si la clave no está.
            # Por ahora, las rutas que dependen de cipher_suite fallarán controladamente.
    except Exception as e:
        app.logger.critical(f"Error al inicializar Fernet con la clave: {e}. La autenticación no funcionará.")
        # cipher_suite permanecerá como None

    @app.route('/login.html')
    def show_login_page_auth():
        return render_template('login.html')

    @app.route('/register.html')
    def show_register_page_auth():
        return render_template('register.html')

   
    @app.route('/register_ajax', methods=['POST'])
    def register_user_ajax():
        # Asegúrate de que 'cipher_suite' sea accesible aquí (definido en el scope de init_auth_routes)
        if not cipher_suite: 
            current_app.logger.critical("REGISTER_AJAX: Fernet (cipher_suite) no está inicializado.")
            return jsonify({"error": "Error crítico de configuración del servidor (crypto)."}), 500

        if not request.is_json:
            return jsonify({"error": "La solicitud debe ser en formato JSON."}), 400
        
        data = request.get_json()
        email = data.get('email')
        password_plain = data.get('password')
        
        # Para un registro público, 'user' es un buen rol por defecto.
        # Si este formulario también lo usa el admin para crear otros admins o roles,
        # el frontend debería enviar el rol deseado.
        # Asegúrate que 'user' sea un valor válido en tu user_role_enum de PostgreSQL.
        role_to_assign = data.get('role', 'user') 

        if not email or not password_plain:
            return jsonify({"error": "El correo electrónico y la contraseña son obligatorios."}), 400
        
        # Aquí podrías añadir validaciones más robustas para el email y la contraseña (longitud, complejidad, etc.)

        existing_user = find_user_by_email(email)
        if existing_user:
            return jsonify({"error": "Este correo electrónico ya está registrado. Intenta iniciar sesión."}), 409 # Conflict

        try:
            encrypted_password_bytes = cipher_suite.encrypt(password_plain.encode('utf-8'))
            encrypted_password_str = encrypted_password_bytes.decode('utf-8')
        except Exception as e:
            current_app.logger.error(f"REGISTER_AJAX: Error encriptando contraseña para {email}: {e}", exc_info=True)
            return jsonify({"error": "Error interno al procesar la contraseña."}), 500

        # Llamar a la función de la base de datos para crear el nuevo usuario
        new_user_result = create_new_user(email, encrypted_password_str, role_to_assign) 

        if new_user_result and not new_user_result.get('error'):
            user_email_created = new_user_result.get('email', email) 
            current_app.logger.info(f"REGISTER_AJAX: Usuario {user_email_created} (Rol: {role_to_assign}) registrado con éxito.")
            return jsonify({"message": f"¡Usuario {user_email_created} registrado con éxito! Ahora puedes iniciar sesión."}), 201 # 201 Created
        else:
            error_message_from_db = "No se pudo crear la cuenta en este momento." # Mensaje genérico
            if new_user_result and new_user_result.get('error'):
                error_message_from_db = new_user_result['error']
            # No es necesario el 'elif not new_user_result:' si create_new_user siempre devuelve un dict
            
            current_app.logger.error(f"REGISTER_AJAX: Fallo al crear usuario {email} en la BD: {error_message_from_db}")
            # Devolver 500 si es un error de BD o configuración, 400 si es un error de datos del usuario (aunque ya se validó antes)
            return jsonify({"error": error_message_from_db}), 500
    @app.route('/login_ajax', methods=['POST'])
    def login_user_ajax():
        if not cipher_suite:
            current_app.logger.error("Intento de login pero Fernet no está inicializado o falló la inicialización.")
            return jsonify({"error": "Error de configuración del servidor (crypto)."}), 500

        if not request.is_json:
            return jsonify({"error": "Solicitud debe ser JSON"}), 400
        
        data = request.get_json()
        email = data.get('email')
        password_plain = data.get('password')

        if not email or not password_plain:
            return jsonify({"error": "Email y contraseña son obligatorios"}), 400

        user = find_user_by_email(email) # Esta función debe devolver un dict con 'id', 'email', 'password_hash', 'role'

        if user and user.get('password_hash') and user.get('role'): # Verificar que 'role' también exista
            try:
                encrypted_password_from_db_bytes = user['password_hash'].encode('utf-8')
                decrypted_password_bytes = cipher_suite.decrypt(encrypted_password_from_db_bytes)
                decrypted_password_plain = decrypted_password_bytes.decode('utf-8')

                if decrypted_password_plain == password_plain:
                    session['user_id'] = user['id']
                    session['user_email'] = user['email']
                    session['user_role'] = user['role'] # Asegúrate que el campo 'role' se obtiene de 'user'
                    
                    current_app.logger.info(f"Usuario {session['user_email']} con rol {session['user_role']} ha iniciado sesión.")
                    
                    redirect_url_target = url_for('home_page') # URL por defecto

                    # Lógica de redirección basada en el rol
                    if session['user_role'] == 'restaurant_owner':
                        # Asumiendo que tienes un Blueprint 'restaurant' y una ruta 'dashboard' en él
                        redirect_url_target = url_for('restaurant.dashboard') 
                    elif session['user_role'] == 'admin':
                        redirect_url_target = url_for('admin.dashboard') # Ejemplo para un panel de admin
                        
                    elif session['user_role']== 'user':
                        redirect_url_target = url_for('inicio_cliente')
                    
                    elif session['user_role']== 'repartidor_moto':
                        redirect_url_target = url_for('delivery.repartidor_dashboard')
                    elif session['user_role']== 'repartidor_bici':
                        redirect_url_target = url_for('delivery.repartidor_dashboard')

                    current_app.logger.info(f"URL de redirección calculada para '{session['user_role']}': {redirect_url_target}")
                    
                    # ***** ESTA ES LA LÍNEA CORREGIDA *****
                    return jsonify({
                        "message": "Inicio de sesión exitoso.",
                        "redirect_url": redirect_url_target 
                    }), 200
                else:
                    current_app.logger.warning(f"Intento de login fallido (contraseña incorrecta) para: {email}")
                    return jsonify({"error": "Correo o contraseña incorrectos"}), 401
            except Exception as e:
                current_app.logger.error(f"Error al desencriptar o comparar contraseña para {email}: {e}")
                return jsonify({"error": "Error al verificar credenciales. Intente más tarde."}), 500
        else:
            current_app.logger.warning(f"Intento de login para usuario no existente, sin hash de contraseña o sin rol: {email}")
            return jsonify({"error": "Correo o contraseña incorrectos"}), 401
            
    @app.route('/logout_ajax', methods=['POST'])
    def logout_user_ajax():
        user_email_logged_out = session.get('user_email', 'Usuario desconocido')
        session.pop('user_id', None)
        session.pop('user_email', None)
        session.pop('user_role', None) # También limpiar el rol de la sesión
        current_app.logger.info(f"Usuario {user_email_logged_out} ha cerrado sesión.")
        # Es buena idea redirigir al login o a la home page desde el cliente después del logout
        return jsonify({"message": "Sesión cerrada exitosamente.", "redirect_url": url_for('show_login_page_auth')}), 200

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            # Guarda la URL a la que intentaban acceder para redirigir después del login
            # request.url contiene la URL completa que se intentó acceder.
            session['next_url'] = request.url 
            return redirect(url_for('show_login_page_auth')) # Endpoint de tu página de login
        return f(*args, **kwargs)
    return decorated_function
