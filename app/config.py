# app/config.py
import os
# No necesitas 'from cryptography.fernet import Fernet' aquí directamente
# a menos que también quieras generar la clave desde aquí,
# pero la instancia de Fernet se creará donde se use la clave.

class Config:
    # Flask Secret Key
    # Generar con: python -c "import os; print(os.urandom(24).hex())"
    # ¡IMPORTANTE! CAMBIA ESTA CLAVE EN PRODUCCIÓN Y USA VARIABLES DE ENTORNO
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'CAMBIA_ESTA_CLAVE_SECRETA_POR_ALGO_SEGURO_Y_UNICO')
    if SECRET_KEY == 'CAMBIA_ESTA_CLAVE_SECRETA_POR_ALGO_SEGURO_Y_UNICO' or SECRET_KEY == 'r76_RTQo[Wr':
        print("ADVERTENCIA: Usando FLASK_SECRET_KEY por defecto o insegura. Configúrala adecuadamente para producción.")

    # Fernet Key para encriptación de contraseñas
    # Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Esta clave DEBE ser bytes.
    FLASK_FERNET_KEY_STR = os.environ.get('FLASK_FERNET_KEY')
    if not FLASK_FERNET_KEY_STR:
        FERNET_KEY = b'p20D_cWCSN29k7s3z3GkDErEAZapu7awPiHbjIeV7b4=' # Clave por defecto en bytes
        print("ADVERTENCIA: Usando clave Fernet por defecto. Asegúrate de que sea la misma para encriptar y desencriptar.")
    else:
        FERNET_KEY = FLASK_FERNET_KEY_STR.encode('utf-8') # Convertir la clave de la variable de entorno a bytes

    # Configuración de la base de datos PostgreSQL
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_NAME = os.environ.get('DB_NAME', 'Dron1')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'cris2001') # ¡Usa variables de entorno para esto en producción!
    DB_PORT = os.environ.get('DB_PORT', '5432')

    # URL de conexión completa (opcional, pero útil para psycopg2 o SQLAlchemy)
    # Puedes construirla aquí o donde la necesites.
    # DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # Por ahora, dejaremos las partes separadas como las tienes y las usaremos directamente.

    # Configuración de Azure IoT Central
    IOT_CENTRAL_DEVICE_ID = '146h7gw55ks' # Renombrada para claridad
    IOT_CENTRAL_API_VERSION = '2022-07-31'
    IOT_CENTRAL_BASE_URL = 'https://skyking.azureiotcentral.com'
    IOT_CENTRAL_HEADERS = {
        'Accept': 'application/json',
        # ¡MUY IMPORTANTE! Esta Authorization Key es EXTREMADAMENTE SENSIBLE.
        # DEBERÍAS cargarla desde una variable de entorno y NUNCA subirla a un repositorio público.
        'Authorization': os.environ.get('IOT_CENTRAL_AUTH_TOKEN', 'SharedAccessSignature sr=73c4cceb-c6da-41c4-894f-1f6e7dd4524e&sig=lKkq1MXMIFy3JtmuNxLIKOlq6mTiN5xQJaCw4DL9jIE%3D&skn=TokenSky&se=1777416684533')
    }
    IOT_CENTRAL_TELEMETRY_NAMES = [
        'AlturaDron', 'BaterA', 'RPM', 'AceleraciN', 'Velocidad',
        'Temperatura_Motor1', 'Temperatura_Motor2', 'Temperatura_Motor3', 'Temperatura_Motor4'
    ]
    IOT_CENTRAL_EXECUTION_INTERVAL_SECONDS = 30

    # Configuración de CORS (opcional, si quieres que sea configurable)
    CORS_ORIGINS = "*" # o por ejemplo: os.environ.get('CORS_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080').split(',')

    # Puedes añadir otras configuraciones aquí, como:
    DEBUG = True
    TEMPLATES_AUTO_RELOAD=True

    
    UPLOAD_FOLDER = os.path.join('static', 'uploads', 'menu_item_images')
    UPLOAD_FOLDER_USER_AVATARS = os.path.join('static', 'uploads', 'user_avatars')
    UPLOAD_FOLDER_RESTAURANT_LOGOS = os.path.join('static', 'uploads', 'restaurant_logos')
    UPLOAD_FOLDER_PROFILE_PICS =  os.path.join('static', 'uploads', 'profile_pics')

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
