# app/routes_admin.py
from flask import (
    Blueprint, render_template, session, redirect, url_for, flash, 
    current_app, request
)
from functools import wraps
from cryptography.fernet import Fernet
from .db import (find_user_by_email, create_new_user, get_all_users_for_admin, 
    get_user_by_id_for_admin, update_user_by_admin_in_db, 
    set_user_active_status_in_db, add_new_drone_to_db, get_all_drones_for_admin, 
    get_drone_by_id_for_admin, update_drone_by_admin_in_db,get_drones_for_select,
    add_drone_maintenance_log, get_all_maintenance_logs,set_drone_status_in_db, get_all_system_orders_for_admin,
    get_order_details_for_admin, get_active_drones_for_select, get_active_delivery_personnel_by_roles, assign_entity_to_order_in_db )
import datetime 

# (Aquí irán importaciones de db.py cuando las necesitemos)

admin_bp = Blueprint(
    'admin', 
    __name__, 
    url_prefix='/admin',  # Todas las rutas de admin empezarán con /admin
    template_folder='admin'   # Plantillas en app/templates/admin/
)

# Decorador para proteger rutas de administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('show_login_page_auth')) # A tu endpoint de login

        if session.get('user_role') != 'admin':
            flash('No tienes permiso para acceder a las funciones de administrador.', 'danger')
            return redirect(url_for('home_page')) # A la página de inicio general

        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Por ahora, un dashboard simple. Más adelante podemos añadir estadísticas.
    # Usaremos la plantilla que creamos como maqueta estática.
    return render_template('admin/dashboard.html') 
                            # Buscará en app/templates/admin/dashboard_admin.html

@admin_bp.route('/usuarios/registrar', methods=['GET', 'POST'])
@admin_required
def register_new_user_by_admin():
    # Inicializar cipher_suite aquí también, o pasarlo de alguna forma segura
    # Es crucial que sea la misma clave que en routes_auth.py
    cipher_suite = None
    try:
        if current_app.config.get('FERNET_KEY'):
            key_bytes = current_app.config['FERNET_KEY']
            if isinstance(key_bytes, str): # Asegurar que sea bytes
                key_bytes = key_bytes.encode('utf-8')
            cipher_suite = Fernet(key_bytes)
        else:
            current_app.logger.critical("ADMIN_REGISTER: FERNET_KEY no configurada.")
    except Exception as e:
        current_app.logger.critical(f"ADMIN_REGISTER: Error inicializando Fernet: {e}")

    if request.method == 'POST':
        if not cipher_suite:
            flash("Error crítico de configuración (crypto). No se puede registrar usuario.", "danger")
            return redirect(url_for('admin.dashboard')) # O a la misma página de registro

        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password_plain = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        phone_number = request.form.get('phone_number', '').strip()
        # address = request.form.get('address', '').strip() # Si añades dirección

        # Validaciones
        if not email or not password_plain or not role or not full_name:
            flash('Nombre completo, email, contraseña y rol son obligatorios.', 'danger')
            return render_template('register_new_user_form.html', form_data=request.form) # Re-renderizar con datos

        if password_plain != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register_new_user_form.html', form_data=request.form)

        # (Añade más validaciones si es necesario: longitud de contraseña, formato de email)

        existing_user = find_user_by_email(email)
        if existing_user:
            flash('Este correo electrónico ya está registrado.', 'danger')
            return render_template('register_new_user_form.html', form_data=request.form)

        try:
            encrypted_password_str = cipher_suite.encrypt(password_plain.encode('utf-8')).decode('utf-8')
        except Exception as e:
            current_app.logger.error(f"ADMIN_REGISTER: Error encriptando contraseña para {email}: {e}", exc_info=True)
            flash('Error al procesar la contraseña.', 'danger')
            return render_template('register_new_user_form.html', form_data=request.form)

        # Llamar a create_new_user (asegúrate que esta función ahora acepte full_name y phone_number)
        # Necesitaremos modificar create_new_user en db.py
        new_user_result = create_new_user(
            email=email, 
            hashed_password_str=encrypted_password_str, 
            user_role=role,
            full_name=full_name, # Nuevo
            phone_number=phone_number if phone_number else None # Nuevo
        )

        if new_user_result and not new_user_result.get('error'):
            flash(f"Usuario {new_user_result.get('email', email)} creado con rol '{role}' exitosamente.", 'success')
            return redirect(url_for('admin.register_new_user_by_admin')) # Redirigir al mismo form (o a una lista de usuarios)
        else:
            error_msg = new_user_result.get('error', 'No se pudo crear el usuario.') if new_user_result else 'Error desconocido.'
            flash(f"Error al crear usuario: {error_msg}", 'danger')
            return render_template('register_new_user_form.html', form_data=request.form)

    # Método GET: simplemente muestra el formulario
    return render_template('admin/register_new_user_form.html', form_data={}) # Pasar form_data vacío para GET


