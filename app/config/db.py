# app/db.py
import psycopg2
from psycopg2 import extras # Para RealDictCursor y execute_values
from flask import current_app # Para acceder a la configuración de la app (app.config)
from datetime import datetime, timezone # Para logs o timestamps si es necesari
from werkzeug.security import check_password_hash, generate_password_hash

def get_db_connection():
    """
    Establece conexión con la base de datos PostgreSQL.
    Utiliza la configuración definida en la instancia de la aplicación Flask.
    """
    try:
        # Cuando la app Flask esté configurada, current_app.config contendrá tus variables de Config.
        # Por ahora, DB_CONFIG no está directamente aquí. Asumiremos que current_app.config
        # tendrá DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT.
        # O, si prefieres, puedes pasar directamente los valores de config a esta función
        # desde donde la llames, pero usar current_app es más "Flask-friendly" a largo plazo.

        # Ejemplo de cómo se usaría con current_app (una vez que app/__init__.py esté configurado):
        conn_details = {
            'host': current_app.config['DB_HOST'],
            'database': current_app.config['DB_NAME'],
            'user': current_app.config['DB_USER'],
            'password': current_app.config['DB_PASSWORD'],
            'port': current_app.config['DB_PORT']
        }
        conn = psycopg2.connect(**conn_details)
        return conn
    except psycopg2.OperationalError as e:
        # En una aplicación real, querrías un mejor logging aquí.
        print(f"[{datetime.now()}] Error al conectar a la base de datos (get_db_connection): {e}")
        # Podrías querer registrar esto en current_app.logger.error(f"DB Connection Error: {e}")
        return None
    except Exception as e: # Captura general
        print(f"[{datetime.now()}] Error inesperado al conectar a la base de datos (get_db_connection): {e}")
        return None

# --- Funciones para Usuarios (Auth) ---

def find_user_by_email(email_address):
    """Busca un usuario por su email y devuelve sus datos o None."""
    conn = get_db_connection()
    if not conn:
        return None # No se pudo conectar a la BD
    
    user_data = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute("SELECT id, email, password_hash, role, is_active FROM users WHERE email = %s", (email_address,))
            user_data = cur.fetchone()
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al buscar usuario por email '{email_address}': {e}")
        # current_app.logger.error(f"DB error finding user by email: {e}")
    finally:
        if conn:
            conn.close()
    return user_data



def create_new_user(email, hashed_password_str, user_role, full_name=None, phone_number=None):
    """Crea un nuevo usuario en la base de datos y devuelve sus datos o un error."""
    conn = get_db_connection()
    if not conn:
        # Usar current_app.logger si está disponible
        log_message = f"create_new_user: No se pudo conectar a BD para registrar {email}"
        if current_app:
            current_app.logger.error(log_message)
        else:
            print(f"[{datetime.now()}] {log_message}") # Fallback si current_app no está disponible (ej. scripts)
        return {'error': 'Error de conexión con la base de datos (DB1)'}

    new_user_info = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # SQL query con RETURNING para obtener los datos del usuario insertado
            sql_query = """INSERT INTO users (email, password_hash, role, full_name, phone_number)
                             VALUES (%s, %s, %s, %s, %s) RETURNING id, email, role, full_name, phone_number;"""
            
            if current_app:
                current_app.logger.debug(f"DB: Ejecutando create_new_user para {email} con rol {user_role}")
            else:
                print(f"DB: Ejecutando create_new_user para {email} con rol {user_role}")

            cur.execute(sql_query, (email, hashed_password_str, user_role, full_name, phone_number))
            new_user_info = cur.fetchone() # Esto debería devolver el diccionario del nuevo usuario o None

            if new_user_info and new_user_info.get('id'):
                conn.commit() # Solo hacer commit si la inserción y RETURNING fueron exitosos
                if current_app:
                    current_app.logger.info(f"Usuario {email} (ID: {new_user_info['id']}) creado con rol {user_role}.")
                else:
                    print(f"Usuario {email} (ID: {new_user_info['id']}) creado con rol {user_role}.")
            else:
                # Si new_user_info es None o no tiene ID, algo falló con INSERT o RETURNING
                # No se debería haber llegado aquí si psycopg2.Error se hubiera lanzado por un INSERT fallido,
                # pero es una salvaguarda.
                if current_app:
                    current_app.logger.error(f"create_new_user: fetchone() devolvió None o no ID para {email} después de INSERT. Haciendo rollback.")
                else:
                    print(f"create_new_user: fetchone() devolvió None o no ID para {email} después de INSERT. Haciendo rollback.")
                if conn: # Asegurar que conn no sea None
                    conn.rollback()
                # new_user_info permanecerá None, y el bloque 'else' final lo manejará
    
    except psycopg2.Error as e:
        log_message_db_error = f"Error de BD (psycopg2) al crear usuario '{email}' (Rol: {user_role}): {e}"
        if current_app:
            current_app.logger.error(log_message_db_error, exc_info=True)
        else:
            print(f"[{datetime.now()}] {log_message_db_error}")
        if conn:
            conn.rollback()
        return {'error': f'Error de base de datos al crear usuario (DB2: {e.pgcode if hasattr(e, "pgcode") else "Desconocido"})'}
    
    except Exception as e_general: # Capturar cualquier otra excepción inesperada
        log_message_general_error = f"Error general inesperado al crear usuario '{email}': {e_general}"
        if current_app:
            current_app.logger.error(log_message_general_error, exc_info=True)
        else:
            print(f"[{datetime.now()}] {log_message_general_error}")
        if conn: # conn podría no estar definido si el error fue muy temprano
            conn.rollback()
        return {'error': 'Error inesperado del servidor al procesar el registro (DB3).'}
        
    finally:
        if conn:
            conn.close()
           

    # Evaluar el resultado final
    if new_user_info and new_user_info.get('id'):
        return new_user_info # Éxito, devuelve el diccionario del usuario
    else:
        return {'error': 'No se pudo obtener la información del usuario después del registro (DB4).'}
# --- Funciones para Telemetría del Dron ---

def save_drone_telemetry_batch(telemetry_data_list):
    """
    Guarda un lote de datos de telemetría en la base de datos.
    telemetry_data_list es una lista de tuplas: (telemetry_name, value, timestamp)
    """
    if not telemetry_data_list:
        return 0 # Nada que insertar

    conn = get_db_connection()
    if not conn:
        print(f"[{datetime.now()}] DB/Telemetry: No se pudo conectar para guardar lote.")
        return -1 # Error de conexión

    rows_affected = 0
    try:
        with conn.cursor() as cur: # No RealDictCursor para inserciones masivas si no necesitas el resultado así
            insert_sql = "INSERT INTO dron1_telemetry (telemetry_name, value, timestamp) VALUES %s"
            # extras.execute_values es eficiente para inserciones masivas
            extras.execute_values(cur, insert_sql, telemetry_data_list, template="(%s, %s, %s)", page_size=100)
            conn.commit()
            rows_affected = cur.rowcount # O len(telemetry_data_list) si execute_values no devuelve rowcount útil
            print(f"[{datetime.now()}] DB/Telemetry: {len(telemetry_data_list)} registros de telemetría insertados.")
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al insertar lote de telemetría: {e}")
        if conn:
            conn.rollback()
        rows_affected = -2 # Error durante la inserción
        # current_app.logger.error(f"DB error saving telemetry batch: {e}")
    finally:
        if conn:
            conn.close()
    return rows_affected

def get_latest_drone_telemetry_timestamp():
    """Obtiene el timestamp más reciente de la tabla de telemetría."""
    conn = get_db_connection()
    if not conn:
        return None

    latest_timestamp = None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(timestamp) FROM dron1_telemetry")
            result = cur.fetchone()
            if result and result[0] is not None:
                latest_timestamp = result[0]
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener MAX(timestamp) de telemetría: {e}")
        # current_app.logger.error(f"DB error getting max telemetry timestamp: {e}")
    finally:
        if conn:
            conn.close()
    return latest_timestamp

