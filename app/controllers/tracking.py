# app/routes_tracking.py
from flask import render_template, abort, session, flash, redirect, url_for, current_app
# Importa las funciones de db.py necesarias
from .db import get_order_for_tracking_by_id_and_user, get_latest_drone_speed_from_telemetry

# Coordenadas del centro de Bucaramanga (Parque Santander aprox.)
BUCARAMANGA_CENTER_LAT = 7.1193
BUCARAMANGA_CENTER_LON = -73.1228

def init_tracking_routes(app):

    @app.route('/seguimiento/pedido/<int:order_id>')
    def track_order_page(order_id):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para ver el seguimiento de tu pedido.', 'warning')
            session['next_url'] = url_for('track_order_page', order_id=order_id)
            return redirect(url_for('show_login_page_auth'))

        order = get_order_for_tracking_by_id_and_user(order_id, session['user_id'])

        if not order:
            current_app.logger.warning(f"Intento de seguimiento para pedido ID {order_id} no encontrado.")
            abort(404)

        # Verificación de permiso: el usuario debe ser el dueño del pedido
        # O podrías tener un rol de 'admin' que pueda ver todos.
        # Asumimos que 'user_id' en la sesión es un integer.
        if order['user_id'] != session['user_id']:
            # Aquí podrías verificar si el usuario es admin, ej: if session.get('role') != 'admin':
            flash('No tienes permiso para ver el seguimiento de este pedido.', 'danger')
            return redirect(url_for('my_orders')) # Redirigir a su lista de pedidos

        tracking_info = {
            'order_id': order['id'],
            'restaurant_name': order.get('restaurant_name', 'N/A'),
            'delivery_type': order['delivery_type'],
            'status': order.get('status', 'Desconocido'),
            'delivery_entity_name': 'No asignado',
            'delivery_entity_contact': 'N/A',
            'current_speed': 'N/A',
            'map_lat': BUCARAMANGA_CENTER_LAT, # Latitud inicial para el mapa
            'map_lon': BUCARAMANGA_CENTER_LON, # Longitud inicial para el mapa
            'map_zoom': 15 # Zoom inicial del mapa
        }

        if order['delivery_type'] == 'drone':
            tracking_info['delivery_entity_name'] = "Dron Skyking One" # Nombre placeholder
            # Si tuviéramos ID específico del dron asignado y en la telemetría:
            # drone_actual_speed = get_latest_drone_speed_from_telemetry() # Asume un solo dron por ahora
            # if drone_actual_speed is not None:
            #     tracking_info['current_speed'] = f"{drone_actual_speed} km/h" # Asumiendo que la velocidad está en km/h
            # else:
            #     tracking_info['current_speed'] = "Velocidad no disponible"
            # Como no hay lat/lon en telemetría, usamos el centro de Bucaramanga.
            # Aquí podríamos simular un movimiento más adelante.

        elif order['delivery_type'] in ['motorcycle', 'bicycle']:
            if order.get('delivery_person_name'):
                tracking_info['delivery_entity_name'] = order['delivery_person_name']
                tracking_info['delivery_entity_contact'] = order.get('delivery_person_phone', 'No disponible')
            else:
                tracking_info['delivery_entity_name'] = "Repartidor en camino"
            # Ubicación simulada en el centro por ahora

        # Crear la plantilla 'tracking/seguimiento_pedido.html'
        # Asegúrate que la ruta a la plantilla sea correcta (con o sin 'tracking/')
        return render_template('order/seguimiento_pedido.html', 
                               order=order,  # Datos originales del pedido
                               tracking=tracking_info) # Datos específicos para la UI de seguimiento