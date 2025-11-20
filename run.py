#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py
Punto de entrada principal para la aplicación SkyKing.
Ejecuta el servidor Flask con SocketIO.
"""

import os
import sys

# Asegurar que el directorio raíz del proyecto esté en el path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importar la función de creación de la app y socketio
from app import create_app, socketio

# Crear la instancia de la aplicación
app = create_app()

if __name__ == '__main__':
    # Configuración del servidor
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = app.config.get('DEBUG', True)
    
    print("=" * 80)
    print("🚁 SISTEMA SKYKING - SERVIDOR INICIANDO 🚁")
    print("=" * 80)
    print(f"🌐 Host: {host}")
    print(f"🔌 Puerto: {port}")
    print(f"🐛 Modo Debug: {debug}")
    print(f"📁 Directorio de trabajo: {project_root}")
    print("=" * 80)
    print("\n✅ Servidor listo. Presiona CTRL+C para detener.\n")
    
    # Ejecutar la aplicación con SocketIO
    # use_reloader=False evita que el servidor se reinicie dos veces en debug mode
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=True,
        log_output=True
    )