def get_drone_telemetry_since(start_timestamp, end_timestamp):
    """Obtiene registros de telemetría dentro de un rango de timestamps."""
    conn = get_db_connection()
    if not conn:
        return [] # Lista vacía si no hay conexión

    data = []
    try:
        with conn.cursor() as cur: # Devolverá tuplas (telemetry_name, value, timestamp)
            query = """
            SELECT telemetry_name, value, timestamp
            FROM dron1_telemetry
            WHERE timestamp > %s AND timestamp <= %s
            ORDER BY timestamp ASC
            """
            cur.execute(query, (start_timestamp, end_timestamp))
            data = cur.fetchall()
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener telemetría desde '{start_timestamp}' hasta '{end_timestamp}': {e}")
        # current_app.logger.error(f"DB error getting telemetry since: {e}")
    finally:
        if conn:
            conn.close()
    return data

def get_historical_drone_telemetry(hours_ago=1):
    """Obtiene telemetría de las últimas 'hours_ago' horas."""
    conn = get_db_connection()
    if not conn:
        return []

    data = []
    # Asegúrate de que la zona horaria sea consistente con cómo almacenas los datos
    # Si tus timestamps en la BD son UTC, compara con UTC.
    # psycopg2.tz.FixedOffsetTimezone(offset=0, name=None) representa UTC.
    # O puedes usar timezone.utc de datetime si tu psycopg2 es reciente.
    from datetime import timezone as dt_timezone, timedelta
    interval_start = datetime.now(dt_timezone.utc) - timedelta(hours=hours_ago)
    try:
        with conn.cursor() as cur: # Devolverá tuplas
            query = """
            SELECT telemetry_name, value, timestamp
            FROM dron1_telemetry
            WHERE timestamp >= %s
            ORDER BY timestamp ASC
            """
            cur.execute(query, (interval_start,))
            data = cur.fetchall()
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener telemetría histórica ({hours_ago}h): {e}")
        # current_app.logger.error(f"DB error getting historical telemetry: {e}")
    finally:
        if conn:
            conn.close()
    return data

# --- Funciones para Restaurantes y Menús ---

def get_all_restaurants():
    """Obtiene todos los restaurantes activos."""
    conn = get_db_connection()
    if not conn:
        print("[DB_DEBUG] get_all_restaurants: No se pudo obtener conexión a BD.") #########################
        return [] # Lista vacía si no hay conexión
    
    restaurants_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute("SELECT id, name, description, address, phone_number, logo_image_url FROM restaurants WHERE is_active = TRUE ORDER BY name ASC")
            restaurants_list = cur.fetchall()
            ##########
            print(f"[DB_DEBUG] get_all_restaurants - Datos crudos obtenidos: {restaurants_list}")
    except psycopg2.Error as e:
        # Idealmente, usa current_app.logger.error si está disponible en el contexto
        print(f"[{datetime.now()}] Error de BD al obtener todos los restaurantes: {e}")
        
    finally:
        if conn:
            conn.close()
    print(f"[DB_DEBUG] get_all_restaurants - Retornando: {restaurants_list}")
    return restaurants_list

def get_restaurant_by_id(restaurant_id):
    """Obtiene un restaurante específico por su ID."""
    conn = get_db_connection()
    if not conn:
        return None
    
    restaurant_data = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute("SELECT id, name, description, address, phone_number, user_id FROM restaurants WHERE id = %s AND is_active = TRUE", (restaurant_id,))
            restaurant_data = cur.fetchone()
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener restaurante por ID '{restaurant_id}': {e}")
    finally:
        if conn:
            conn.close()
    return restaurant_data

def get_menu_items_by_restaurant_id(restaurant_id):
    """Obtiene todos los ítems de menú disponibles para un restaurante específico."""
    conn = get_db_connection()
    if not conn:
        return []
    
    menu_items_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, description, price, image_url "
                "FROM menu_items "
                "WHERE restaurant_id = %s AND is_available = TRUE ORDER BY name ASC",
                (restaurant_id,)
            )
            menu_items_list = cur.fetchall()
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener ítems de menú para restaurante ID '{restaurant_id}': {e}")
    finally:
        if conn:
            conn.close()
    return menu_items_list

def get_menu_item_by_id(menu_item_id):
    """Obtiene un ítem de menú específico por su ID."""
    conn = get_db_connection()
    if not conn:
        return None
    menu_item_data = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, name, description, price, restaurant_id " # Añade los campos que necesites
                "FROM menu_items "
                "WHERE id = %s AND is_available = TRUE",
                (menu_item_id,)
            )
            menu_item_data = cur.fetchone()
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener ítem de menú por ID '{menu_item_id}': {e}")
    finally:
        if conn:
            conn.close()
    return menu_item_data

# --- Funciones para Pedidos (Orders) ---

def create_new_order(user_id, restaurant_id, delivery_address, total_amount, 
                     status, payment_method, payment_status, notes, delivery_type, 
                     order_items_list):
    """
    Crea un nuevo pedido y sus ítems asociados en la base de datos.
    order_items_list es una lista de diccionarios, cada uno con:
    {'menu_item_id': id, 'quantity': cant, 'price_at_order': precio}
    """
    conn = get_db_connection()
    if not conn:
        return None # No se pudo conectar

    new_order_id = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # 1. Insertar en la tabla 'orders'
            cur.execute(
                """
                INSERT INTO orders (user_id, restaurant_id, delivery_address, total_amount, 
                                    status, payment_method, payment_status, notes, delivery_type, ordered_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id; 
                """,
                (user_id, restaurant_id, delivery_address, total_amount, 
                 status, payment_method, payment_status, notes, delivery_type, datetime.now(timezone.utc)) # Asegura UTC para ordered_at
            )
            result = cur.fetchone()
            if not result or not result.get('id'):
                raise psycopg2.DatabaseError("No se pudo obtener el ID del nuevo pedido.")
            new_order_id = result['id']

            # 2. Preparar datos para 'order_items'
            items_to_insert_in_db = []
            for item in order_items_list:
                items_to_insert_in_db.append((
                    new_order_id, 
                    item['menu_item_id'], 
                    item['quantity'], 
                    item['price_at_order']
                ))
            
            if items_to_insert_in_db:
                # Usar extras.execute_values para inserción masiva eficiente
                insert_query_items = "INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_order) VALUES %s"
                extras.execute_values(cur, insert_query_items, items_to_insert_in_db, template="(%s, %s, %s, %s)")
            
            conn.commit() # Confirmar la transacción (pedido y sus ítems)
            
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al crear nuevo pedido para usuario ID '{user_id}': {e}")
        if conn:
            conn.rollback() # Revertir toda la transacción si algo falla
        new_order_id = None # Indicar que falló
        # Considera devolver el error 'e' o un mensaje más específico si es necesario
    except Exception as e: # Capturar otros posibles errores (como el DatabaseError que lancé)
        print(f"[{datetime.now()}] Error general al crear nuevo pedido: {e}")
        if conn:
            conn.rollback()
        new_order_id = None
    finally:
        if conn:
            conn.close()
            
    return new_order_id # Devuelve el ID del nuevo pedido o None si falló


def get_orders_by_user_id(user_id_param):
    """Obtiene el historial de pedidos para un usuario específico."""
    conn = get_db_connection()
    if not conn:
        return []
    
    orders_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Esta consulta obtiene los pedidos principales.
            # Podrías hacer otra consulta para obtener los ítems de cada pedido si es necesario,
            # o usar un JOIN más complejo.
            cur.execute(
                "SELECT o.id, o.restaurant_id, r.name as restaurant_name, o.total_amount, o.status, o.ordered_at, o.delivery_type "
                "FROM orders o "
                "JOIN restaurants r ON o.restaurant_id = r.id "
                "WHERE o.user_id = %s ORDER BY o.ordered_at DESC",
                (user_id_param,)
            )
            orders_list = cur.fetchall()
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener pedidos para usuario ID '{user_id_param}': {e}")
    finally:
        if conn:
            conn.close()
    return orders_list

