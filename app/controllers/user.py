# app/routes_user.py
from flask import (
    Blueprint, render_template, session, redirect, url_for, flash, 
    current_app, request, abort
)
from werkzeug.utils import secure_filename
import os
import uuid

# Asumiendo que login_required está en app/decorators.py o accesible de otra forma
from .routes_pages import login_required 
# Asegúrate que estas funciones de db.py las vas a crear o ya existen y son compatibles
from .db import (
    get_user_profile_data, # La usaremos para cargar los datos iniciales
    update_user_profile_data, 
    update_user_profile_picture_url, 
    verify_user_password, # Para verificar la contraseña actual antes de cambiarla
    update_user_password_hash # Para guardar la nueva contraseña hasheada
)

user_bp = Blueprint('user', __name__, url_prefix='/usuario') 

# Función para verificar extensiones de archivo (puedes moverla a un archivo utils si la usas en más sitios)
def allowed_file(filename):
    # Asegúrate que ALLOWED_PROFILE_PIC_EXTENSIONS esté en tu config de Flask
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_PROFILE_PIC_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})

@user_bp.route('/mi_cuenta', methods=['GET', 'POST'])
@login_required
def mi_cuenta():
    user_id = session.get('user_id')
    # Usamos tu función existente para obtener los datos del perfil
    # Asegúrate que get_user_profile_data devuelva 'profile_picture_url' y otros campos necesarios
    user_data = get_user_profile_data(user_id) 

    if not user_data:
        flash("No se pudo cargar tu información de perfil.", "danger")
        # Redirige a una página principal o de error apropiada
        return redirect(url_for('main.home_page')) # Ajusta 'main.home_page' al nombre de tu ruta principal

    # Convertir a dict para poder modificarlo si es necesario (ej. añadir placeholders como hiciste)
    # O si get_user_profile_data ya devuelve un dict, no es necesario.
    # psycopg2.extras.RealDictRow se comporta como un diccionario, así que usualmente está bien.
    
    if request.method == 'POST':
        action = request.form.get('action') # Identifica qué formulario se envió

        if action == 'update_profile_data':
            full_name = request.form.get('full_name', user_data.get('full_name')) # Tomar valor actual si no se envía
            phone_number = request.form.get('phone_number', user_data.get('phone_number'))
            # address = request.form.get('address') # Si añades dirección

            if not full_name: # Validación simple
                flash('El nombre completo es obligatorio.', 'warning')
            # Aquí puedes añadir más validaciones para phone_number, etc.
            elif update_user_profile_data(user_id, full_name, phone_number): # Modifica esta función en db.py
                flash('Datos del perfil actualizados con éxito.', 'success')
                current_app.logger.info(f"Usuario {user_id} actualizó sus datos de perfil.")
            else:
                flash('Error al actualizar los datos del perfil.', 'danger')
            return redirect(url_for('user.mi_cuenta')) # Recargar la página

        elif action == 'update_profile_picture':
            profile_pic_file = request.files.get('profile_picture')

            if profile_pic_file and profile_pic_file.filename:
                if allowed_file(profile_pic_file.filename):
                    original_filename = secure_filename(profile_pic_file.filename)
                    extension = original_filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4()}.{extension}"
                    
                    upload_folder_key = 'UPLOAD_FOLDER_PROFILE_PICS' # Ej: 'static/uploads/profile_pics'
                    # Usar current_app.static_folder para la base y luego la ruta relativa
                    # La ruta guardada en BD debe ser relativa a la carpeta static principal
                    # Ej: si UPLOAD_FOLDER_PROFILE_PICS = 'uploads/profile_pics' (sin static/ al inicio)
                    # Y tu carpeta static es 'app/static/', entonces la imagen se guarda en 'app/static/uploads/profile_pics'
                    # Y en la BD se guarda 'uploads/profile_pics/unique_filename.ext'
                    
                    # Directorio donde se guardarán las fotos de perfil (relativo a la carpeta 'static')
                    # Asegúrate que UPLOAD_FOLDER_PROFILE_PICS en tu config NO empiece con 'static/'
                    # Debe ser algo como 'uploads/profile_pics'
                    profile_pics_dir_relative_to_static = current_app.config.get(upload_folder_key, 'uploads/profile_pics')
                    
                    # Ruta absoluta para guardar el archivo en el servidor
                    absolute_upload_dir = os.path.join(current_app.static_folder, profile_pics_dir_relative_to_static)
                    
                    if not os.path.exists(absolute_upload_dir):
                        os.makedirs(absolute_upload_dir, exist_ok=True)
                    
                    file_save_path = os.path.join(absolute_upload_dir, unique_filename)
                    
                    try:
                        # Eliminar foto antigua si existe
                        if user_data.get('profile_picture_url'):
                            # La URL guardada es relativa a static, ej: "uploads/profile_pics/old.jpg"
                            old_pic_path_in_static = user_data['profile_picture_url']
                            old_pic_absolute_path = os.path.join(current_app.static_folder, old_pic_path_in_static)
                            if os.path.exists(old_pic_absolute_path):
                                os.remove(old_pic_absolute_path)
                                current_app.logger.info(f"Foto de perfil antigua eliminada: {old_pic_absolute_path}")
                        
                        profile_pic_file.save(file_save_path)
                        
                        # Ruta para guardar en BD (relativa a la carpeta static)
                        db_pic_path = os.path.join(profile_pics_dir_relative_to_static, unique_filename).replace("\\", "/")
                        
                        if update_user_profile_picture_url(user_id, db_pic_path): # Función a crear en db.py
                            flash('Foto de perfil actualizada con éxito.', 'success')
                            current_app.logger.info(f"Usuario {user_id} actualizó foto a {db_pic_path}")
                        else:
                            flash('Error al actualizar la foto de perfil en la base de datos.', 'danger')
                    except Exception as e:
                        flash(f'Error al guardar la foto de perfil: {str(e)}', 'danger')
                        current_app.logger.error(f"Error guardando foto de perfil para user {user_id}: {e}", exc_info=True)
                else:
                    flash('Tipo de archivo no permitido para la foto de perfil.', 'warning')
            else:
                flash('No se seleccionó ningún archivo para la foto de perfil.', 'info')
            return redirect(url_for('user.mi_cuenta'))

        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_new_password = request.form.get('confirm_new_password')

            if not all([current_password, new_password, confirm_new_password]):
                flash('Todos los campos de contraseña son obligatorios.', 'warning')
            elif new_password != confirm_new_password:
                flash('La nueva contraseña y la confirmación no coinciden.', 'warning')
            elif len(new_password) < 6: # Ejemplo de validación
                flash('La nueva contraseña debe tener al menos 6 caracteres.', 'warning')
            else:
                # werkzeug.security debe estar importado donde definas verify_user_password y update_user_password_hash
                if verify_user_password(user_id, current_password): 
                    if update_user_password_hash(user_id, new_password): # Esta función debe hashear la new_password
                        flash('Contraseña actualizada con éxito.', 'success')
                        current_app.logger.info(f"Usuario {user_id} actualizó su contraseña.")
                    else:
                        flash('Error al actualizar la contraseña.', 'danger')
                else:
                    flash('La contraseña actual es incorrecta.', 'danger')
            return redirect(url_for('user.mi_cuenta'))

    # Para la solicitud GET, o si un POST no redirige (aunque todos los POST deberían redirigir)
    return render_template('/templates/mi_perfil.html', user=user_data)
    # Asegúrate que 'mi_perfil.html' esté en 'app/templates/user_templates/'

# Puedes eliminar o comentar tu ruta @user_bp.route('/perfil') si '/mi_cuenta' la reemplaza completamente.
# O mantenerla si sirve para un propósito diferente (ej. un perfil público vs. perfil editable)
# Si la eliminas, asegúrate de actualizar cualquier url_for que apunte a 'user.view_profile'.