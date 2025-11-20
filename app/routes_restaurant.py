# app/routes_restaurant.py
from flask import (
    Blueprint, render_template, session, redirect, url_for, flash, 
    current_app, abort, request
)
from functools import wraps # Para crear decoradores
from werkzeug.utils import secure_filename # Para asegurar nombres de archivo
# Importar la función de la base de datos que necesitamos
from .db import (get_restaurants_by_owner_id, get_restaurant_by_id
, get_menu_items_by_restaurant_id, add_new_menu_item_to_db,get_menu_item_by_id, update_menu_item_in_db, delete_menu_item_from_db,
get_orders_for_restaurant_from_db, update_order_status_in_db,get_order_details_by_id,update_restaurant_details_in_db)
import psycopg2, os, uuid

# Crear un Blueprint:
# - 'restaurant': nombre del Blueprint, se usará en url_for (ej. 'restaurant.dashboard')
# - __name__: ayuda a Flask a localizar el blueprint
# - url_prefix='/restaurante': todas las rutas definidas en este blueprint comenzarán con /restaurante
# - template_folder='restaurant': las plantillas para este blueprint se buscarán en app/templates/restaurant/

#Verificar que la extensión del archivo subido sea una de las permitidas.
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


restaurant_bp = Blueprint(
    'restaurant', 
    __name__, 
    url_prefix='/restaurante', 
    template_folder='restaurant' # Esto significa que Flask buscará en app/templates/restaurant/
)

# --- Decorador para Proteger Rutas de Dueño de Restaurante ---
def restaurant_owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            # Usamos los nombres de las funciones de vista para url_for
            return redirect(url_for('show_login_page_auth')) 
        
        # Asumimos que 'restaurant_owner' es el string exacto guardado en session['user_role']
        if session.get('user_role') != 'restaurant_owner':
            flash('No tienes permiso para acceder a la gestión de restaurantes.', 'danger')
            return redirect(url_for('home_page')) # Endpoint de la página de inicio
        
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas del Blueprint de Restaurante ---
@restaurant_bp.route('/dashboard.html') # La URL completa será /restaurante/dashboard
@restaurant_owner_required # Aplicamos el decorador para proteger esta ruta
def dashboard():
    owner_id = session.get('user_id')
    if not owner_id: # Doble chequeo, aunque el decorador ya lo hace
        flash('Error de sesión. Por favor, inicia sesión de nuevo.', 'danger')
        return redirect(url_for('show_login_page_auth'))

    try:
        # Obtener los restaurantes que pertenecen a este dueño
        restaurants_owned = get_restaurants_by_owner_id(owner_id)
        current_app.logger.info(f"Dueño ID {owner_id} tiene {len(restaurants_owned) if restaurants_owned else 0} restaurantes.")
    except Exception as e:
        current_app.logger.error(f"Error obteniendo restaurantes para dueño ID {owner_id}: {e}")
        flash('Ocurrió un error al cargar la información de tus restaurantes.', 'danger')
        restaurants_owned = [] # Lista vacía para evitar errores en la plantilla

    return render_template('restaurant/dashboard.html', restaurants=restaurants_owned)
                            # Buscará dashboard.html en app/templates/restaurant/dashboard.html

@restaurant_bp.route('/<int:restaurant_id>/menu') # Ej: /restaurante/1/menu
@restaurant_owner_required
def manage_menu(restaurant_id):
    owner_id = session.get('user_id')

    # Verificar que el restaurante pertenece al dueño actual
    restaurant = get_restaurant_by_id(restaurant_id) # Ya tenemos esta función en db.py

    if not restaurant:
        current_app.logger.warning(f"Dueño {owner_id} intentó gestionar menú de restaurante no existente: {restaurant_id}")
        abort(404)

    # Asumiendo que la tabla 'restaurants' tiene la columna 'user_id' para el dueño
    if restaurant['user_id'] != owner_id:
        flash('No tienes permiso para gestionar el menú de este restaurante.', 'danger')
        current_app.logger.warning(f"Dueño {owner_id} intentó acceso no autorizado a menú de restaurante: {restaurant_id}")
        return redirect(url_for('restaurant.dashboard')) # Redirigir a su propio dashboard

    menu_items = get_menu_items_by_restaurant_id(restaurant_id) # Ya tenemos esta función

    return render_template('restaurant/manage_menu.html', 
                           restaurant=restaurant, 
                           menu_items=menu_items)
                           # Buscará en app/templates/restaurant/manage_menu.html