# (Opcional) Función para obtener los detalles de un pedido específico, incluyendo sus ítems
def get_order_details_by_id(order_id_param):
    conn = get_db_connection()
    if not conn:
        return None, [] # Pedido y lista de ítems

    order_details = None
    order_items_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Obtener detalles del pedido
            cur.execute(
                "SELECT o.*, r.name as restaurant_name " # Selecciona todos los campos de orders y el nombre del restaurante
                "FROM orders o "
                "JOIN restaurants r ON o.restaurant_id = r.id "
                "WHERE o.id = %s", (order_id_param,)
            )
            order_details = cur.fetchone()

            if order_details:
                # Obtener ítems del pedido
                cur.execute(
                    "SELECT oi.quantity, oi.price_at_order, mi.name as menu_item_name, mi.description as menu_item_description "
                    "FROM order_items oi "
                    "JOIN menu_items mi ON oi.menu_item_id = mi.id "
                    "WHERE oi.order_id = %s",
                    (order_id_param,)
                )
                order_items_list = cur.fetchall()
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener detalles del pedido ID '{order_id_param}': {e}")
        order_details = None # Asegurar que no se devuelvan datos parciales en caso de error
        order_items_list = []
    finally:
        if conn:
            conn.close()
    return order_details, order_items_list

def get_order_for_tracking_by_id_and_user(order_id, user_id_requesting):
    """
    Obtiene los detalles de un pedido para seguimiento, incluyendo el nombre del restaurante
    y los detalles del repartidor si está asignado.
    Verifica que el pedido pertenezca al usuario que lo solicita o que el usuario sea admin.
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    order_data = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Obtener el rol del usuario que solicita (necesitarás esta función o adaptarla)
            # Asumimos que tienes una función o forma de obtener el rol del usuario actual.
            # Por ahora, lo simplificaremos y asumiremos que la verificación de rol se hace en la ruta.
            # O, si 'users' tiene 'role':
            # cur.execute("SELECT role FROM users WHERE id = %s", (user_id_requesting,))
            # user_requesting_details = cur.fetchone()
            # user_is_admin = user_requesting_details and user_requesting_details['role'] == 'admin'

            query = """
                SELECT 
                    o.id, o.user_id, o.restaurant_id, o.delivery_address, o.status, 
                    o.ordered_at, o.delivery_type, o.delivery_person_id,
                    r.name as restaurant_name,
                    u.full_name as delivery_person_name, 
                    u.phone_number as delivery_person_phone,
                    u.role as delivery_person_role
                FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.id
                LEFT JOIN users u ON o.delivery_person_id = u.id
                WHERE o.id = %s;
            """
            cur.execute(query, (order_id,))
            order_data = cur.fetchone()

            # Verificación de permiso (simplificada aquí, idealmente más robusta)
            if order_data and order_data['user_id'] != user_id_requesting:
                # Si no es el dueño del pedido, no devolver datos (a menos que sea admin)
                # Esta lógica de permiso es mejor manejarla en la ruta.
                # Por ahora, la función devuelve los datos y la ruta decide.
                pass # La ruta se encargará de la lógica de permisos

    except psycopg2.Error as e:
        # current_app.logger.error(...)
        print(f"[{datetime.now()}] Error de BD al obtener pedido para seguimiento ID '{order_id}': {e}")
        order_data = None
    finally:
        if conn:
            conn.close()
    return order_data


def get_latest_drone_speed_from_telemetry():
    """
    Obtiene la velocidad más reciente del dron desde la tabla de telemetría.
    Asume que todos los registros en dron1_telemetry son del único dron
    y que la columna de velocidad se llama 'Velocidad'.
    """
    conn = get_db_connection()
    if not conn:
        return None # O 'N/A'

    speed_data = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Asumiendo que la telemetría de velocidad se llama 'Velocidad'
            # y que queremos la más reciente para el dron.
            # Si tienes múltiples drones o diferentes nombres de telemetría, esto necesitaría cambiar.
            cur.execute(
                "SELECT value FROM dron1_telemetry "
                "WHERE telemetry_name = 'Velocidad' " # Ajusta 'Velocidad' si el nombre es diferente
                "ORDER BY timestamp DESC LIMIT 1"
            )
            result = cur.fetchone()
            if result:
                speed_data = result['value']
    except psycopg2.Error as e:
        print(f"[{datetime.now()}] Error de BD al obtener velocidad del dron: {e}")
    finally:
        if conn:
            conn.close()
    return speed_data


def get_restaurants_by_owner_id(owner_user_id):
    """Obtiene los restaurantes asociados a un user_id (dueño)."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("get_restaurants_by_owner_id: No se pudo obtener conexión a BD.")
        return [] # Devuelve lista vacía si no hay conexión

    restaurants_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Asumimos que la tabla 'restaurants' tiene una columna 'user_id'
            cur.execute(
                "SELECT id, name, description, address, phone_number, is_active "
                "FROM restaurants WHERE user_id = %s ORDER BY name ASC", 
                (owner_user_id,)
            )
            restaurants_list = cur.fetchall()
            # current_app.logger.debug(f"Restaurantes encontrados para owner {owner_user_id}: {restaurants_list}")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener restaurantes por dueño ID '{owner_user_id}': {e}")
    except Exception as e: # Captura otros posibles errores, ej. si current_app no está disponible
        print(f"Error general en get_restaurants_by_owner_id: {e}")
    finally:
        if conn:
            conn.close()
    return restaurants_list



