# app/services.py
import requests
import json
from datetime import datetime, timezone # Asegúrate de importar timezone para datetime.fromisoformat
import time
from flask import current_app # Para acceder a la configuración de la app (app.config)
from .db import save_drone_telemetry_batch # Importamos la función para guardar en BD

def azure_iot_data_fetcher_thread(app_instance):
    """
    Esta función se ejecuta en un hilo para extraer datos de Azure IoT Central
    y luego llama a una función de db.py para guardarlos.
    Necesita la instancia de la app para crear un contexto de aplicación.
    """
    with app_instance.app_context(): # Esencial para que current_app funcione en el hilo
        current_app.logger.info(f"[{datetime.now()}] Iniciando hilo de extracción de datos de Azure IoT Central...")

        # Accedemos a la configuración a través de current_app.config
        device_id = current_app.config['IOT_CENTRAL_DEVICE_ID']
        api_version = current_app.config['IOT_CENTRAL_API_VERSION']
        base_url = current_app.config['IOT_CENTRAL_BASE_URL']
        headers = current_app.config['IOT_CENTRAL_HEADERS']
        telemetry_names_to_extract = current_app.config['IOT_CENTRAL_TELEMETRY_NAMES']
        interval_seconds = current_app.config['IOT_CENTRAL_EXECUTION_INTERVAL_SECONDS']

        while True:
            extracted_data_for_db_insert = [] # Lista de tuplas (name, value, timestamp_dt)
            current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_app.logger.info(f"\n[{current_time_str}] --- Iniciando nuevo ciclo de extracción IoT Central ---")
            current_app.logger.debug(f"[{current_time_str}] Dispositivo: {device_id}. Solicitando: {', '.join(telemetry_names_to_extract)}")

            for telemetry_name in telemetry_names_to_extract:
                telemetry_url = f'{base_url}/api/devices/{device_id}/telemetry/{telemetry_name}?api-version={api_version}'
                try:
                    response = requests.get(telemetry_url, headers=headers, timeout=10)
                    response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
                    data_json = response.json()

                    if isinstance(data_json, dict) and 'value' in data_json and 'timestamp' in data_json:
                        value = data_json['value']
                        timestamp_str = data_json['timestamp']
                        try:
                            # Convertir a datetime y asegurar que sea timezone-aware (UTC)
                            timestamp_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if timestamp_dt.tzinfo is None: # Si por alguna razón no tiene tzinfo
                                timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
                            
                            extracted_data_for_db_insert.append((telemetry_name, value, timestamp_dt))
                        except ValueError:
                            current_app.logger.warning(f"[{current_time_str}] - Advertencia: No se pudo parsear timestamp '{timestamp_str}' para '{telemetry_name}'.")
                    else:
                        current_app.logger.warning(f"[{current_time_str}] - Advertencia: Respuesta para '{telemetry_name}' no tiene estructura esperada. Data: {data_json}")
                except requests.exceptions.RequestException as e:
                    current_app.logger.error(f"[{current_time_str}] - Error HTTP para '{telemetry_name}': {e}")
                except json.JSONDecodeError:
                    current_app.logger.error(f"[{current_time_str}] - Error: Respuesta para '{telemetry_name}' no es JSON válido. Contenido: {response.text[:200]}...")
                except Exception as e:
                    current_app.logger.error(f"[{current_time_str}] - Error inesperado procesando '{telemetry_name}': {e}")

            if not extracted_data_for_db_insert:
                current_app.logger.info(f"[{current_time_str}] No se extrajeron datos válidos de IoT Central en este ciclo.")
            else:
                # Llamamos a la función de db.py para guardar los datos
                # Esta función ya maneja su propia conexión y logging de errores de BD
                rows_inserted = save_drone_telemetry_batch(extracted_data_for_db_insert)
                
                if rows_inserted == -1: # Error de conexión en db.py
                    current_app.logger.error(f"[{current_time_str}] AzureFetcher: Fallo de conexión a BD al intentar guardar telemetría.")
                elif rows_inserted == -2: # Error de inserción en db.py
                    current_app.logger.error(f"[{current_time_str}] AzureFetcher: Error de inserción en BD al intentar guardar telemetría.")
                elif rows_inserted > 0:
                    current_app.logger.info(f"[{current_time_str}] AzureFetcher: {rows_inserted} telemetrías enviadas a guardar en BD.")
                else: # 0 rows insertados, pero sin error reportado por db.py
                     current_app.logger.info(f"[{current_time_str}] AzureFetcher: Lote de telemetría procesado, pero no se insertaron filas (posiblemente datos ya procesados o vacíos).")


            current_app.logger.info(f"[{current_time_str}] Esperando {interval_seconds} segundos antes del próximo ciclo de extracción IoT...")
            time.sleep(interval_seconds)