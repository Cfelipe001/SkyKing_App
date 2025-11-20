# app/routes_pages.py
from flask import render_template, session, redirect,flash, request, flash, redirect, url_for# session podría ser útil aquí en el futuro
from .routes_auth import login_required
# No es necesario importar 'app' de Flask aquí, ya que la instancia
# se pasará a la función init_pages_routes.

def init_pages_routes(app):
    """
    Inicializa las rutas para las páginas generales de la aplicación.
    """

    @app.route('/')
    def home_page(): # Renombrada de 'home' para evitar posible colisión y ser más descriptiva
        # Podrías pasar datos a la plantilla si es necesario, ej:
        # user_email = session.get('user_email')
        # return render_template('inicio.html', user_email=user_email)
        return render_template('inicio.html')

    @app.route('/restaurants_list.html')
    def show_pedidos_page():
        # Lógica para verificar si el usuario está logueado antes de mostrar
        # if 'user_id' not in session:
        #     return redirect(url_for('auth_routes.show_login_page')) # Asumiendo que login está en auth_routes
        return render_template('order/restaurants_list.html')

    @app.route('/pago.html')
    def show_pago_page():
        # Similar a pedidos, podrías requerir login
        return render_template('pago.html')

    @app.route('/inicio_cliente.html')
    # @login_required # Descomenta esto si quieres que esta página requiera login
    def inicio_cliente(): # <--- ESTE ES EL NOMBRE DE LA FUNCIÓN (Y EL ENDPOINT)
        # Aquí podrías pasar datos específicos para el dashboard del cliente si los necesitas
        # Por ahora, solo renderizamos la plantilla.
        # Asumimos que 'inicio_cliente.html' está en 'app/templates/user/inicio_cliente.html'
        # Si está en 'app/templates/inicio_cliente.html', usa solo 'inicio_cliente.html'
        if 'user_id' not in session or session.get('user_role') != 'user': # Simple verificación de rol
            flash("Acceso no autorizado o necesitas ser un cliente.", "warning")
            return redirect(('home_page')) # O a login

        return render_template('inicio_cliente.html')
    
# app/routes_pages.py
# ... (importaciones existentes, y la función init_pages_routes) ...
# from flask import request, flash, redirect # Añade request, flash, redirect si los usas en el POST

# dentro de init_pages_routes(app):
    # ... (tus otras rutas como home_page, inicio_cliente_dashboard) ...

    @app.route('/soporte', methods=['GET', 'POST'])
    @login_required # Probablemente quieras que solo usuarios logueados envíen solicitudes
    def support_page(): # Nombre del endpoint: 'support_page'
        if request.method == 'POST':
            # Aquí iría la lógica para procesar la solicitud de soporte:
            # subject = request.form.get('subject')
            # category = request.form.get('category')
            # description = request.form.get('description')
            # ... (guardar en BD, enviar email, etc.) ...
            flash('Tu solicitud de soporte ha sido enviada. Te contactaremos pronto.', 'success')
            return redirect(url_for('support_page')) # Redirigir a la misma página para ver el mensaje

        # Para el método GET, o después del POST si no hubo redirección específica
        return render_template('soporte.html')