@restaurant_bp.route('/<int:restaurant_id>/menu/nuevo', methods=['GET', 'POST'])
@restaurant_owner_required
def add_new_menu_item_for_restaurant(restaurant_id):
    owner_id = session.get('user_id')
    restaurant = get_restaurant_by_id(restaurant_id)

    if not restaurant:
        abort(404)
    if restaurant['user_id'] != owner_id: # Verificar propiedad
        flash('No tienes permiso para añadir ítems a este restaurante.', 'danger')
        return redirect(url_for('restaurant.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        price_str = request.form.get('price')
        is_available = request.form.get('is_available') == 'on' # Checkbox devuelve 'on' o nada

        image_file = request.files.get('menu_item_image') # Obtener el archivo del formulario
        image_filename_to_save = None # Variable para guardar el nombre del archivo en la BD

        # Validaciones básicas
        if not name or not price_str:
            flash('El nombre y el precio del ítem son obligatorios.', 'danger')
            # Volver a renderizar el formulario, idealmente con los datos ya ingresados (más avanzado)
            return render_template('menu_item_form.html', 
                                   form_action_title="Añadir Nuevo Ítem", 
                                   restaurant=restaurant,
                                   item_data={'name': name, 'description': description, 'price': price_str, 'is_available': is_available}) # Pasar datos actuales

        try:
            price = float(price_str)
            if price < 0:
                raise ValueError("El precio no puede ser negativo.")
        except ValueError:
            flash('El precio debe ser un número válido.', 'danger')
            return render_template('menu_item_form.html', 
                                   form_action_title="Añadir Nuevo Ítem", 
                                   restaurant=restaurant,
                                   item_data={'name': name, 'description': description, 'price': price_str, 'is_available': is_available})
        

        # --- INICIO: Lógica para manejar el archivo de imagen ---
        if image_file and image_file.filename != '':
            if allowed_file(image_file.filename):
                # 1. Asegurar el nombre del archivo original
                original_filename = secure_filename(image_file.filename)
                # 2. Crear un nombre de archivo único para evitar colisiones
                #    Ej: <uuid>_<nombre_original_seguro>
                #    Obtener la extensión del archivo
                extension = original_filename.rsplit('.', 1)[1].lower()
                unique_filename_base = str(uuid.uuid4())
                unique_filename = f"{unique_filename_base}.{extension}"
                
                # 3. Construir la ruta completa donde se guardará el archivo
                #    current_app.root_path es la carpeta 'app/'
                #    current_app.config['UPLOAD_FOLDER'] es 'static/uploads/menu_item_images'
                #    Necesitamos construir la ruta absoluta para .save()
                #    Y la ruta relativa para la BD.

                # Ruta relativa desde 'app/' para guardar en la BD (ej. 'static/uploads/menu_item_images/nombre.jpg')
                # UPLOAD_FOLDER ya está configurado como 'static/uploads/menu_item_images'
                # por lo que solo necesitamos añadir el nombre del archivo.
                # No, UPLOAD_FOLDER en config es 'static/uploads/menu_item_images'
                # current_app.config['UPLOAD_FOLDER'] es 'static/uploads/menu_item_images'
                # El path que se guarda en BD debe ser relativo a la carpeta 'static'
                # ej: 'uploads/menu_item_images/nombre_archivo.jpg'

                # Path para guardar el archivo en el servidor: app/static/uploads/menu_item_images/nombre_archivo.jpg
                # current_app.root_path es /path/to/Skyking_Web/app
                # config['UPLOAD_FOLDER'] es 'static/uploads/menu_item_images' (relativo a root_path si no se usa os.path.isabs)
                # Si UPLOAD_FOLDER en config NO es absoluto, se considera relativo a app.root_path
                # Mi config fue: os.path.join('static', 'uploads', 'menu_item_images')
                # Esta es una ruta relativa a la raíz de la aplicación, no a app.root_path
                # Flask por defecto sirve 'static' desde app.static_folder que es 'static' si no se especifica.
                # Si UPLOAD_FOLDER está en app/config.py como:
                # UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'menu_item_images') # Esto lo haría absoluto
                # O más simple, si está dentro de la carpeta 'app':
                # UPLOAD_FOLDER = os.path.join(current_app.root_path, 'static', 'uploads', 'menu_item_images') # Para la función save()
                # Y para la BD: 'uploads/menu_item_images/' + unique_filename

                upload_folder_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                if not os.path.exists(upload_folder_path):
                    os.makedirs(upload_folder_path) # Crear la carpeta si no existe

                file_save_path = os.path.join(upload_folder_path, unique_filename)
                
                try:
                    image_file.save(file_save_path)
                    path_parts = current_app.config['UPLOAD_FOLDER'].split(os.path.sep)
    
                    # Si el primer componente es 'static', lo omitimos para la ruta relativa en la BD
                    if path_parts and path_parts[0].lower() == 'static': # Usar lower() por si acaso
                        relative_upload_dir_for_db = os.path.join(*path_parts[1:])
                    else:
                        # Si UPLOAD_FOLDER no empieza con 'static', algo es inesperado, pero usa el path completo
                        # (esto no debería pasar con tu config actual)
                        relative_upload_dir_for_db = current_app.config['UPLOAD_FOLDER']
    
                    # Guardar la ruta relativa a la carpeta 'static' en la BD
                    image_filename_to_save = os.path.join(relative_upload_dir_for_db, unique_filename)
                    # Asegurar que use slashes para URLs
                    image_filename_to_save = image_filename_to_save.replace("\\", "/")
                    current_app.logger.info(f"Imagen guardada en: {file_save_path}")
                    current_app.logger.info(f"Ruta para BD: {image_filename_to_save}")
                except Exception as e:
                    current_app.logger.error(f"Error al guardar la imagen: {e}")
                    flash('Hubo un error al guardar la imagen del ítem.', 'danger')
                    # No necesariamente hay que retornar aquí, podría continuar sin imagen
                    image_filename_to_save = None # No se pudo guardar
            else:
                flash('Tipo de archivo de imagen no permitido. Permitidos: png, jpg, jpeg, gif.', 'danger')
                # Quedarse en el formulario, idealmente con los datos para no perderlos
                return render_template('menu_item_form.html', 
                                form_action_title="Añadir Nuevo Ítem", 
                                restaurant=restaurant,
                                item_data=request.form) # Repoblar con datos del form
        # --- FIN: Lógica para manejar el archivo de imagen ---

        # Llamar a la función de db.py para añadir el ítem
        new_item_id = add_new_menu_item_to_db(
            restaurant_id=restaurant_id,
            name=name,
            description=description,
            price=price,
            image_url=image_filename_to_save,
            is_available=is_available
        )

        if new_item_id:
            flash(f'Ítem "{name}" añadido al menú con éxito.', 'success')
            return redirect(url_for('restaurant.manage_menu', restaurant_id=restaurant_id))
        else:
            flash('Error al añadir el ítem al menú. Inténtalo de nuevo.', 'danger')
            # Quedarse en el formulario, idealmente con los datos para no perderlos
            return render_template('menu_item_form.html', 
                                   form_action_title="Añadir Nuevo Ítem", 
                                   restaurant=restaurant,
                                   item_data={'name': name, 'description': description, 'price': price_str, 'is_available': is_available})
    
    # Método GET: Mostrar el formulario vacío
    return render_template('restaurant/menu_item_form.html', 
                           form_action_title="Añadir Nuevo Ítem al Menú de " + restaurant.get('name', ''), 
                           restaurant=restaurant,
                           item_data={}) # item_data vacío para un nuevo ítem

@restaurant_bp.route('/<int:restaurant_id>/menu/editar/<int:item_id>', methods=['GET', 'POST'])
@restaurant_owner_required
def edit_menu_item_for_restaurant(restaurant_id, item_id):
    owner_id = session.get('user_id')
    restaurant = get_restaurant_by_id(restaurant_id)

    if not restaurant:
        abort(404)
    if restaurant.get('user_id') != owner_id: # Usar .get() por seguridad
        flash('No tienes permiso para gestionar ítems de este restaurante.', 'danger')
        return redirect(url_for('restaurant.dashboard'))

    # Obtener el ítem de menú actual para asegurarse de que pertenece a este restaurante y para el formulario
    item_to_edit = get_menu_item_by_id(item_id)

    if not item_to_edit or item_to_edit.get('restaurant_id') != restaurant_id:
        flash('Ítem de menú no encontrado o no pertenece a este restaurante.', 'danger')
        return redirect(url_for('restaurant.manage_menu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        price_str = request.form.get('price')
        is_available = request.form.get('is_available') == 'on'
        # image_url = request.form.get('image_url', item_to_edit.get('image_url')) # Conservar la URL si no se envía una nueva
        image_file = request.files.get('menu_item_image')
        current_image_url = item_to_edit.get('image_url') # Obtener la URL actual
        image_filename_to_save_for_db = current_image_url

        if image_file and image_file.filename != '':
            if allowed_file(image_file.filename):
                original_filename = secure_filename(image_file.filename)
                extension = original_filename.rsplit('.', 1)[1].lower()
                unique_filename_base = str(uuid.uuid4())
                unique_filename = f"{unique_filename_base}.{extension}"
                
                upload_folder_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                if not os.path.exists(upload_folder_path):
                    os.makedirs(upload_folder_path)
                
                file_save_path = os.path.join(upload_folder_path, unique_filename)
                
                try:

                    image_file.save(file_save_path)
                    
                    # Aquí podrías querer eliminar la imagen antigua si existe y es diferente
                    if current_image_url:
                        old_image_abs_path= os.path.join(current_app.root_path, 'static', current_image_url)
                        if os.path.exists(old_image_abs_path):
                            try:
                                os.remove(old_image_abs_path)
                                current_app.logger.info(f"Imagen antigua eliminada: {old_image_abs_path}")
                            except Exception as del_err:
                                current_app.logger.error(f"Error al eliminar la imagen antigua {old_image_abs_path}: {del_err}")
                    
                    # Ruta relativa a 'static/' para la BD
                    path_parts = current_app.config['UPLOAD_FOLDER'].split(os.path.sep)
    
                    # Si el primer componente es 'static', lo omitimos para la ruta relativa en la BD
                    if path_parts and path_parts[0].lower() == 'static': # Usar lower() por si acaso
                        relative_upload_dir_for_db = os.path.join(*path_parts[1:])
                    else:
                        # Si UPLOAD_FOLDER no empieza con 'static', algo es inesperado, pero usa el path completo
                        # (esto no debería pasar con tu config actual)
                        relative_upload_dir_for_db = current_app.config['UPLOAD_FOLDER']
                    image_filename_to_save_for_db = os.path.join(relative_upload_dir_for_db, unique_filename).replace("\\", "/")
                    current_app.logger.info(f"Nueva imagen guardada en: {file_save_path}, para BD: {image_filename_to_save_for_db}")
                except Exception as e:
                    current_app.logger.error(f"Error al guardar la nueva imagen durante edición: {e}")
                    flash('Hubo un error al guardar la nueva imagen.', 'danger')
                    image_filename_to_save_for_db = current_image_url # Mantener la antigua si falla la nueva
            else:
                flash('Tipo de archivo de imagen no permitido al editar. Se mantuvo la imagen actual.', 'warning')
                # No cambiamos image_filename_to_save_for_db, se queda la actual.

        if not name or not price_str:
            flash('El nombre y el precio del ítem son obligatorios.', 'danger')
            # Volvemos a renderizar el form con los datos actuales y el error
            return render_template('menu_item_form.html', 
                                   form_action_title=f"Editar Ítem: {item_to_edit['name']}", 
                                   restaurant=restaurant, 
                                   item_data=request.form, # Enviar los datos del form actual para repoblar
                                   editing_item_id=item_id) # Para la acción del formulario

        try:
            price = float(price_str)
            if price < 0:
                raise ValueError("El precio no puede ser negativo.")
        except ValueError:
            flash('El precio debe ser un número válido.', 'danger')
            return render_template('menu_item_form.html', 
                                   form_action_title=f"Editar Ítem: {item_to_edit['name']}", 
                                   restaurant=restaurant, 
                                   item_data=request.form,
                                   editing_item_id=item_id)

        # Llamar a la función de db.py para actualizar el ítem
        # Nota: image_url no se está actualizando en este ejemplo simple, puedes añadirlo.
        success = update_menu_item_in_db(
            item_id=item_id,
            name=name,
            description=description,
            price=price,
            is_available=is_available,
            image_url=image_filename_to_save_for_db
        )

        if success:
            flash(f'Ítem "{name}" actualizado con éxito.', 'success')
            return redirect(url_for('restaurant.manage_menu', restaurant_id=restaurant_id))
        else:
            flash('Error al actualizar el ítem. Inténtalo de nuevo.', 'danger')
            # Quedarse en el formulario, idealmente con los datos para no perderlos
            return render_template('menu_item_form.html', 
                                   form_action_title=f"Editar Ítem: {item_to_edit['name']}", 
                                   restaurant=restaurant, 
                                   item_data=request.form, # Repoblar con los datos que fallaron
                                   editing_item_id=item_id)
    
    # Método GET: Mostrar el formulario con los datos del ítem a editar
    # item_to_edit ya es un diccionario (RealDictRow), así que se puede pasar directamente
    return render_template('restaurant/menu_item_form.html', 
                           form_action_title=f"Editar Ítem: {item_to_edit.get('name', 'Desconocido')}", 
                           restaurant=restaurant, 
                           item_data=item_to_edit, # Pasar los datos actuales del ítem
                           editing_item_id=item_id) # Para que el action del form sea correcto

@restaurant_bp.route('/<int:restaurant_id>/menu/eliminar/<int:item_id>', methods=['POST'])
@restaurant_owner_required
def delete_menu_item_for_restaurant(restaurant_id, item_id):
    owner_id = session.get('user_id')
    restaurant = get_restaurant_by_id(restaurant_id)

    # Verificar propiedad del restaurante
    if not restaurant or restaurant.get('user_id') != owner_id:
        flash('Acción no permitida.', 'danger')
        return redirect(url_for('restaurant.dashboard'))

    # Verificar que el ítem pertenezca al restaurante (opcional, pero bueno)
    item_to_delete = get_menu_item_by_id(item_id)
    if not item_to_delete or item_to_delete.get('restaurant_id') != restaurant_id:
        flash('Ítem no encontrado o no pertenece a este restaurante.', 'danger')
        return redirect(url_for('restaurant.manage_menu', restaurant_id=restaurant_id))

    try:
        success = delete_menu_item_from_db(item_id)
        if success:
            flash(f'Ítem "{item_to_delete.get("name", "ID:"+str(item_id))}" eliminado del menú con éxito.', 'success')
        else:
            # Esto podría pasar si el ítem ya fue eliminado por otra acción o no existía.
            flash(f'No se pudo eliminar el ítem "{item_to_delete.get("name", "ID:"+str(item_id))}". Puede que ya no exista.', 'warning')
    except psycopg2.Error as db_error:
        # Específicamente para PostgreSQL, el código '23503' es foreign_key_violation
        if hasattr(db_error, 'pgcode') and db_error.pgcode == '23503':
            flash(f'No se puede eliminar el ítem "{item_to_delete.get("name")}" porque está asociado a pedidos existentes.', 'danger')
        else:
            flash(f'Error de base de datos al intentar eliminar el ítem: {db_error}', 'danger')
        current_app.logger.error(f"Error de BD al eliminar item {item_id} del restaurante {restaurant_id}: {db_error}")
    except Exception as e:
        flash(f'Ocurrió un error inesperado al eliminar el ítem: {e}', 'danger')
        current_app.logger.error(f"Error inesperado al eliminar item {item_id} del restaurante {restaurant_id}: {e}")
        
    return redirect(url_for('restaurant.manage_menu', restaurant_id=restaurant_id))

@restaurant_bp.route('/<int:restaurant_id>/pedidos')
@restaurant_owner_required
def view_restaurant_orders(restaurant_id):
    owner_id = session.get('user_id')
    restaurant = get_restaurant_by_id(restaurant_id)

    if not restaurant or restaurant.get('user_id') != owner_id:
        flash('No tienes permiso para ver los pedidos de este restaurante.', 'danger')
        return redirect(url_for('restaurant.dashboard'))

    # Podrías añadir filtros aquí basados en request.args, ej. request.args.get('status')
    # Por ahora, obtenemos todos los pedidos del restaurante.
    orders = get_orders_for_restaurant_from_db(restaurant_id)
    
    # Posibles estados para el dropdown de cambio de estado
    # Asegúrate que coincidan con tu ENUM 'order_status_enum'
    possible_statuses = ['pending', 'confirmed', 'preparing', 'out_for_delivery', 'delivered', 'cancelled']

    return render_template('restaurant/restaurant_orders.html', 
                           restaurant=restaurant, 
                           orders=orders,
                           possible_statuses=possible_statuses,
                           form_data={})

@restaurant_bp.route('/<int:restaurant_id>/pedidos/<int:order_id>/actualizar-estado', methods=['POST'])
@restaurant_owner_required
def update_restaurant_order_status(restaurant_id, order_id):
    owner_id = session.get('user_id')
    restaurant = get_restaurant_by_id(restaurant_id)

    # Verificar propiedad del restaurante
    if not restaurant or restaurant.get('user_id') != owner_id:
        flash('Acción no permitida.', 'danger')
        return redirect(url_for('restaurant.dashboard'))

    # (Opcional pero recomendado: verificar que el order_id pertenezca a este restaurant_id)
    order_to_update = get_order_details_by_id(order_id) # Necesitarías esta función o una similar
    if not order_to_update or order_to_update[0].get('restaurant_id') != restaurant_id:
        flash('Este pedido no pertenece a tu restaurante.', 'danger')
        return redirect(url_for('restaurant.view_restaurant_orders', restaurant_id=restaurant_id))

    new_status = request.form.get('new_status')
    valid_statuses = ['pending', 'confirmed', 'preparing', 'out_for_delivery', 'delivered', 'cancelled', 'failed'] # De tu ENUM
    
    if new_status not in valid_statuses:
        flash('Estado inválido seleccionado.', 'danger')
        return redirect(url_for('restaurant.view_restaurant_orders', restaurant_id=restaurant_id))
    else:
        success = update_order_status_in_db(order_id, new_status)

    if success:
        flash(f'Estado del pedido #{order_id} actualizado a "{new_status.replace("_", " ").capitalize()}".', 'success')
    else:
        flash(f'Error al actualizar el estado del pedido #{order_id}.', 'danger')
        
    return redirect(url_for('restaurant.view_restaurant_orders', restaurant_id=restaurant_id))


@restaurant_bp.route('/<int:restaurant_id>/editar', methods=['GET', 'POST'])
@restaurant_owner_required
def edit_restaurant_info(restaurant_id):
    owner_id = session.get('user_id')
    restaurant_to_edit = get_restaurant_by_id(restaurant_id) 

    if not restaurant_to_edit:
        current_app.logger.warning(f"Intento de editar restaurante no existente: ID {restaurant_id} por usuario {owner_id}")
        abort(404)
    
    if restaurant_to_edit.get('user_id') != owner_id:
        flash('No tienes permiso para editar la información de este restaurante.', 'danger')
        current_app.logger.warning(f"Dueño {owner_id} intentó acceso no autorizado para editar restaurante ID {restaurant_id}")
        return redirect(url_for('restaurant.dashboard'))

    if request.method == 'POST':
        current_app.logger.info(f"--- INICIO PROCESO EDIT RESTAURANT ID: {restaurant_id} ---")
        name = request.form.get('name')
        description = request.form.get('description', '')
        address = request.form.get('address', '')
        phone_number = request.form.get('phone_number', '')
        is_active = request.form.get('is_active') == 'on'

        logo_image_file = request.files.get('restaurant_logo_image')
        # Inicia con el logo actual; se actualizará si se sube uno nuevo y se guarda bien.
        logo_filename_to_pass_to_db = restaurant_to_edit.get('logo_image_url') 
        current_app.logger.info(f"Logo actual en BD (antes de procesar): {logo_filename_to_pass_to_db}")

        if not name:
            flash('El nombre del restaurante es obligatorio.', 'danger')
            return render_template('restaurant/edit_restaurant_form.html', 
                                   restaurant=request.form, 
                                   current_logo_url=logo_filename_to_pass_to_db,
                                   restaurant_id=restaurant_id) 

        if logo_image_file and logo_image_file.filename != '':
            current_app.logger.info(f"Archivo de logo detectado: {logo_image_file.filename}")
            if allowed_file(logo_image_file.filename):
                original_filename = secure_filename(logo_image_file.filename)
                extension = original_filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}.{extension}"
                current_app.logger.info(f"Nombre de archivo único generado: {unique_filename}")
                
                upload_folder_config_key = 'UPLOAD_FOLDER_RESTAURANT_LOGOS' # Asegúrate que esta key exista en tu config
                upload_folder_relative_path = current_app.config.get(upload_folder_config_key)
                current_app.logger.info(f"Ruta relativa de subida desde config: {upload_folder_relative_path}")

                if not upload_folder_relative_path:
                    flash('Error de configuración: Carpeta de subida de logos no definida.', 'danger')
                    current_app.logger.error(f"EDIT_RESTAURANT: {upload_folder_config_key} no está configurado.")
                else:
                    absolute_upload_folder = os.path.join(current_app.root_path, upload_folder_relative_path)
                    current_app.logger.info(f"Ruta absoluta para guardar archivo: {absolute_upload_folder}")
                    
                    if not os.path.exists(absolute_upload_folder):
                        try:
                            os.makedirs(absolute_upload_folder, exist_ok=True)
                            current_app.logger.info(f"Carpeta de subida creada: {absolute_upload_folder}")
                        except Exception as mkdir_e:
                            current_app.logger.error(f"EDIT_RESTAURANT: No se pudo crear la carpeta {absolute_upload_folder}: {mkdir_e}")
                            flash('Error interno al preparar la subida de imágenes.', 'danger')
                    
                    if os.path.exists(absolute_upload_folder):
                        file_save_path = os.path.join(absolute_upload_folder, unique_filename)
                        current_app.logger.info(f"Ruta completa para guardar el archivo: {file_save_path}")
                        try:
                            # Opcional: Borrar el logo antiguo del sistema de archivos
                            if restaurant_to_edit.get('logo_image_url'):
                                old_logo_path_relative_to_static = restaurant_to_edit.get('logo_image_url')
                                # current_app.static_folder es la ruta absoluta a la carpeta static de la app
                                old_logo_full_path = os.path.join(current_app.static_folder, old_logo_path_relative_to_static)
                                if os.path.exists(old_logo_full_path):
                                    os.remove(old_logo_full_path)
                                    current_app.logger.info(f"Logo antiguo {old_logo_path_relative_to_static} eliminado del servidor: {old_logo_full_path}")
                                else:
                                    current_app.logger.warning(f"Se intentó eliminar el logo antiguo pero no se encontró en: {old_logo_full_path}")
                            
                            logo_image_file.save(file_save_path)
                            
                            # ---- INICIO DE LA CORRECCIÓN IMPORTANTE ----
                            # Construir la ruta para guardar en la BD (relativa a la carpeta 'static')
                            # upload_folder_relative_path es tu config, ej: "static\uploads\restaurant_logos"
                            
                            normalized_relative_path = upload_folder_relative_path.replace("\\", "/")
                            
                            path_for_db_dir = normalized_relative_path
                            if normalized_relative_path.lower().startswith('static/'):
                                path_for_db_dir = normalized_relative_path[len('static/'):]
                            
                            # Asegurarse de que no haya slashes iniciales extras si path_for_db_dir quedó vacío
                            path_for_db_dir = path_for_db_dir.lstrip('/')

                            logo_filename_to_pass_to_db = f"{path_for_db_dir}/{unique_filename}"
                            # ---- FIN DE LA CORRECCIÓN IMPORTANTE ----
                            
                            current_app.logger.info(f"Logo guardado en: {file_save_path}. Ruta para BD: {logo_filename_to_pass_to_db}")
                            flash('Nuevo logo guardado con éxito.', 'info')
                        except Exception as e_save:
                            current_app.logger.error(f"Error al guardar el logo del restaurante: {e_save}", exc_info=True)
                            flash('Hubo un error al guardar el nuevo logo del restaurante.', 'danger')
                            logo_filename_to_pass_to_db = restaurant_to_edit.get('logo_image_url') # Revertir al antiguo si falla el guardado
            else: # Fin de if allowed_file
                if logo_image_file and logo_image_file.filename: # Solo mostrar error si se intentó subir un archivo no permitido
                    flash('Tipo de archivo de imagen no permitido. Se mantuvo la imagen actual si existía.', 'warning')
                    current_app.logger.warning(f"Tipo de archivo no permitido: {logo_image_file.filename}")
        else: # No se subió un archivo nuevo
            current_app.logger.info("No se proporcionó nuevo archivo de logo o el nombre de archivo está vacío.")

        current_app.logger.info(f"Valor de 'logo_filename_to_pass_to_db' ANTES de llamar a update_restaurant_details_in_db: {logo_filename_to_pass_to_db}")
        success = update_restaurant_details_in_db(
            restaurant_id, name, description, address, phone_number, is_active,
            logo_image_url=logo_filename_to_pass_to_db # Pasando la ruta (nueva o la original) a la función de BD
        )

        if success:
            flash(f'Información del restaurante "{name}" actualizada con éxito.', 'success')
            current_app.logger.info(f"Restaurante ID {restaurant_id} actualizado en BD. Success: {success}")
            return redirect(url_for('restaurant.dashboard'))
        else:
            flash('Error al actualizar la información del restaurante. Inténtalo de nuevo.', 'danger')
            current_app.logger.error(f"Fallo al actualizar restaurante ID {restaurant_id} en BD. Success: {success}")
            # Repoblar con request.form para que el usuario no pierda los cambios que intentó hacer
            return render_template('restaurant/edit_restaurant_form.html', 
                                   restaurant=request.form, 
                                   current_logo_url=restaurant_to_edit.get('logo_image_url'), # Mostrar el logo que estaba antes del intento fallido
                                   restaurant_id=restaurant_id)
    
    # Método GET: Mostrar el formulario con los datos actuales del restaurante
    return render_template('restaurant/edit_restaurant_form.html', 
                           restaurant=restaurant_to_edit, 
                           restaurant_id=restaurant_id)