# app/routes_admin.py
# ... (definición de admin_bp, decorador admin_required, ruta dashboard) ...

@admin_bp.route('/drones/agregar', methods=['GET', 'POST'])
@admin_required
def add_new_drone_by_admin():
    if request.method == 'POST':
        # --- LÓGICA PARA PROCESAR EL FORMULARIO (MÉTODO POST) ---
        identifier = request.form.get('drone_identifier', '').strip()
        model = request.form.get('drone_model', '').strip()
        purchase_date_str = request.form.get('purchase_date') # Viene como string
        status = request.form.get('status')
        max_load_str = request.form.get('max_load_capacity_kg', '').strip()
        max_flight_time_str = request.form.get('max_flight_time_min', '').strip()

        # Validaciones básicas
        if not identifier or not model or not status:
            flash('El identificador, modelo y estado del dron son obligatorios.', 'danger')
            return render_template('admin/agregar_dron.html', form_data=request.form) # Re-renderizar con datos

        # Conversión y validación de tipos de datos
        purchase_date_obj = None
        if purchase_date_str:
            try:
                # datetime.datetime.strptime(purchase_date_str, '%Y-%m-%d').date() # Si datetime está importado
                # Por ahora, si la BD acepta el string 'YYYY-MM-DD' para DATE, podría ser suficiente
                # o podrías pasar None si la conversión falla o está vacío.
                # Para psycopg2, pasar None si está vacío es mejor.
                purchase_date_obj = purchase_date_str # La BD lo tomará como DATE
            except ValueError:
                flash('Formato de fecha de adquisición inválido. Use AAAA-MM-DD.', 'danger')
                return render_template('admin/agregar_dron.html', form_data=request.form)

        max_load_obj = None
        if max_load_str:
            try:
                max_load_obj = float(max_load_str)
                if max_load_obj < 0:
                    flash('La capacidad de carga no puede ser negativa.', 'danger')
                    return render_template('admin/agregar_dron.html', form_data=request.form)
            except ValueError:
                flash('La capacidad de carga debe ser un número válido.', 'danger')
                return render_template('admin/agregar_dron.html', form_data=request.form)

        max_flight_time_obj = None
        if max_flight_time_str:
            try:
                max_flight_time_obj = int(max_flight_time_str)
                if max_flight_time_obj < 0:
                    flash('El tiempo de vuelo no puede ser negativo.', 'danger')
                    return render_template('admin/agregar_dron.html', form_data=request.form)
            except ValueError:
                flash('El tiempo de vuelo debe ser un número entero válido.', 'danger')
                return render_template('admin/agregar_dron.html', form_data=request.form)

        # Llamar a la función de db.py para añadir el dron
        new_drone_id = add_new_drone_to_db(
            identifier=identifier,
            model=model,
            purchase_date=purchase_date_obj if purchase_date_obj else None,
            status=status,
            max_load=max_load_obj,
            max_flight_time=max_flight_time_obj
        )

        if new_drone_id:
            flash(f'Dron "{identifier}" - {model} añadido con éxito (ID: {new_drone_id}).', 'success')
            return redirect(url_for('admin.add_new_drone_by_admin')) # Redirigir para añadir otro o a una lista de drones
        else:
            # Comprobar si el error es por identificador duplicado (si add_new_drone_to_db lo maneja y devuelve un error específico)
            # Por ahora, un mensaje genérico.
            flash('Error al añadir el dron a la base de datos. Verifica que el Identificador no esté ya en uso.', 'danger')
            return render_template('admin/agregar_dron.html.html', form_data=request.form) # Quedarse en el form con los datos

    # Método GET: simplemente muestra el formulario
    return render_template('admin/agregar_dron.html', form_data={}) # form_data vacío para un nuevo dron