def add_new_menu_item_to_db(restaurant_id, name, description, price, image_url=None, is_available=True):
    """Añade un nuevo ítem de menú a la base de datos para un restaurante específico."""
    conn = get_db_connection()
    if not conn:
        # current_app.logger.error("add_new_menu_item_to_db: No se pudo obtener conexión a BD.")
        print("[DB_DEBUG] add_new_menu_item_to_db: No se pudo obtener conexión a BD.")
        return None # O False para indicar fallo

    new_item_id = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO menu_items (restaurant_id, name, description, price, image_url, is_available, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (restaurant_id, name, description, price, image_url, is_available, datetime.now(timezone.utc))
            )
            result = cur.fetchone()
            if result and result.get('id'):
                new_item_id = result['id']
                conn.commit()
                # current_app.logger.info(f"Nuevo ítem de menú ID {new_item_id} añadido para restaurante ID {restaurant_id}.")
                print(f"[DB_DEBUG] Nuevo ítem de menú ID {new_item_id} añadido para restaurante ID {restaurant_id}.")
            else:
                # current_app.logger.error("add_new_menu_item_to_db: No se pudo obtener el ID del nuevo ítem.")
                print("[DB_DEBUG] add_new_menu_item_to_db: No se pudo obtener el ID del nuevo ítem.")
                conn.rollback() # Revertir si no se pudo obtener el ID
    except psycopg2.Error as e:
        # current_app.logger.error(f"Error de BD al añadir ítem de menú para restaurante ID '{restaurant_id}': {e}")
        print(f"[{datetime.now()}] Error de BD al añadir ítem de menú para restaurante ID '{restaurant_id}': {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        # current_app.logger.error(f"Error general en add_new_menu_item_to_db: {e}")
        print(f"[{datetime.now()}] Error general en add_new_menu_item_to_db: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return new_item_id # Devuelve el ID del nuevo ítem o None si falló



def update_menu_item_in_db(item_id, name, description, price, is_available, image_url=None):
    """Actualiza un ítem de menú existente en la base de datos."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"update_menu_item_in_db: No se pudo obtener conexión a BD para item ID {item_id}.")
        return False # Indicar fallo

    updated_rows = 0
    try:
        with conn.cursor() as cur: # No necesitamos RealDictCursor para un UPDATE si no devolvemos la fila
            cur.execute(
                """
                UPDATE menu_items 
                SET name = %s, description = %s, price = %s, is_available = %s, image_url = %s
                WHERE id = %s;
                """,
                (name, description, price, is_available, image_url, item_id)
            )
            updated_rows = cur.rowcount # Número de filas afectadas (debería ser 1 o 0)
            conn.commit()
            if updated_rows > 0:
                current_app.logger.info(f"Ítem de menú ID {item_id} actualizado exitosamente.")
            else:
                current_app.logger.warning(f"No se actualizó ningún ítem con ID {item_id} (podría no existir o los datos eran iguales).")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al actualizar ítem de menú ID '{item_id}': {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        current_app.logger.error(f"Error general en update_menu_item_in_db para item ID {item_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return updated_rows > 0 # Devuelve True si se actualizó al menos una fila, False si no.
    

def delete_menu_item_from_db(item_id_to_delete):
    """Elimina un ítem de menú de la base de datos por su ID."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"delete_menu_item_from_db: No se pudo obtener conexión a BD para item ID {item_id_to_delete}.")
        return False

    deleted_rows = 0
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM menu_items WHERE id = %s;", (item_id_to_delete,))
            deleted_rows = cur.rowcount # Número de filas afectadas (debería ser 1 si existía)
            conn.commit()
            if deleted_rows > 0:
                current_app.logger.info(f"Ítem de menú ID {item_id_to_delete} eliminado exitosamente.")
            else:
                current_app.logger.warning(f"No se eliminó ningún ítem con ID {item_id_to_delete} (podría no existir).")
    except psycopg2.Error as e:
        # Esto podría fallar si el ítem está referenciado en order_items y hay una restricción FK
        current_app.logger.error(f"Error de BD al eliminar ítem de menú ID '{item_id_to_delete}': {e}")
        if conn:
            conn.rollback()
        # Podrías querer devolver el error 'e' o un código específico para manejarlo en la ruta
        # Por ejemplo, si e.pgcode == '23503' (foreign_key_violation)
        raise e # Relanzar la excepción para que la ruta la maneje si es necesario, o devolver False
    except Exception as e:
        current_app.logger.error(f"Error general en delete_menu_item_from_db para item ID {item_id_to_delete}: {e}")
        if conn:
            conn.rollback()
        return False # Indicar fallo
    finally:
        if conn:
            conn.close()
    return deleted_rows > 0 # Devuelve True si se eliminó al menos una fila



# app/db.py
# ... (tus importaciones y funciones existentes) ...

def get_orders_for_restaurant_from_db(restaurant_id_param, status_filter=None):
    """
    Obtiene todos los pedidos para un restaurante específico (versión simplificada).
    Incluye el nombre (o email) del cliente.
    """
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"GFRDB: No connection for restaurant {restaurant_id_param}")
        return []
    
    # Descomenta las siguientes líneas si quieres seguir depurando el estado de la conexión
    # current_app.logger.info(f"GFRDB: Connection object: {conn}")
    # current_app.logger.info(f"GFRDB: Connection closed status: {conn.closed}")
    # if conn.closed:
    #     current_app.logger.error(f"GFRDB: ¡La conexión para el restaurante {restaurant_id_param} ya estaba cerrada!")
    #     return []

    # Prueba con autocommit, puede ayudar con algunos problemas de estado de cursor/transacción
    conn.autocommit = True 

    orders_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            query = """
                SELECT 
                    o.id, o.user_id, o.delivery_address, o.total_amount, o.status, 
                    o.ordered_at, o.delivery_type, o.notes,
                    u.full_name as customer_name, u.email as customer_email
                FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE o.restaurant_id = %s
            """
            params = [restaurant_id_param]

            if status_filter: # Si decides usar filtros de estado más adelante
                query += " AND o.status = %s"
                params.append(status_filter)
            
            query += " ORDER BY o.ordered_at DESC;"
            
            # current_app.logger.info(f"GFRDB: Executing simple query for R.{restaurant_id_param}")
            cur.execute(query, tuple(params))
            orders_list = cur.fetchall()
            # current_app.logger.info(f"GFRDB: Orders found for R.{restaurant_id_param} (simple query): {len(orders_list)}")

    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD (psycopg2.Error) al obtener pedidos (simple) para R.ID '{restaurant_id_param}': {e}", exc_info=True)
    except Exception as e:
        current_app.logger.error(f"Error general (Exception) en GFRDB (simple) para R.ID {restaurant_id_param}: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
    
    return orders_list

def update_order_status_in_db(order_id_to_update, new_status):
    """Actualiza el estado de un pedido específico."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"update_order_status_in_db: No se pudo conectar a BD para order ID {order_id_to_update}.")
        return False

    updated_rows = 0
    try:
        with conn.cursor() as cur:
            # Asegúrate que new_status sea uno de los valores válidos de tu ENUM order_status_enum
            cur.execute(
                "UPDATE orders SET status = %s WHERE id = %s;",
                (new_status, order_id_to_update)
            )
            updated_rows = cur.rowcount
            conn.commit()
            if updated_rows > 0:
                current_app.logger.info(f"Estado del pedido ID {order_id_to_update} actualizado a '{new_status}'.")
            else:
                current_app.logger.warning(f"No se actualizó el estado del pedido ID {order_id_to_update} (podría no existir o el estado ya era '{new_status}').")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al actualizar estado del pedido ID '{order_id_to_update}': {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        current_app.logger.error(f"Error general en update_order_status_in_db para order ID {order_id_to_update}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return updated_rows > 0



def update_restaurant_details_in_db(restaurant_id, name, description, address, phone_number, is_active, logo_image_url=None):
    """Actualiza los detalles de un restaurante existente en la base de datos, incluyendo el logo_image_url."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"update_restaurant_details_in_db: No se pudo conectar a BD para restaurante ID {restaurant_id}")
        return False

    updated_rows = 0
    try:
        with conn.cursor() as cur:
            is_active_bool = True if is_active else False # Convertir 'on' o presencia a booleano

            # Lista de campos a actualizar y sus parámetros
            set_clauses = [
                "name = %s",
                "description = %s",
                "address = %s",
                "phone_number = %s",
                "is_active = %s"
            ]
            params = [name, description, address, phone_number, is_active_bool]

           
            if logo_image_url is not None: # Esto cubre tanto una nueva URL como None (para borrar)
                set_clauses.append("logo_image_url = %s")
                params.append(logo_image_url)
           

            # Añadimos el restaurant_id para la cláusula WHERE
            params.append(restaurant_id)

            # Construimos la consulta SQL
            sql_query = f"UPDATE restaurants SET {', '.join(set_clauses)} WHERE id = %s;"
            
            current_app.logger.debug(f"DB: Ejecutando update_restaurant_details: {cur.mogrify(sql_query, tuple(params)).decode('utf-8', 'ignore')}")
            cur.execute(sql_query, tuple(params))
            updated_rows = cur.rowcount
            conn.commit()

            if updated_rows > 0:
                current_app.logger.info(f"Detalles del restaurante ID {restaurant_id} actualizados exitosamente.")
            else:
                current_app.logger.warning(f"No se actualizó ningún restaurante con ID {restaurant_id} (podría no existir o los datos eran idénticos).")
    
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al actualizar restaurante ID '{restaurant_id}': {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e_general:
        current_app.logger.error(f"Error general en update_restaurant_details_in_db para ID {restaurant_id}: {e_general}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            
    return updated_rows > 0


def add_new_drone_to_db(identifier, model, purchase_date, status, max_load=None, max_flight_time=None):
    """Añade un nuevo dron a la base de datos."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("add_new_drone_to_db: No se pudo conectar a BD.")
        return None # O False para indicar fallo

    new_drone_id = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            sql_query = """
                INSERT INTO drones (drone_identifier, model, purchase_date, status, 
                                    max_load_capacity_kg, max_flight_time_min, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """
            # Convertir purchase_date a None si está vacío, ya que el campo DATE puede ser NULL
            purchase_date_to_db = purchase_date if purchase_date else None
            
            cur.execute(sql_query, (
                identifier, model, purchase_date_to_db, status, 
                max_load, max_flight_time, datetime.now(timezone.utc)
            ))
            result = cur.fetchone()
            if result and result.get('id'):
                new_drone_id = result['id']
                conn.commit()
                current_app.logger.info(f"Nuevo dron ID {new_drone_id} ('{identifier}') añadido.")
            else:
                current_app.logger.error("add_new_drone_to_db: No se pudo obtener el ID del nuevo dron.")
                conn.rollback()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al añadir dron '{identifier}': {e}", exc_info=True)
        if conn:
            conn.rollback()
        # Podrías devolver el error específico si quieres manejarlo en la ruta
        # raise e 
    except Exception as e_general:
        current_app.logger.error(f"Error general en add_new_drone_to_db para dron '{identifier}': {e_general}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            
    return new_drone_id # Devuelve el ID del nuevo dron o None si falló



def get_all_users_for_admin():
    """Obtiene todos los usuarios para el panel de administración."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("get_all_users_for_admin: No se pudo conectar a BD.")
        return []

    users_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Selecciona los campos que quieres mostrar al admin
            # Es buena idea no seleccionar password_hash aquí por seguridad,
            # a menos que sea estrictamente necesario para alguna función admin (raro).
            cur.execute(
                "SELECT id, email, full_name, role, phone_number, created_at, is_active "
                "FROM users ORDER BY created_at DESC, id ASC" 
            )
            users_list = cur.fetchall()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener todos los usuarios: {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_all_users_for_admin: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return users_list



def get_user_by_id_for_admin(user_id_to_find):
    """Obtiene un usuario por su ID para el panel de administración."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"get_user_by_id_for_admin: No se pudo conectar a BD para user ID {user_id_to_find}")
        return None
    
    user_data = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Selecciona los campos necesarios, evita password_hash si no es para cambiarla
            cur.execute(
                "SELECT id, email, full_name, role, phone_number FROM users WHERE id = %s", 
                (user_id_to_find,)
            )
            user_data = cur.fetchone()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener usuario por ID '{user_id_to_find}': {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_user_by_id_for_admin para ID {user_id_to_find}: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return user_data

#Editar usuarios por admin
def update_user_by_admin_in_db(user_id_to_update, full_name, email, role, phone_number):
    """Actualiza los datos de un usuario por parte del administrador (no actualiza contraseña)."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"update_user_by_admin_in_db: No se pudo conectar a BD para user ID {user_id_to_update}")
        return False

    updated_rows = 0
    try:
        with conn.cursor() as cur:
            sql_query = """
                UPDATE users 
                SET full_name = %s, email = %s, role = %s, phone_number = %s
                WHERE id = %s;
            """
            cur.execute(sql_query, (full_name, email, role, phone_number, user_id_to_update))
            updated_rows = cur.rowcount
            conn.commit()
            if updated_rows > 0:
                current_app.logger.info(f"Usuario ID {user_id_to_update} actualizado por admin.")
            else:
                current_app.logger.warning(f"No se actualizó ningún usuario con ID {user_id_to_update} (podría no existir o los datos eran iguales).")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al actualizar usuario ID '{user_id_to_update}' por admin: {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e_general:
        current_app.logger.error(f"Error general en update_user_by_admin_in_db para ID {user_id_to_update}: {e_general}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return updated_rows > 0



def set_user_active_status_in_db(user_id_to_update, new_active_status):
    """Actualiza el estado 'is_active' de un usuario específico."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"set_user_active_status_in_db: No se pudo conectar a BD para user ID {user_id_to_update}")
        return False

    updated_rows = 0
    try:
        with conn.cursor() as cur:
            # new_active_status debe ser un booleano (True o False)
            cur.execute(
                "UPDATE users SET is_active = %s WHERE id = %s;",
                (new_active_status, user_id_to_update)
            )
            updated_rows = cur.rowcount
            conn.commit()
            if updated_rows > 0:
                action = "activado" if new_active_status else "desactivado"
                current_app.logger.info(f"Usuario ID {user_id_to_update} {action} exitosamente.")
            else:
                current_app.logger.warning(f"No se actualizó el estado de ningún usuario con ID {user_id_to_update} (podría no existir).")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al actualizar estado is_active para usuario ID '{user_id_to_update}': {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e_general:
        current_app.logger.error(f"Error general en set_user_active_status_in_db para ID {user_id_to_update}: {e_general}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return updated_rows > 0 # Devuelve True si se actualizó al menos una fila



def get_all_drones_for_admin():
    """Obtiene todos los drones para el panel de administración."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("get_all_drones_for_admin: No se pudo conectar a BD.")
        return []

    drones_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Selecciona los campos que quieres mostrar al admin
            cur.execute(
                """
                SELECT id, drone_identifier, model, purchase_date, status, 
                       max_load_capacity_kg, max_flight_time_min, created_at 
                FROM drones 
                ORDER BY created_at DESC, id ASC
                """
            )
            drones_list = cur.fetchall()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener todos los drones: {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_all_drones_for_admin: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return drones_list

#editar drones

def get_drone_by_id_for_admin(drone_id_to_find):
    """Obtiene un dron por su ID para el panel de administración."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"get_drone_by_id_for_admin: No se pudo conectar a BD para drone ID {drone_id_to_find}")
        return None
    
    drone_data = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, drone_identifier, model, purchase_date, status, 
                       max_load_capacity_kg, max_flight_time_min 
                FROM drones 
                WHERE id = %s
                """, 
                (drone_id_to_find,)
            )
            drone_data = cur.fetchone()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener dron por ID '{drone_id_to_find}': {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_drone_by_id_for_admin para ID {drone_id_to_find}: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return drone_data

def update_drone_by_admin_in_db(drone_id, identifier, model, purchase_date, status, max_load=None, max_flight_time=None):
    """Actualiza los detalles de un dron existente en la base de datos."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"update_drone_by_admin_in_db: No se pudo conectar a BD para drone ID {drone_id}")
        return False

    updated_rows = 0
    try:
        with conn.cursor() as cur:
            purchase_date_to_db = purchase_date if purchase_date else None
            
            sql_query = """
                UPDATE drones 
                SET drone_identifier = %s, model = %s, purchase_date = %s, 
                    status = %s, max_load_capacity_kg = %s, max_flight_time_min = %s
                WHERE id = %s;
            """
            cur.execute(sql_query, (
                identifier, model, purchase_date_to_db, status, 
                max_load, max_flight_time, drone_id
            ))
            updated_rows = cur.rowcount
            conn.commit()
            if updated_rows > 0:
                current_app.logger.info(f"Dron ID {drone_id} ('{identifier}') actualizado exitosamente.")
            else:
                current_app.logger.warning(f"No se actualizó ningún dron con ID {drone_id} (podría no existir o los datos eran iguales).")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al actualizar dron ID '{drone_id}': {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e_general:
        current_app.logger.error(f"Error general en update_drone_by_admin_in_db para ID {drone_id}: {e_general}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return updated_rows > 0

# app/db.py
# ... (tus importaciones existentes: psycopg2, extras, current_app, datetime, timezone) ...

# --- Funciones para la Gestión de Mantenimiento de Drones ---

def get_drones_for_select():
    """Obtiene una lista de drones (id, identificador, modelo) para usar en selectores/dropdowns."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("get_drones_for_select: No se pudo conectar a BD.")
        return []
    
    drones_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, drone_identifier, model FROM drones ORDER BY drone_identifier ASC"
            )
            drones_list = cur.fetchall()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener lista de drones para select: {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_drones_for_select: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return drones_list

def add_drone_maintenance_log(drone_id, service_date_str, service_type, description, 
                              parts_replaced=None, cost=None, technician_name=None):
    """Añade un nuevo registro de mantenimiento para un dron."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"add_drone_maintenance_log: No se pudo conectar a BD para drone ID {drone_id}.")
        return None # O False

    new_log_id = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Convertir service_date_str a None si está vacío, ya que el campo DATE puede ser NULL
            # o asegúrate de que siempre venga una fecha válida. Asumimos que es NOT NULL.
            # La BD se encargará de la conversión de string 'YYYY-MM-DD' a DATE.
            
            # Convertir cost a None si está vacío o no es un número válido
            cost_to_db = None
            if cost is not None:
                try:
                    cost_to_db = float(cost)
                except ValueError:
                    # Manejar el error si el costo no es un número, o dejarlo como None
                    current_app.logger.warning(f"Valor de costo inválido '{cost}' para log de mantenimiento del dron ID {drone_id}. Se guardará como NULL.")
                    cost_to_db = None

            sql_query = """
                INSERT INTO drone_maintenance_logs 
                    (drone_id, service_date, service_type, description, parts_replaced, cost, technician_name, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """
            cur.execute(sql_query, (
                drone_id, service_date_str, service_type, description,
                parts_replaced if parts_replaced else None, 
                cost_to_db, 
                technician_name if technician_name else None,
                datetime.now(timezone.utc)
            ))
            result = cur.fetchone()
            if result and result.get('id'):
                new_log_id = result['id']
                conn.commit()
                current_app.logger.info(f"Nuevo log de mantenimiento ID {new_log_id} añadido para dron ID {drone_id}.")
            else:
                current_app.logger.error("add_drone_maintenance_log: No se pudo obtener el ID del nuevo log.")
                conn.rollback()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al añadir log de mantenimiento para dron ID {drone_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e_general:
        current_app.logger.error(f"Error general en add_drone_maintenance_log para dron ID {drone_id}: {e_general}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return new_log_id


def get_all_maintenance_logs():
    """Obtiene todos los registros de mantenimiento, uniendo con la tabla de drones para más detalles."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("get_all_maintenance_logs: No se pudo conectar a BD.")
        return []
    
    logs_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Unimos con la tabla drones para obtener el identificador y modelo del dron
            cur.execute(
                """
                SELECT 
                    dml.id, dml.drone_id, d.drone_identifier, d.model as drone_model,
                    dml.service_date, dml.service_type, dml.description, 
                    dml.parts_replaced, dml.cost, dml.technician_name, dml.created_at
                FROM drone_maintenance_logs dml
                JOIN drones d ON dml.drone_id = d.id
                ORDER BY dml.service_date DESC, dml.created_at DESC;
                """
            )
            logs_list = cur.fetchall()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener todos los logs de mantenimiento: {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_all_maintenance_logs: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return logs_list



def set_drone_status_in_db(drone_id_to_update, new_drone_status):
    """Actualiza el estado 'status' de un dron específico."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"set_drone_status_in_db: No se pudo conectar a BD para drone ID {drone_id_to_update}")
        return False

    updated_rows = 0
    try:
        with conn.cursor() as cur:
            # new_drone_status debe ser un valor válido de tu ENUM drone_status_enum
            # (ej. 'activo', 'mantenimiento', 'inactivo', 'de_baja')
            cur.execute(
                "UPDATE drones SET status = %s WHERE id = %s;",
                (new_drone_status, drone_id_to_update)
            )
            updated_rows = cur.rowcount
            conn.commit()
            if updated_rows > 0:
                current_app.logger.info(f"Estado del dron ID {drone_id_to_update} actualizado a '{new_drone_status}'.")
            else:
                current_app.logger.warning(f"No se actualizó el estado de ningún dron con ID {drone_id_to_update} (podría no existir o el estado ya era '{new_drone_status}').")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al actualizar estado para dron ID '{drone_id_to_update}': {e}", exc_info=True)
        if conn:
            conn.rollback()
    except Exception as e_general:
        current_app.logger.error(f"Error general en set_drone_status_in_db para ID {drone_id_to_update}: {e_general}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return updated_rows > 0 # Devuelve True si se actualizó al menos una fila

#Ver todos los pedidos del sistema

def get_all_system_orders_for_admin(status_filter=None, date_filter=None): # Podríamos añadir más filtros
    """
    Obtiene todos los pedidos del sistema para el panel de administración.
    Incluye nombre del cliente y nombre del restaurante.
    """
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("get_all_system_orders_for_admin: No se pudo conectar a BD.")
        return []
    
    orders_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            base_query = """
                SELECT 
                    o.id, 
                    o.user_id, 
                    u.full_name AS customer_name, 
                    u.email AS customer_email,
                    o.restaurant_id, 
                    r.name AS restaurant_name,
                    o.delivery_address, 
                    o.total_amount, 
                    o.status, 
                    o.ordered_at, 
                    o.delivery_type, 
                    o.delivery_person_id,
                    dp.full_name AS delivery_person_name 
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN restaurants r ON o.restaurant_id = r.id
                LEFT JOIN users dp ON o.delivery_person_id = dp.id -- Para obtener el nombre del repartidor
            """
            params = []
            conditions = []

            if status_filter:
                conditions.append("o.status = %s")
                params.append(status_filter)
            
            if date_filter: # date_filter podría ser un string 'YYYY-MM-DD'
                conditions.append("DATE(o.ordered_at) = %s")
                params.append(date_filter)
            
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += " ORDER BY o.ordered_at DESC;"
            
            cur.execute(base_query, tuple(params))
            orders_list = cur.fetchall()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener todos los pedidos del sistema: {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_all_system_orders_for_admin: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return orders_list

#Ver detalles de pedidos por admin


def get_order_details_for_admin(order_id_to_find):
    """
    Obtiene los detalles completos de un pedido específico para el administrador,
    incluyendo información del cliente, restaurante, repartidor (si aplica) y los ítems del pedido.
    """
    conn = get_db_connection()
    if not conn:
        # Usar current_app.logger si está disponible y configurado
        log_message_conn_error = f"get_order_details_for_admin: No se pudo conectar a BD para pedido ID {order_id_to_find}"
        if current_app:
            current_app.logger.error(log_message_conn_error)
        else:
            print(f"[{datetime.now()}] {log_message_conn_error}")
        return None

    order_details = {} # Usaremos este diccionario para construir la respuesta
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # 1. Obtener información principal del pedido y entidades relacionadas
            current_app.logger.debug(f"DB_ADMIN_ORDER_DETAIL: Obteniendo información principal para pedido ID {order_id_to_find}")
            cur.execute("""
                SELECT 
                    o.id, o.user_id, o.restaurant_id, o.delivery_address, 
                    o.notes AS delivery_instructions,
                    o.total_amount, o.status, o.ordered_at, o.delivery_type, o.payment_method,
                    o.payment_status,
                    o.delivery_person_id, 
                    o.assigned_drone_id, -- <--- AÑADIR ESTA COLUMNA
                    u_customer.full_name AS customer_name, u_customer.email AS customer_email, u_customer.phone_number AS customer_phone,
                    r.name AS restaurant_name, r.address AS restaurant_address, r.phone_number AS restaurant_phone,
                    u_delivery_person.full_name AS delivery_person_name, 
                    u_delivery_person.phone_number AS delivery_person_phone,
                    d.drone_identifier AS assigned_drone_identifier, -- <--- AÑADIR ESTO (del dron asignado)
                    d.model AS assigned_drone_model                 -- <--- Y ESTO (opcional)
                FROM orders o
                JOIN users u_customer ON o.user_id = u_customer.id
                JOIN restaurants r ON o.restaurant_id = r.id
                LEFT JOIN users u_delivery_person ON o.delivery_person_id = u_delivery_person.id
                LEFT JOIN drones d ON o.assigned_drone_id = d.id -- <--- NUEVO JOIN con la tabla drones
                WHERE o.id = %s;
            """, (order_id_to_find,))
            order_main_info = cur.fetchone()


            if not order_main_info:
                current_app.logger.warning(f"get_order_details_for_admin: Pedido ID {order_id_to_find} no encontrado.")
                # No es necesario cerrar la conexión aquí, el finally lo hará.
                return None 
            
            order_details.update(order_main_info) # Copia los datos principales al diccionario

            # 2. Obtener los ítems del pedido
            current_app.logger.debug(f"DB_ADMIN_ORDER_DETAIL: Obteniendo ítems para pedido ID {order_id_to_find}")
            cur.execute("""
                SELECT 
                    oi.menu_item_id, 
                    mi.name AS item_name, 
                    mi.description AS item_description, 
                    oi.price_at_order AS item_unit_price, -- Precio unitario al momento de la orden
                    oi.quantity, 
                    (oi.quantity * oi.price_at_order) AS item_subtotal -- Calculamos el subtotal aquí
                FROM order_items oi
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE oi.order_id = %s
                ORDER BY mi.name ASC; -- Opcional: ordenar ítems
            """, (order_id_to_find,))
            order_items = cur.fetchall()
            order_details['items'] = order_items # Añadimos la lista de ítems al diccionario principal
            
    except psycopg2.Error as e:
        log_message_db_error = f"Error de BD (psycopg2) al obtener detalles del pedido ID {order_id_to_find} para admin: {e}"
        if current_app:
            current_app.logger.error(log_message_db_error, exc_info=True)
        else:
            print(f"[{datetime.now()}] {log_message_db_error}")
        return None # Indicar error
    except Exception as e_general:
        log_message_general_error = f"Error general en get_order_details_for_admin para pedido ID {order_id_to_find}: {e_general}"
        if current_app:
            current_app.logger.error(log_message_general_error, exc_info=True)
        else:
            print(f"[{datetime.now()}] {log_message_general_error}")
        return None # Indicar error
    finally:
        if conn:
            conn.close()
            # if current_app: # Log opcional
            #     current_app.logger.debug(f"DB_ADMIN_ORDER_DETAIL: Conexión cerrada para pedido ID {order_id_to_find}")
            
    return order_details

# ontener drones activos para asiganarlos en el pedido
def get_active_drones_for_select():
    """Obtiene drones activos (id, identificador, modelo) para selectores."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("get_active_drones_for_select: No se pudo conectar a BD.")
        return []
    drones_list = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, drone_identifier, model FROM drones WHERE status = 'activo' ORDER BY drone_identifier ASC"
            ) # Filtramos por status 'activo'
            drones_list = cur.fetchall()
    # ... (manejo de excepciones y finally como en get_drones_for_select) ...
    except psycopg2.Error as e: # Ejemplo de manejo
        current_app.logger.error(f"Error de BD en get_active_drones_for_select: {e}", exc_info=True)
    finally:
        if conn: conn.close()
    return drones_list

# obtener repartidores activos
def get_active_delivery_personnel_by_roles(role_list):
    """Obtiene usuarios activos con roles específicos (ej. repartidores)."""
    conn = get_db_connection()
    if not conn:
        current_app.logger.error("get_active_delivery_personnel_by_roles: No se pudo conectar a BD.")
        return []

    personnel_list = []
    if not role_list: # Si no se especifican roles, devolver vacío
        return []

    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Creamos placeholders %s dinámicamente para la lista de roles
            role_placeholders = ', '.join(['%s'] * len(role_list))
            query = f"""
                SELECT id, full_name, email, role 
                FROM users 
                WHERE role IN ({role_placeholders}) AND is_active = TRUE 
                ORDER BY full_name ASC
            """
            cur.execute(query, tuple(role_list))
            personnel_list = cur.fetchall()
    # ... (manejo de excepciones y finally) ...
    except psycopg2.Error as e: # Ejemplo de manejo
        current_app.logger.error(f"Error de BD en get_active_delivery_personnel_by_roles: {e}", exc_info=True)
    finally:
        if conn: conn.close()
    return personnel_list

#asignar entrega del pedido

def assign_entity_to_order_in_db(order_id, entity_type, entity_id, new_order_status=None):
    """
    Asigna un dron o un repartidor a un pedido y opcionalmente actualiza el estado del pedido.
    entity_id puede ser None si se está desasignando.
    """
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"assign_entity_to_order_in_db: No se pudo conectar a BD para pedido ID {order_id}")
        return False

    updated_rows = 0
    try:
        with conn.cursor() as cur:
            set_clauses = []
            params = []

            if entity_type == 'drone':
                set_clauses.append("assigned_drone_id = %s")
                params.append(entity_id) # entity_id será el ID del dron o None para desasignar
                set_clauses.append("delivery_person_id = NULL") # Poner el otro a NULL
            elif entity_type == 'person':
                set_clauses.append("delivery_person_id = %s")
                params.append(entity_id) # entity_id será el ID de la persona o None para desasignar
                set_clauses.append("assigned_drone_id = NULL") # Poner el otro a NULL
            else:
                # Si se llega aquí, es un error de lógica en la ruta que llama, ya que entity_type debería ser validado antes.
                current_app.logger.error(f"Tipo de entidad '{entity_type}' inválido en assign_entity_to_order_in_db para pedido ID {order_id}")
                return False 

            if new_order_status:
                # Asegúrate que new_order_status sea un valor válido de tu ENUM order_status_enum
                valid_statuses = ['pending', 'confirmed', 'preparing', 'out_for_delivery', 'delivered', 'cancelled', 'failed']
                if new_order_status in valid_statuses:
                    set_clauses.append("status = %s")
                    params.append(new_order_status)
                else:
                    current_app.logger.warning(f"Estado '{new_order_status}' inválido al asignar entrega para pedido ID {order_id}. No se cambiará el estado.")

            if not set_clauses: # No debería pasar si entity_type es 'drone' o 'person'
                current_app.logger.error(f"No se generaron cláusulas SET para la asignación del pedido ID {order_id}")
                return False

            params.append(order_id) # Para la cláusula WHERE

            sql_query = "UPDATE orders SET " + ", ".join(set_clauses) + " WHERE id = %s;"

            current_app.logger.debug(f"Assign query: {cur.mogrify(sql_query, tuple(params)).decode('utf-8', 'ignore')}")
            cur.execute(sql_query, tuple(params))
            updated_rows = cur.rowcount
            conn.commit()

            if updated_rows > 0:
                assigned_entity_log = f"{entity_type} ID {entity_id if entity_id else 'ninguno (desasignado)'}"
                status_log = f"Nuevo estado: {new_order_status}" if new_order_status else "estado sin cambios"
                current_app.logger.info(f"Pedido ID {order_id} actualizado. Asignado {assigned_entity_log}. {status_log}.")
            else:
                current_app.logger.warning(f"No se actualizó el pedido ID {order_id} al asignar entrega (podría no existir o datos iguales).")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al asignar entrega para pedido ID '{order_id}': {e}", exc_info=True)
        if conn: conn.rollback()
    except Exception as e_general:
        current_app.logger.error(f"Error general en assign_entity_to_order_in_db para pedido ID {order_id}: {e_general}", exc_info=True)
        if conn: conn.rollback()
    finally:
        if conn:
            conn.close()
    return updated_rows > 0



def get_assigned_orders_for_delivery_person_from_db(delivery_person_user_id):
    """
    Obtiene los pedidos activos asignados a un repartidor específico.
    Incluye detalles del restaurante (para recogida) y del cliente (para entrega).
    """
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"get_assigned_orders_for_delivery_person: No se pudo conectar a BD para repartidor ID {delivery_person_user_id}")
        return []
    
    assigned_orders = []
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
           
            relevant_statuses = ('confirmed', 'preparing', 'out_for_delivery')
            
            query = """
                SELECT 
                    o.id, 
                    o.delivery_address AS customer_delivery_address, 
                    o.status, 
                    o.notes AS order_notes,
                    o.delivery_type,
                    r.name AS restaurant_name, 
                    r.address AS restaurant_address, 
                    r.phone_number AS restaurant_phone,
                    u_customer.full_name AS customer_name,
                    u_customer.phone_number AS customer_phone 
                FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.id
                JOIN users u_customer ON o.user_id = u_customer.id
                WHERE o.delivery_person_id = %s 
                  AND o.status IN %s
                ORDER BY o.ordered_at ASC; -- Podrías querer ordenar por prioridad o tiempo estimado
            """
            cur.execute(query, (delivery_person_user_id, relevant_statuses))
            assigned_orders = cur.fetchall()
            current_app.logger.info(f"Encontrados {len(assigned_orders)} pedidos asignados para repartidor ID {delivery_person_user_id}")
            
    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener pedidos para repartidor ID '{delivery_person_user_id}': {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_assigned_orders_for_delivery_person para repartidor ID {delivery_person_user_id}: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return assigned_orders



def get_assigned_order_details_for_delivery_db(order_id, delivery_person_user_id):
    """
    Obtiene los detalles de un pedido específico asignado a un repartidor.
    Verifica que el pedido esté asignado al repartidor solicitante.
    """
    conn = get_db_connection()
    if not conn:
        current_app.logger.error(f"get_assigned_order_details_for_delivery: No se pudo conectar a BD para pedido ID {order_id}")
        return None

    order_details = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Seleccionamos detalles del pedido, restaurante (recogida), y cliente (entrega)
            # y verificamos que el delivery_person_id coincida.
            query = """
                SELECT 
                    o.id AS order_id, 
                    o.delivery_address AS customer_delivery_address, 
                    o.status AS order_status, 
                    o.notes AS order_notes,
                    o.delivery_type,
                    o.total_amount,
                    r.name AS restaurant_name, 
                    r.address AS restaurant_address, 
                    r.phone_number AS restaurant_phone,
                    u_customer.full_name AS customer_name,
                    u_customer.phone_number AS customer_phone,
                    (
                        SELECT STRING_AGG(mi.name || ' (x' || oi.quantity || ')', ', ')
                        FROM order_items oi
                        JOIN menu_items mi ON oi.menu_item_id = mi.id
                        WHERE oi.order_id = o.id
                    ) as item_summary 
                FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.id
                JOIN users u_customer ON o.user_id = u_customer.id
                WHERE o.id = %s AND o.delivery_person_id = %s 
                  AND o.status IN ('confirmed', 'preparing', 'out_for_delivery'); 
                  -- Solo mostrar pedidos que el repartidor necesita gestionar activamente
            """
            # Ajusta los relevant_statuses según necesites
            cur.execute(query, (order_id, delivery_person_user_id))
            order_details = cur.fetchone()

            if order_details:
                current_app.logger.info(f"Detalles del pedido ID {order_id} obtenidos para repartidor ID {delivery_person_user_id}.")
            else:
                current_app.logger.warning(f"Repartidor ID {delivery_person_user_id} intentó acceder a detalles del pedido ID {order_id} no asignado o en estado incorrecto.")

    except psycopg2.Error as e:
        current_app.logger.error(f"Error de BD al obtener detalles de pedido asignado ID '{order_id}': {e}", exc_info=True)
    except Exception as e_general:
        current_app.logger.error(f"Error general en get_assigned_order_details_for_delivery para pedido ID {order_id}: {e_general}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return order_details

# app/db.py
# ... (importaciones) ...

def get_user_profile_data(user_id): # O renómbrala/modifícala
    """Obtiene los datos de un usuario para su perfil por su ID."""
    conn = get_db_connection()
    if not conn:
        # ... (manejo de error) ...
        return None
    user_data = None
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # ASEGÚRATE QUE LA COLUMNA profile_picture_url EXISTA EN TU TABLA users
            cur.execute(
                "SELECT id, email, full_name, role, phone_number, profile_picture_url "
                "FROM users WHERE id = %s AND is_active = TRUE", 
                (user_id,)
            )
            user_data = cur.fetchone()
    # ... (except y finally blocks) ...
    finally: # Ejemplo simple de finally
        if conn:
            conn.close()
    return user_data

def update_user_profile_data(user_id, full_name, phone_number): # Añade otros campos como 'address' si es necesario
    """Actualiza nombre y teléfono. Otros campos pueden añadirse."""
    conn = get_db_connection()
    if not conn: return False
    updated_rows = 0
    try:
        with conn.cursor() as cur:
            # Aquí puedes construir una lista de campos a actualizar para más flexibilidad
            # Por ahora, actualizamos estos dos.
            fields_to_update = []
            params = []
            if full_name is not None: # Permite actualizar campos individualmente si se desea
                fields_to_update.append("full_name = %s")
                params.append(full_name)
            if phone_number is not None:
                fields_to_update.append("phone_number = %s")
                params.append(phone_number)
            
            if not fields_to_update: # No hay nada que actualizar
                return True # O False si consideras que es un error no enviar nada

            params.append(user_id) # Para el WHERE
            
            query = f"UPDATE users SET {', '.join(fields_to_update)} WHERE id = %s;"
            
            cur.execute(query, tuple(params))
            updated_rows = cur.rowcount
            conn.commit()
            current_app.logger.debug(f"DB: Actualizando perfil para user {user_id}. Query: {cur.query.decode if cur.query else 'N/A'}")
    except psycopg2.Error as e:
        current_app.logger.error(f"Error DB actualizando perfil (datos) para user '{user_id}': {e}", exc_info=True)
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return updated_rows > 0

def update_user_profile_picture_url(user_id, db_pic_path):
    """Actualiza solo la URL de la foto de perfil."""
    conn = get_db_connection()
    if not conn: return False
    updated_rows = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET profile_picture_url = %s WHERE id = %s;",
                (db_pic_path, user_id)
            )
            updated_rows = cur.rowcount
            conn.commit()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error DB actualizando URL foto perfil user '{user_id}': {e}", exc_info=True)
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return updated_rows > 0

def verify_user_password(user_id, password_to_check):
    """Verifica la contraseña actual de un usuario (requiere el hash de la BD)."""
    conn = get_db_connection()
    if not conn: return False
    password_hash_from_db = None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            if result:
                password_hash_from_db = result[0]
    except psycopg2.Error as e:
        current_app.logger.error(f"Error DB obteniendo hash para user '{user_id}': {e}")
        return False
    finally:
        if conn: conn.close()
    
    if password_hash_from_db and check_password_hash(password_hash_from_db, password_to_check):
        return True
    current_app.logger.warning(f"Fallo verificación contraseña para user {user_id}")
    return False

def update_user_password_hash(user_id, new_plain_password):
    """Hashea y actualiza la contraseña de un usuario."""
    conn = get_db_connection()
    if not conn: return False
    updated_rows = 0
    try:
        new_hashed_password = generate_password_hash(new_plain_password) # Hashear aquí
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s;",
                (new_hashed_password, user_id)
            )
            updated_rows = cur.rowcount
            conn.commit()
    except psycopg2.Error as e:
        current_app.logger.error(f"Error DB actualizando hash contraseña para user '{user_id}': {e}", exc_info=True)
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return updated_rows > 0