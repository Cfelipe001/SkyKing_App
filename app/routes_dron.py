# app/routes_dron.py
from flask import render_template, jsonify, current_app
from datetime import datetime, timezone, timedelta # timedelta es necesaria para get_historical_drone_telemetry

# Importamos la función de base de datos
from .db import get_historical_drone_telemetry

def init_dron_routes(app):
    """
    Inicializa las rutas relacionadas con los datos del dron.
    """

    @app.route('/datosDron.html')
    def show_datos_dron_page(): # Nombre de función ligeramente diferente
        return render_template('datosDron.html')

    @app.route('/api/datos-iniciales')
    def get_datos_iniciales_api():
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_app.logger.info(f"[{current_time_str}] API: Solicitud recibida para /api/datos-iniciales")

        try:
            # Llama a la función de db.py para obtener los datos crudos
            datos_raw = get_historical_drone_telemetry(hours_ago=1) # pide datos de la última hora

            if datos_raw is None: # Si la función de BD indica un error grave (ej. no conexión)
                current_app.logger.error(f"[{current_time_str}] API: Error al obtener datos históricos de la BD.")
                return jsonify({"error": "Error interno del servidor al obtener datos"}), 500
            
            # --- Lógica de Organización de Datos (copiada de tu run.py original) ---
            # Esta lógica transforma la lista de tuplas de la BD al formato que espera tu frontend.
            datos_organizados = {'timestamps': []} # El que espera el frontend
            temp_data_by_timestamp = {} # Temporal para agrupar por timestamp
            all_telemetry_keys = set()

            for telemetry_name, value, ts_db_obj in datos_raw:
                # Asegurar que el timestamp es string ISO y UTC para el cliente
                ts_iso = ts_db_obj.astimezone(timezone.utc).isoformat()

                all_telemetry_keys.add(telemetry_name)
                if ts_iso not in temp_data_by_timestamp:
                    temp_data_by_timestamp[ts_iso] = {}
                
                try: # Intentar convertir el valor a float, si no, dejar como string
                    numeric_value = float(value)
                except (ValueError, TypeError):
                    numeric_value = str(value)
                temp_data_by_timestamp[ts_iso][telemetry_name] = numeric_value

            sorted_timestamps_iso = sorted(temp_data_by_timestamp.keys())
            datos_organizados['timestamps'] = sorted_timestamps_iso

            # Inicializar listas para cada clave de telemetría
            for key in all_telemetry_keys:
                datos_organizados[key] = [None] * len(sorted_timestamps_iso) # Llenar con None

            # Poblar las listas con los valores correspondientes
            for i, ts_iso_key in enumerate(sorted_timestamps_iso):
                for telemetry_key_data in all_telemetry_keys:
                    if telemetry_key_data in temp_data_by_timestamp[ts_iso_key]:
                        datos_organizados[telemetry_key_data][i] = temp_data_by_timestamp[ts_iso_key][telemetry_key_data]
            # --- Fin de Lógica de Organización de Datos ---
            
            current_app.logger.info(f"[{current_time_str}] API: Enviando {len(datos_organizados['timestamps'])} puntos de datos iniciales.")
            return jsonify(datos_organizados)

        except Exception as e:
            current_app.logger.error(f"[{current_time_str}] API: Error general procesando /api/datos-iniciales: {e}", exc_info=True)
            return jsonify({"error": "Error inesperado del servidor al procesar la solicitud"}), 500