@admin_bp.route('/usuarios')
@admin_required
def manage_users_list():
    try:
        users = get_all_users_for_admin()
    except Exception as e:
        current_app.logger.error(f"Error al obtener la lista de usuarios para el admin: {e}", exc_info=True)
        flash("Ocurrió un error al cargar la lista de usuarios.", "danger")
        users = []

    return render_template('admin/manage_users_list.html', users=users)
                            


@admin_bp.route('/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user_by_admin(user_id):
    user_to_edit = get_user_by_id_for_admin(user_id)
    if not user_to_edit:
        flash(f"Usuario con ID {user_id} no encontrado.", "danger")
        return redirect(url_for('admin.manage_users_list'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role')
        phone_number = request.form.get('phone_number', '').strip()

        # Validaciones
        if not full_name or not email or not role:
            flash('Nombre completo, email y rol son obligatorios.', 'danger')
            # Pasar los datos actuales (del POST o del user_to_edit si es el primer error)
            # Es mejor pasar request.form para que los cambios no guardados se mantengan
            return render_template('admin/edit_user_form.html', user=request.form, user_id=user_id, current_role=user_to_edit.get('role'))

        # (Opcional: validar si el email nuevo ya existe para OTRO usuario)
        # ...

        success = update_user_by_admin_in_db(user_id, full_name, email, role, phone_number)

        if success:
            flash(f'Usuario "{email}" actualizado con éxito.', 'success')
            return redirect(url_for('admin.manage_users_list'))
        else:
            flash('Error al actualizar el usuario. Inténtalo de nuevo.', 'danger')
            # Devolver al formulario con los datos que se intentaron guardar
            return render_template('admin/edit_user_form.html', user=request.form, user_id=user_id, current_role=role)

    # Método GET: mostrar el formulario con los datos actuales del usuario
    # user_to_edit ya es un diccionario (RealDictRow)
    return render_template('admin/edit_user_form.html', user=user_to_edit, user_id=user_id, current_role=user_to_edit.get('role'))



@admin_bp.route('/usuarios/<int:user_id>/desactivar', methods=['POST'])
@admin_required
def deactivate_user_by_admin(user_id):
    # Por seguridad, no permitir que un admin se desactive a sí mismo.
    if user_id == session.get('user_id'):
        flash('No puedes desactivar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('admin.manage_users_list'))

    success = set_user_active_status_in_db(user_id, False) # False para desactivar
    if success:
        flash(f'Usuario ID {user_id} desactivado con éxito.', 'success')
    else:
        flash(f'Error al desactivar el usuario ID {user_id}.', 'danger')
    return redirect(url_for('admin.manage_users_list'))

@admin_bp.route('/usuarios/<int:user_id>/activar', methods=['POST'])
@admin_required
def activate_user_by_admin(user_id):
    success = set_user_active_status_in_db(user_id, True) # True para activar
    if success:
        flash(f'Usuario ID {user_id} activado con éxito.', 'success')
    else:
        flash(f'Error al activar el usuario ID {user_id}.', 'danger')
    return redirect(url_for('admin.manage_users_list'))
                            


@admin_bp.route('/drones') 
@admin_required
def manage_drones_list():
    try:
        drones = get_all_drones_for_admin()
    except Exception as e:
        current_app.logger.error(f"Error al obtener la lista de drones para el admin: {e}", exc_info=True)
        flash("Ocurrió un error al cargar la lista de drones.", "danger")
        drones = []

    return render_template('admin/manage_drones_list.html', drones=drones)

# app/routes_admin.py
# ... (tus rutas existentes) ...

@admin_bp.route('/drones/editar/<int:drone_id>', methods=['GET', 'POST'])
@admin_required
def edit_drone_by_admin(drone_id):
    drone_to_edit = get_drone_by_id_for_admin(drone_id)
    if not drone_to_edit:
        flash(f"Dron con ID {drone_id} no encontrado.", "danger")
        return redirect(url_for('admin.manage_drones_list'))

    # Posibles estados para el dropdown del dron
    # Asegúrate que coincidan con tu ENUM 'drone_status_enum'
    possible_drone_statuses = ['activo', 'mantenimiento', 'inactivo', 'de_baja']


    if request.method == 'POST':
        identifier = request.form.get('drone_identifier', '').strip()
        model = request.form.get('drone_model', '').strip()
        purchase_date_str = request.form.get('purchase_date')
        status = request.form.get('status')
        max_load_str = request.form.get('max_load_capacity_kg', '').strip()
        max_flight_time_str = request.form.get('max_flight_time_min', '').strip()

        if not identifier or not model or not status:
            flash('El identificador, modelo y estado del dron son obligatorios.', 'danger')
            return render_template('admin/agregar_dron.html', 
                                   form_action_title=f"Editar Dron: {drone_to_edit['drone_identifier']}",
                                   drone=request.form, # Usar request.form para repoblar
                                   drone_id=drone_id,
                                   possible_statuses=possible_drone_statuses,
                                   is_edit_mode=True)

        # Conversión y validación (similar a add_new_drone_by_admin)
        purchase_date_obj = purchase_date_str if purchase_date_str else None

        max_load_obj = None
        if max_load_str:
            try: max_load_obj = float(max_load_str)
            except ValueError: flash('Capacidad de carga inválida.', 'danger'); return render_template('add_drone_form.html', form_action_title=f"Editar Dron: {drone_to_edit['drone_identifier']}", drone=request.form, drone_id=drone_id, possible_statuses=possible_drone_statuses, is_edit_mode=True)
            if max_load_obj < 0: flash('Capacidad de carga no puede ser negativa.', 'danger'); return render_template('add_drone_form.html', form_action_title=f"Editar Dron: {drone_to_edit['drone_identifier']}", drone=request.form, drone_id=drone_id, possible_statuses=possible_drone_statuses, is_edit_mode=True)

        max_flight_time_obj = None
        if max_flight_time_str:
            try: max_flight_time_obj = int(max_flight_time_str)
            except ValueError: flash('Tiempo de vuelo inválido.', 'danger'); return render_template('add_drone_form.html', form_action_title=f"Editar Dron: {drone_to_edit['drone_identifier']}", drone=request.form, drone_id=drone_id, possible_statuses=possible_drone_statuses, is_edit_mode=True)
            if max_flight_time_obj < 0: flash('Tiempo de vuelo no puede ser negativo.', 'danger'); return render_template('add_drone_form.html', form_action_title=f"Editar Dron: {drone_to_edit['drone_identifier']}", drone=request.form, drone_id=drone_id, possible_statuses=possible_drone_statuses, is_edit_mode=True)


        success = update_drone_by_admin_in_db(
            drone_id, identifier, model, purchase_date_obj, status, 
            max_load_obj, max_flight_time_obj
        )

        if success:
            flash(f'Dron "{identifier}" actualizado con éxito.', 'success')
            return redirect(url_for('admin.manage_drones_list'))
        else:
            flash('Error al actualizar el dron. Verifica que el Identificador no esté duplicado para otro dron.', 'danger')
            return render_template('admin/agregar_dron.html', 
                                   form_action_title=f"Editar Dron: {drone_to_edit['drone_identifier']}",
                                   drone=request.form, # Repoblar con los datos que fallaron
                                   drone_id=drone_id,
                                   possible_statuses=possible_drone_statuses,
                                   is_edit_mode=True)

    # Método GET: mostrar el formulario con los datos actuales del dron
    return render_template('admin/agregar_dron.html', 
                           form_action_title=f"Editar Dron: {drone_to_edit.get('drone_identifier', 'Desconocido')}",
                           drone=drone_to_edit, # Pasar los datos actuales del dron
                           drone_id=drone_id, # Para el action del formulario
                           possible_statuses=possible_drone_statuses,
                           is_edit_mode=True) # Indicador para la plantilla


@admin_bp.route('/drones/mantenimiento', methods=['GET', 'POST'])
@admin_required
def manage_drone_maintenance():
    if request.method == 'POST':
        drone_id = request.form.get('drone_id', type=int)
        service_date_str = request.form.get('service_date')
        service_type = request.form.get('service_type')
        description = request.form.get('description', '').strip()
        parts_replaced = request.form.get('parts_replaced', '').strip()
        cost_str = request.form.get('cost', '').strip()
        technician_name = request.form.get('technician_name', '').strip()

        # Validaciones básicas
        if not drone_id or not service_date_str or not service_type or not description:
            flash('Dron, fecha de servicio, tipo de servicio y descripción son obligatorios.', 'danger')
        else:
            # Validar y convertir fecha
            try:
                # La base de datos espera 'YYYY-MM-DD' para el tipo DATE
                # El input type="date" del HTML debería enviar en este formato.
                # No se necesita conversión explícita a objeto date si la BD lo maneja.
                pass 
            except ValueError:
                flash('Formato de fecha de servicio inválido.', 'danger')
                # Para re-renderizar el GET, necesitamos los drones y los logs de nuevo
                drones_for_select = get_drones_for_select()
                maintenance_logs = get_all_maintenance_logs()
                return render_template('admin/drone_mantenimiento.html', 
                                       drones=drones_for_select, 
                                       logs=maintenance_logs, 
                                       form_data=request.form)

            cost_obj = None
            if cost_str:
                try:
                    cost_obj = float(cost_str)
                    if cost_obj < 0:
                         flash('El costo no puede ser negativo.', 'danger')
                         cost_obj = None # O manejar el error y no continuar
                except ValueError:
                    flash('El costo debe ser un número válido.', 'danger')
                    cost_obj = None # O manejar el error

            if drone_id and service_date_str and service_type and description : # Si validaciones básicas pasan
                new_log_id = add_drone_maintenance_log(
                    drone_id=drone_id,
                    service_date_str=service_date_str,
                    service_type=service_type,
                    description=description,
                    parts_replaced=parts_replaced if parts_replaced else None,
                    cost=cost_obj,
                    technician_name=technician_name if technician_name else None
                )

                if new_log_id:
                    flash(f'Registro de mantenimiento para dron ID {drone_id} añadido con éxito.', 'success')
                else:
                    flash('Error al añadir el registro de mantenimiento.', 'danger')
            # Siempre redirigir después de un POST exitoso o fallido (si no se re-renderiza por error de validación)
            # para evitar reenvío del formulario si el usuario recarga.
        return redirect(url_for('admin.manage_drone_maintenance'))

    # Método GET: Mostrar el formulario y la lista de logs de mantenimiento
    try:
        drones_for_select = get_drones_for_select()
        maintenance_logs = get_all_maintenance_logs()
    except Exception as e:
        current_app.logger.error(f"Error obteniendo datos para la página de mantenimiento de drones: {e}", exc_info=True)
        flash("Ocurrió un error al cargar la página de mantenimiento.", "danger")
        drones_for_select = []
        maintenance_logs = []

    return render_template('admin/drone_mantenimiento.html', 
                           drones=drones_for_select, 
                           logs=maintenance_logs,
                           form_data={}) # Para el primer GET, form_data está vacío


@admin_bp.route('/drones/<int:drone_id>/cambiar-estado', methods=['POST'])
@admin_required
def change_drone_status_route(drone_id): # Renombré la función para claridad
    new_status = request.form.get('new_drone_status')

    # Obtener los valores válidos de tu ENUM drone_status_enum para validación
    # Podrías tenerlos en config o definirlos aquí.
    # Asumimos que ya creaste: 
    # CREATE TYPE drone_status_enum AS ENUM ('activo', 'mantenimiento', 'inactivo', 'de_baja');
    valid_drone_statuses = ['activo', 'mantenimiento', 'inactivo', 'de_baja'] 

    if not new_status or new_status not in valid_drone_statuses:
        flash(f"Estado '{new_status}' inválido seleccionado para el dron.", 'danger')
        return redirect(url_for('admin.manage_drones_list'))

    # (Opcional: verificar que el drone_id exista antes de intentar actualizar)
    # drone_check = get_drone_by_id_for_admin(drone_id)
    # if not drone_check:
    #     flash(f"Dron ID {drone_id} no encontrado.", "danger")
    #     return redirect(url_for('admin.manage_drones_list'))

    success = set_drone_status_in_db(drone_id, new_status)

    if success:
        flash(f'Estado del dron ID {drone_id} actualizado a "{new_status.replace("_", " ").capitalize()}".', 'success')
    else:
        flash(f'Error al actualizar el estado del dron ID {drone_id}.', 'danger')

    return redirect(url_for('admin.manage_drones_list'))
                           
# Ver todos los pedidos del sistema
@admin_bp.route('/pedidos/todos') # URL: /admin/pedidos/todos
@admin_required
def view_all_system_orders():
    # Aquí podríamos obtener filtros de request.args si los implementamos
    # status = request.args.get('status')
    # date = request.args.get('date')
    try:
        all_orders = get_all_system_orders_for_admin() # Por ahora sin filtros
    except Exception as e:
        current_app.logger.error(f"Error al obtener la lista de todos los pedidos: {e}", exc_info=True)
        flash("Ocurrió un error al cargar la lista de todos los pedidos.", "danger")
        all_orders = []

    return render_template('admin/all_order_list.html', orders=all_orders)
                            # Buscará en app/templates/admin/all_orders_list.html

#ver datalles de los pedidos


@admin_bp.route('/pedidos/detalles/<int:order_id>') # Asumo que esta es tu ruta actual
@admin_required
def view_order_details_by_admin(order_id):
    order = get_order_details_for_admin(order_id) # Esta función ya obtiene muchos detalles

    if not order:
        flash(f"Pedido con ID {order_id} no encontrado o error al cargar detalles.", "danger")
        return redirect(url_for('admin.view_all_system_orders'))

    assignable_entities = [] # Lista para drones o repartidores
    entity_type_for_assignment = None # Para saber qué tipo de ID se enviará en el form ('drone_id' o 'delivery_person_id')

    if order.get('delivery_type') == 'drone':
        assignable_entities = get_active_drones_for_select()
        entity_type_for_assignment = 'drone'
        current_app.logger.info(f"Cargando {len(assignable_entities)} drones activos para asignación al pedido {order_id}")
    elif order.get('delivery_type') == 'motorcycle':
        assignable_entities = get_active_delivery_personnel_by_roles(['repartidor_moto'])
        entity_type_for_assignment = 'person'
        current_app.logger.info(f"Cargando {len(assignable_entities)} repartidores en moto para asignación al pedido {order_id}")
    elif order.get('delivery_type') == 'bicycle':
        assignable_entities = get_active_delivery_personnel_by_roles(['repartidor_bici'])
        entity_type_for_assignment = 'person'
        current_app.logger.info(f"Cargando {len(assignable_entities)} repartidores en bici para asignación al pedido {order_id}")
    return render_template(
        'admin/order_details.html', 
        order=order, 
        assignable_entities=assignable_entities,
        entity_type_for_assignment=entity_type_for_assignment
        # possible_order_statuses=possible_order_statuses # Si decides pasarlos
    )
 #asignar entrega


@admin_bp.route('/pedidos/<int:order_id>/asignar-entrega', methods=['POST'])
@admin_required
def assign_delivery_handler(order_id): 

    entity_id_to_assign = request.form.get('delivery_entity_id', type=int)
    

    entity_type = request.form.get('entity_type_for_assignment') # El form debería enviar esto

    if not entity_id_to_assign or not entity_type:
        flash('No se seleccionó un repartidor/dron o el tipo de entidad es incorrecto.', 'danger')
        return redirect(url_for('admin.view_order_details_by_admin', order_id=order_id))

    
    new_order_status = 'confirmed' 
   

    success = False
    if entity_type == 'drone':
        current_app.logger.info(f"Admin asignando Dron ID {entity_id_to_assign} al pedido ID {order_id}")
        success = assign_entity_to_order_in_db(order_id, 'drone', entity_id_to_assign, new_order_status)
    elif entity_type == 'person':
        current_app.logger.info(f"Admin asignando Repartidor ID {entity_id_to_assign} al pedido ID {order_id}")
        success = assign_entity_to_order_in_db(order_id, 'person', entity_id_to_assign, new_order_status)
    else:
        flash('Tipo de entidad de entrega desconocido.', 'danger')

    if success:
        flash(f'Entrega asignada exitosamente al pedido #{order_id}. Estado actualizado a "{new_order_status}".', 'success')
    elif entity_type in ['drone', 'person']: # Si el tipo era válido pero falló la BD
        flash(f'Error al asignar la entrega para el pedido #{order_id}.', 'danger')

    return redirect(url_for('admin.view_order_details_by_admin', order_id=order_id))