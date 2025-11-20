# app/__init__.py
import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import logging # Para configurar el logging
import datetime

# Importamos la clase de configuración desde la nueva estructura
from .config.config import Config


socketio = SocketIO()

def create_app(config_class_name=Config): # Acepta una clase de config, por defecto usa la nuestra
    """
    Fábrica de la aplicación Flask (Application Factory).
    """
    app = Flask(__name__) # Flask busca 'templates' y 'static' dentro del paquete 'app' por defecto
    # 1. Cargar la configuración desde el objeto Config
    app.config.from_object(config_class_name)

    
    if not app.debug and not app.testing:
        
        app.logger.setLevel(logging.INFO)
      
    else:
        app.logger.setLevel(logging.DEBUG) # Más verboso en debug

    app.logger.info("Iniciando la creación de la aplicación Skyking...")
    app.logger.info(f"SECRET_KEY cargada: {'Sí' if app.config.get('SECRET_KEY') else 'No'}")
    app.logger.info(f"FERNET_KEY cargada: {'Sí' if app.config.get('FERNET_KEY') else 'No'}")
    # No imprimas valores sensibles de configuración en los logs.

    # 3. Inicializar extensiones de Flask
    CORS(app, resources={r"/*": {"origins": app.config.get('CORS_ORIGINS', "*")}})
    app.logger.info("CORS inicializado.")

    # Aquí es donde realmente vinculamos la instancia de 'socketio' con nuestra 'app'.
    socketio.init_app(app, cors_allowed_origins=app.config.get('CORS_ORIGINS', "*"), async_mode='threading')
    app.logger.info("SocketIO inicializado con la app.")

    # 4. Registrar las rutas - Importamos desde las ubicaciones ORIGINALES que funcionan
    from . import routes_pages
    from . import routes_auth
    from . import routes_dron
    from . import routes_order
    from . import routes_tracking
    from .routes_restaurant import restaurant_bp
    from .routes_admin import admin_bp
    from .routes_delivery import delivery_bp
    from .routes_user import user_bp

    routes_pages.init_pages_routes(app)
    routes_auth.init_auth_routes(app)
    routes_dron.init_dron_routes(app)
    routes_order.init_order_routes(app)
    routes_tracking.init_tracking_routes(app)

    app.register_blueprint(restaurant_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(delivery_bp) 
    app.register_blueprint(user_bp)
    app.logger.info("Módulos de rutas y Blueprints inicializados.")
    app.logger.info("Módulos de rutas inicializados.")
    
    # 5. Registrar los manejadores de SocketIO
    from . import sockets # Importamos el módulo sockets.py
    sockets.init_socket_handlers(socketio) # Pasamos la instancia de socketio
    app.logger.info("Manejadores de SocketIO inicializados.")

    # (Opcional) Una ruta de prueba para verificar que la app funciona
    @app.route('/health')
    def health_check():
        return "Aplicación Skyking funcionando!"
    
    # >>> AÑADE ESTO: PROCESADOR DE CONTEXTO <
    @app.context_processor
    def inject_current_time():
        return {'now_utc': datetime.datetime.utcnow} # Pasamos la función utcnow
    app.logger.info("Procesador de contexto para 'now_utc' registrado.")
    # >>> FIN DE LA ADICIÓN <

    app.logger.info("Creación de la aplicación Skyking completada.")
    return app # Devolvemos la instancia de la aplicación configurada