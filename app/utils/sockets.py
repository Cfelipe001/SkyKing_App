# app/sockets.py
from flask import request, current_app # current_app para el logger en el hilo
# No importamos 'socketio' directamente de flask_socketio aquí para definir manejadores,
# sino que usaremos la instancia que se le pasará a una función de inicialización.
from datetime import datetime, timezone, timedelta
import time
import psycopg2

# Importamos las funciones de base de datos que necesitamos
from .db import get_latest_drone_telemetry_timestamp, get_drone_telemetry_since

# Esta variable almacenará la instancia de SocketIO una vez inicializada en app/__init__.py
# y pasada a init_socket_handlers.
_socketio = None

def init_socket_handlers(socketio_instance):
    """
    Inicializa los manejadores de eventos de SocketIO.
    Esta función será llamada desde app/__init__.py después de crear la instancia de SocketIO.
    """
    global _socketio
    _socketio = socketio_instance

    @_socketio.on('connect')
    def handle_socket_connect_event(): # Renombrado para evitar colisión si Flask tiene 'handle_connect'
        # No es necesario current_app aquí si solo usas request y _socketio global
        # app_instance.logger.info(f"Cliente conectado: {request.sid}")
        print(f"[{datetime.now()}] Sockets: Cliente conectado: {request.sid}")

    @_socketio.on('disconnect')
    def handle_socket_disconnect_event():
        # app_instance.logger.info(f"Cliente desconectado: {request.sid}")
        print(f"[{datetime.now()}] Sockets: Cliente desconectado: {request.sid}")

