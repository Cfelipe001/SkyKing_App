# app/routes_delivery.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app
from functools import wraps # Para el decorador
from .db import get_assigned_orders_for_delivery_person_from_db, get_assigned_order_details_for_delivery_db

from .routes_auth import login_required 


delivery_bp = Blueprint(
    'delivery',  # Nombre del Blueprint
    __name__,
    url_prefix='/repartidor',        
    template_folder='delivery'       
)

# Decorador específico para roles de repartidor (opcional, podríamos hacer el check en la ruta)
def delivery_person_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') not in ['repartidor_moto', 'repartidor_bici']:
            flash('No tienes permiso para acceder a esta sección de repartidores.', 'danger')
            return redirect(url_for('home_page')) # O a donde consideres apropiado
        return f(*args, **kwargs)
    return decorated_function




@delivery_bp.route('/dashboard')
@login_required
@delivery_person_required # Asumiendo que definiste este decorador como hablamos
def repartidor_dashboard():
    user_id = session.get('user_id')
    user_email = session.get('user_email', 'Repartidor')

    try:
        assigned_orders = get_assigned_orders_for_delivery_person_from_db(user_id)
    except Exception as e:
        current_app.logger.error(f"Error obteniendo pedidos asignados para repartidor {user_id}: {e}", exc_info=True)
        flash("Ocurrió un error al cargar tus pedidos asignados.", "danger")
        assigned_orders = []

    current_app.logger.info(f"Repartidor {user_email} (ID: {user_id}) accedió a su dashboard. Pedidos asignados: {len(assigned_orders)}")

    return render_template('delivery/dashboard_repartidor.html', 
                           orders=assigned_orders, 
                           user_email=user_email)



@delivery_bp.route('/pedido/<int:order_id>/detalles-entrega')
@login_required
@delivery_person_required 
def view_delivery_order_details(order_id):
    user_id = session.get('user_id')

    order_info = get_assigned_order_details_for_delivery_db(order_id, user_id)

    if not order_info:
        flash(f"No se encontraron detalles para el pedido #{order_id}, o no está asignado a ti en un estado activo.", "warning")
        return redirect(url_for('delivery.repartidor_dashboard'))

    # Coordenadas para el mapa (por ahora, placeholders o centro de la ciudad)
    # Idealmente, estas vendrían de geocodificar las direcciones o de la BD
    pickup_coords = {'lat': 7.1193, 'lon': -73.1228} # Centro Bucaramanga (Placeholder Restaurante)
    delivery_coords = {'lat': 7.1250, 'lon': -73.1250} # Un punto cercano (Placeholder Cliente)
    # En una implementación real, si order_info.restaurant_lat/lon y order_info.customer_lat/lon existen, úsalas.

    return render_template('delivery/delivery_order_details_map.html', 
                           order=order_info,
                           pickup_coords=pickup_coords,
                           delivery_coords=delivery_coords)