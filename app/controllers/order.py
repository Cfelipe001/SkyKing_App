# app/routes_order.py
from flask import render_template, request, jsonify, session, url_for, redirect, flash, current_app, abort

# Importamos las funciones de base de datos que necesitamos
from .db import (
    get_all_restaurants,
    get_orders_by_user_id, 
    get_restaurant_by_id, 
    get_menu_items_by_restaurant_id,
    get_menu_item_by_id, # Lo necesitaremos para añadir al carrito/pedido
    create_new_order # Lo necesitaremos más adelante
)

def init_order_routes(app):
    """
    Inicializa las rutas para el flujo de pedidos.
    """

    @app.route('/restaurantes')
    def list_restaurants():
        """Muestra la lista de todos los restaurantes activos."""
        try:
            restaurants = get_all_restaurants() # Llama a la función de db.py
            # 'order/restaurants_list.html' asume que tienes una subcarpeta 'order' en 'templates'
            return render_template('order/restaurants_list.html', restaurants=restaurants)
            current_app.logger.info(f"[ROUTE_DEBUG] list_restaurants - Restaurantes para la plantilla: {restaurants}") ###########
        except Exception as e:
            current_app.logger.error(f"Error al listar restaurantes: {e}", exc_info=True)
            abort(500) # Error interno del servidor

    @app.route('/restaurantes/<int:restaurant_id>/menu')
    def restaurant_menu(restaurant_id):
        """Muestra el menú de un restaurante específico."""
        try:
            restaurant = get_restaurant_by_id(restaurant_id)
            if not restaurant:
                current_app.logger.warning(f"Intento de acceso a menú de restaurante no existente o inactivo: ID {restaurant_id}")
                abort(404) # No encontrado

            menu_items = get_menu_items_by_restaurant_id(restaurant_id)
            return render_template('order/restaurant_menu.html', restaurant=restaurant, menu_items=menu_items)
        except Exception as e:
            current_app.logger.error(f"Error al mostrar menú del restaurante ID {restaurant_id}: {e}", exc_info=True)
            abort(500)

    # --- Rutas para el Carrito y Proceso de Pedido (las desarrollaremos en los siguientes pasos) ---

    @app.route('/carrito/agregar/<int:menu_item_id>', methods=['POST'])
    def add_to_cart(menu_item_id):
        """Añade un ítem al carrito (guardado en la sesión)."""
        # Verificar que el usuario esté logueado
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para añadir ítems al carrito.', 'warning')
            # Guardar la URL a la que se intentaba acceder para redirigir después del login
            session['next_url'] = url_for('order_routes.restaurant_menu', 
                                          restaurant_id=request.form.get('restaurant_id_for_redirect')) # Necesitarás pasar esto en el form
            return redirect(url_for('auth_routes.show_login_page_auth')) # Asumiendo nombre de endpoint de login

        menu_item = get_menu_item_by_id(menu_item_id)
        if not menu_item:
            flash('El ítem que intentas añadir no existe o no está disponible.', 'danger')
            # Redirigir a la página anterior o a la lista de restaurantes
            return redirect(request.referrer or url_for('order_routes.list_restaurants'))

        # Obtener cantidad del formulario (si no se envía, default a 1)
        try:
            quantity = int(request.form.get('quantity', 1))
            if quantity < 1:
                quantity = 1
        except ValueError:
            quantity = 1

        # Inicializar carrito en sesión si no existe
        cart = session.get('cart', {}) # El carrito será un dict {menu_item_id: {'name': ..., 'price': ..., 'quantity': ...}}
        
        cart_item_id_str = str(menu_item_id) # Usar string como clave en dict de sesión

        if cart_item_id_str in cart:
            cart[cart_item_id_str]['quantity'] += quantity
        else:
            cart[cart_item_id_str] = {
                'name': menu_item['name'],
                'price': float(menu_item['price']), # Asegurar que el precio sea float para cálculos
                'quantity': quantity,
                'restaurant_id': menu_item['restaurant_id'] # Guardar para saber de qué restaurante es el ítem
            }
        
        session['cart'] = cart # Guardar el carrito actualizado en la sesión
        session.modified = True # Importante para que Flask guarde la sesión si se modifica un objeto mutable como un dict

        flash(f"{menu_item['name']} añadido al carrito!", 'success')
        # Redirigir de vuelta al menú del restaurante del ítem añadido
        return redirect(url_for('restaurant_menu', restaurant_id=menu_item['restaurant_id']))


    @app.route('/carrito')
    def view_cart():
        """Muestra el contenido del carrito."""
        cart = session.get('cart', {})
        total_cart_amount = 0
        current_app.logger.info(f"[DEBUG_CART] Contenido de session['cart']: {cart}")
        # Agrupar items por restaurante
        items_by_restaurant = {}
        if cart:
            for item_id, item_data in cart.items():
                restaurant_id = item_data['restaurant_id']
                if restaurant_id not in items_by_restaurant:
                    # Obtener nombre del restaurante (podríamos optimizar esto más adelante)
                    # Por ahora, una consulta simple. Considera si esto es muy costoso si hay muchos restaurantes.
                    # Alternativa: guardar nombre del restaurante en la sesión también, o pasar solo IDs y resolver en plantilla.
                    restaurant_info = get_restaurant_by_id(restaurant_id) # Llamada a BD
                    items_by_restaurant[restaurant_id] = {
                        'name': restaurant_info['name'] if restaurant_info else 'Restaurante Desconocido',
                        'items': [],
                        'subtotal': 0
                    }
                
                item_subtotal = item_data['price'] * item_data['quantity']
                items_by_restaurant[restaurant_id]['items'].append({
                    'id_str': item_id, # El ID del menu_item
                    'id_int': int(item_id),
                    'name': item_data['name'],
                    'price': item_data['price'],
                    'quantity': item_data['quantity'],
                    'subtotal': item_subtotal
                })
                items_by_restaurant[restaurant_id]['subtotal'] += item_subtotal
                total_cart_amount += item_subtotal
        
        # Pasar los IDs de restaurante para que la plantilla pueda generar enlaces de "volver al menú"
        restaurant_ids = list(items_by_restaurant.keys())

        return render_template('order/view_cart.html', 
                               cart_by_restaurant=items_by_restaurant, 
                               total_cart_amount=total_cart_amount,
                               restaurant_ids=restaurant_ids)


    @app.route('/carrito/actualizar/<string:menu_item_id_str>', methods=['POST'])
    def update_cart_item(menu_item_id_str):
        cart = session.get('cart', {})
        try:
            new_quantity = int(request.form.get('quantity'))
        except (ValueError, TypeError):
            flash('Cantidad inválida.', 'danger')
            return redirect(url_for('view_cart'))

        if menu_item_id_str in cart:
            if new_quantity > 0:
                cart[menu_item_id_str]['quantity'] = new_quantity
                flash('Carrito actualizado.', 'success')
            elif new_quantity == 0: # Eliminar ítem si la cantidad es 0
                del cart[menu_item_id_str]
                flash('Ítem eliminado del carrito.', 'info')
        else:
            flash('Ítem no encontrado en el carrito.', 'danger')
        
        session['cart'] = cart
        session.modified = True
        return redirect(url_for('view_cart'))

    @app.route('/carrito/eliminar/<string:menu_item_id_str>', methods=['POST']) # O podría ser GET con un botón
    def remove_from_cart(menu_item_id_str):
        cart = session.get('cart', {})
        if menu_item_id_str in cart:
            del cart[menu_item_id_str]
            flash('Ítem eliminado del carrito.', 'success')
        else:
            flash('Ítem no encontrado en el carrito.', 'danger')
        session['cart'] = cart
        session.modified = True
        return redirect(url_for('view_cart'))


    @app.route('/pedido/checkout', methods=['GET', 'POST'])
    def checkout():
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para realizar un pedido.', 'warning')
            # Guardar la URL actual o la del checkout para redirigir después del login
            # Si venimos con un GET y restaurant_id, hay que preservarlo.
            next_url_params = {}
            if request.method == 'GET' and request.args.get('restaurant_id_for_checkout'):
                next_url_params['restaurant_id_for_checkout'] = request.args.get('restaurant_id_for_checkout')
            
            session['next_url'] = url_for('checkout', **next_url_params)
            return redirect(url_for('show_login_page_auth'))

        cart = session.get('cart', {})
        if not cart: # Si el carrito está vacío, no hay nada que procesar
            flash('Tu carrito está vacío. Añade algunos ítems antes de proceder.', 'info')
            return redirect(url_for('list_restaurants'))

        # app/routes_order.py (dentro de la función checkout)

        if request.method == 'POST':
            restaurant_id_being_checked_out = request.form.get('restaurant_id_for_checkout', type=int)
            delivery_address = request.form.get('delivery_address')
            notes = request.form.get('notes', '')

            # --- NUEVA LÍNEA: OBTENER EL TIPO DE ENTREGA DEL FORMULARIO ---
            delivery_type_selected = request.form.get('delivery_type')

            if not restaurant_id_being_checked_out:
                flash('Error: Restaurante no especificado para el pedido. Intenta de nuevo desde el carrito.', 'danger')
                return redirect(url_for('view_cart'))

            if not delivery_address or len(delivery_address.strip()) < 5:
                flash('La dirección de entrega es obligatoria y debe ser válida.', 'danger')
                return redirect(url_for('checkout', restaurant_id_for_checkout=restaurant_id_being_checked_out))

            # --- VALIDACIÓN PARA delivery_type_selected ---
            valid_delivery_types = ['drone', 'motorcycle', 'bicycle'] # Los valores de tu ENUM
            if not delivery_type_selected or delivery_type_selected not in valid_delivery_types:
                flash('Por favor, selecciona un tipo de entrega válido.', 'danger')
                return redirect(url_for('checkout', restaurant_id_for_checkout=restaurant_id_being_checked_out))

            # ... (lógica para recalcular/validar items_for_this_order_db_format y current_order_total) ...
            # ... (esta parte de tu código se mantiene igual) ...
            items_for_this_order_db_format = []
            current_order_total = 0.0
            cart_after_this_order = {} 

            for item_id_str_from_session, item_data_in_cart in cart.items():
                if item_data_in_cart.get('restaurant_id') == restaurant_id_being_checked_out:
                    try:
                        price = float(item_data_in_cart.get('price', 0))
                        quantity = int(item_data_in_cart.get('quantity', 0))
                        if quantity <= 0: continue
                        items_for_this_order_db_format.append({
                            'menu_item_id': int(item_id_str_from_session),
                            'quantity': quantity,
                            'price_at_order': price 
                        })
                        current_order_total += price * quantity
                    except (ValueError, TypeError) as e:
                        # ... (manejo de error) ...
                        return redirect(url_for('view_cart'))
                else:
                    cart_after_this_order[item_id_str_from_session] = item_data_in_cart

            if not items_for_this_order_db_format:
                flash(f'No hay ítems válidos para el restaurante seleccionado en tu carrito.', 'warning')
                return redirect(url_for('view_cart'))

            payment_method = "cash_on_delivery" 
            order_status = "pending" 
            payment_status = "pending"

            order_id = create_new_order(
                user_id=session['user_id'],
                restaurant_id=restaurant_id_being_checked_out,
                delivery_address=delivery_address,
                total_amount=current_order_total,
                status=order_status,
                payment_method=payment_method,
                payment_status=payment_status,
                notes=notes,
                delivery_type=delivery_type_selected, # <--- USA LA VARIABLE DEL FORMULARIO
                order_items_list=items_for_this_order_db_format
            )

            if order_id:
                session['cart'] = cart_after_this_order 
                session.modified = True
                flash(f'¡Pedido #{order_id} realizado con éxito con entrega en {delivery_type_selected}!', 'success') # Mensaje actualizado
                return redirect(url_for('order_confirmation', order_id=order_id))
            else:
                flash('Hubo un error al procesar tu pedido. Por favor, inténtalo de nuevo.', 'danger')
                return redirect(url_for('checkout', restaurant_id_for_checkout=restaurant_id_being_checked_out))

        # --- LÓGICA GET (se mantiene igual) ---
        # ...
        
        # --- LÓGICA PARA MOSTRAR EL FORMULARIO DE CHECKOUT (MÉTODO GET) ---
        # Esta parte se ejecuta si request.method no es 'POST'
        restaurant_id_to_checkout = request.args.get('restaurant_id_for_checkout', type=int)

        if not restaurant_id_to_checkout:
            flash('No se especificó un restaurante para el checkout. Por favor, inténtalo desde el carrito.', 'danger')
            return redirect(url_for('view_cart'))

        restaurant_info = get_restaurant_by_id(restaurant_id_to_checkout)
        if not restaurant_info:
            flash('El restaurante para el que intentas hacer checkout no existe o no está disponible.', 'danger')
            return redirect(url_for('view_cart'))

        # Filtrar items del carrito para este restaurante específico para mostrar en el formulario
        items_for_checkout_display = []
        total_for_checkout_display = 0.0
        
        for item_id_str_from_session, item_data_in_cart in cart.items():
            if item_data_in_cart.get('restaurant_id') == restaurant_id_to_checkout:
                try:
                    price = float(item_data_in_cart.get('price', 0))
                    quantity = int(item_data_in_cart.get('quantity', 0))

                    if quantity <= 0: # No mostrar ítems con cantidad 0
                        continue
                        
                    item_subtotal = price * quantity
                    
                    items_for_checkout_display.append({
                        'id_str': item_id_str_from_session, # Aunque no se use directamente en el form, puede ser útil
                        'name': item_data_in_cart.get('name', 'Ítem Desconocido'),
                        'price': price,
                        'quantity': quantity,
                        'subtotal': item_subtotal
                    })
                    total_for_checkout_display += item_subtotal
                except (ValueError, TypeError) as e:
                    current_app.logger.error(f"Error procesando item del carrito para display (ID: {item_id_str_from_session}): {e}")
                    # Podrías decidir saltar este ítem o manejar el error de otra forma
        
        if not items_for_checkout_display: # Si no hay ítems válidos para mostrar para este restaurante
            flash(f'No tienes ítems de {restaurant_info.get("name", "este restaurante")} en tu carrito para procesar.', 'warning')
            return redirect(url_for('view_cart'))

        return render_template('order/checkout_form.html', 
                               items_to_checkout=items_for_checkout_display,
                               restaurant_being_checked_out=restaurant_info, # Para mostrar el nombre, etc.
                               total_checkout_amount=total_for_checkout_display)

    # --- Ruta de Confirmación de Pedido ---
    @app.route('/pedido/confirmacion/<int:order_id>')
    def order_confirmation(order_id):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para ver esta página.', 'warning')
            return redirect(url_for('show_login_page_auth'))
        
        # (Opcional) Podrías obtener detalles del pedido aquí para mostrarlos si quisieras
        # order_details, _ = get_order_details_by_id(order_id)
        # if not order_details or order_details.get('user_id') != session['user_id']:
        #     flash('Pedido no encontrado o no tienes permiso para verlo.', 'danger')
        #     return redirect(url_for('home_page')) # O a 'my_orders'

        return render_template('order/order_confirmation.html', order_id=order_id)

    # --- Ruta para "Mis Pedidos" (Historial) ---
    @app.route('/mis-pedidos')
    def my_orders():
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para ver tu historial de pedidos.', 'warning')
            session['next_url'] = url_for('my_orders')
            return redirect(url_for('show_login_page_auth'))
        
        try:
            user_orders = get_orders_by_user_id(session['user_id'])
            return render_template('order/my_orders.html', orders=user_orders)
        except Exception as e:
            current_app.logger.error(f"Error al obtener mis pedidos para usuario ID {session.get('user_id')}: {e}", exc_info=True)
            abort(500) # O mostrar una página de error amigable