def socket_emitter_thread(app_instance, socketio_instance_for_thread):
    """
    Esta función se ejecuta en un hilo para consultar la base de datos
    y emitir datos nuevos a través de WebSocket.
    """
    # Es importante pasar socketio_instance_for_thread explícitamente si _socketio
    # podría no estar disponible o si queremos ser más explícitos para el hilo.
    # Si _socketio se establece globalmente antes de que el hilo comience, también funcionaría.
    sio_to_use = socketio_instance_for_thread if socketio_instance_for_thread else _socketio

    with app_instance.app_context(): # Necesario para current_app.logger y para las funciones de db.py
        current_app.logger.info(f"[{datetime.now()}] Iniciando hilo de emisión de datos SocketIO...")
        ultimo_timestamp_conocido = None
        contador_sin_datos = 0

        while True:
            try:
                # Las operaciones de BD ahora usan funciones de db.py
                # que a su vez usan current_app para la configuración
                ultimo_timestamp_db = get_latest_drone_telemetry_timestamp()

                if ultimo_timestamp_db is None:
                    # current_app.logger.debug(f"[{datetime.now()}] SocketEmitter: No hay timestamps en la BD aún.")
                    time.sleep(5) # Espera un poco si la BD está vacía
                    continue
                
                # Asegurarse que ultimo_timestamp_db sea timezone-aware si viene de la BD así
                if ultimo_timestamp_db.tzinfo is None:
                     ultimo_timestamp_db = ultimo_timestamp_db.replace(tzinfo=timezone.utc)


                if ultimo_timestamp_conocido is None:
                    current_app.logger.info(f"[{datetime.now()}] SocketEmitter: Primera ejecución o reinicio, timestamp conocido: {ultimo_timestamp_db}")
                    ultimo_timestamp_conocido = ultimo_timestamp_db
                    time.sleep(1) # Pequeña pausa antes de la siguiente verificación
                    continue
                 
                # Asegurarse que ultimo_timestamp_conocido sea timezone-aware para la comparación
                if ultimo_timestamp_conocido.tzinfo is None:
                    ultimo_timestamp_conocido = ultimo_timestamp_conocido.replace(tzinfo=timezone.utc)


                if ultimo_timestamp_db > ultimo_timestamp_conocido:
                    nuevos_datos_raw = get_drone_telemetry_since(ultimo_timestamp_conocido, ultimo_timestamp_db)

                    if nuevos_datos_raw:
                        current_app.logger.info(f"[{datetime.now()}] SocketEmitter: Encontrados {len(nuevos_datos_raw)} nuevos registros entre {ultimo_timestamp_conocido} y {ultimo_timestamp_db}.")
                        datos_organizados_para_emitir = {}
                        max_ts_en_lote = ultimo_timestamp_conocido # El timestamp más reciente de ESTE lote

                        for telemetry_name, value, timestamp_val_db in nuevos_datos_raw:
                            # Asegurar que el timestamp es string ISO y UTC para el cliente
                            ts_iso = timestamp_val_db.astimezone(timezone.utc).isoformat()
                            # .isoformat() para datetime con tzinfo ya incluye el offset o 'Z'

                            if telemetry_name not in datos_organizados_para_emitir:
                                datos_organizados_para_emitir[telemetry_name] = []
                            
                            datos_organizados_para_emitir[telemetry_name].append({
                                'value': value,
                                'timestamp': ts_iso
                            })
                            if timestamp_val_db > max_ts_en_lote:
                                max_ts_en_lote = timestamp_val_db
                        
                        if datos_organizados_para_emitir: # Solo emitir si hay algo organizado
                            if sio_to_use:
                                sio_to_use.emit('nuevos_datos', datos_organizados_para_emitir)
                                current_app.logger.info(f"[{datetime.now()}] SocketEmitter: Datos emitidos. {len(datos_organizados_para_emitir)} series de telemetría.")
                            else:
                                current_app.logger.error(f"[{datetime.now()}] SocketEmitter: ERROR CRÍTICO - instancia de socketio no disponible para emitir.")

                        ultimo_timestamp_conocido = max_ts_en_lote # Actualizar con el timestamp más reciente procesado en este lote
                        current_app.logger.debug(f"[{datetime.now()}] SocketEmitter: Timestamp conocido actualizado a: {ultimo_timestamp_conocido}")
                        contador_sin_datos = 0
                    else:
                        # Esto podría pasar si el MAX(timestamp) cambió pero los datos exactos en el rango > ultimo_conocido y <= nuevo_max ya no están o la consulta es muy específica.
                        # Es más seguro actualizar ultimo_timestamp_conocido al nuevo máximo de la BD para evitar saltarse datos.
                        current_app.logger.info(f"[{datetime.now()}] SocketEmitter: MAX DB ({ultimo_timestamp_db}) > Conocido ({ultimo_timestamp_conocido}), pero la consulta no devolvió filas. Actualizando conocido al MAX DB.")
                        ultimo_timestamp_conocido = ultimo_timestamp_db
                        contador_sin_datos +=1
                else: # No hay nuevos timestamps en la BD (ultimo_timestamp_db <= ultimo_timestamp_conocido)
                    contador_sin_datos += 1
                
                if contador_sin_datos > 0 and (contador_sin_datos == 1 or contador_sin_datos % 60 == 0) : # Loguear cada minuto si no hay datos
                    current_app.logger.debug(f"[{datetime.now()}] SocketEmitter: No hay nuevos datos detectados (Ciclo {contador_sin_datos}). MAX DB: {ultimo_timestamp_db}, Conocido: {ultimo_timestamp_conocido}")

            except psycopg2.InterfaceError as e: # Errores de conexión que pueden cerrarla
                current_app.logger.error(f"[{datetime.now()}] SocketEmitter: Error de interfaz psycopg2 (reintentando conexión): {e}")
                time.sleep(10) # Esperar antes de reintentar todo el ciclo
            except psycopg2.OperationalError as e: # Otros errores operacionales de BD
                current_app.logger.error(f"[{datetime.now()}] SocketEmitter: Error operacional de BD (reintentando conexión): {e}")
                time.sleep(10)
            except Exception as e:
                current_app.logger.error(f"[{datetime.now()}] SocketEmitter: Error general inesperado en emisión de datos: {e}", exc_info=True)
                time.sleep(5) # Esperar un poco antes de continuar
            
            time.sleep(1) # Intervalo base del bucle del emisor