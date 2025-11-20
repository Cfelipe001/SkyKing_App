#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_system.py
Script de verificación del sistema SkyKing.
Verifica que todos los componentes estén correctamente configurados.
"""

import sys
import os

def print_header(text):
    """Imprime un encabezado formateado"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_check(name, status, message=""):
    """Imprime el resultado de una verificación"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name}")
    if message:
        print(f"   → {message}")

def check_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    required = (3, 9)
    status = version >= required
    message = f"Python {version.major}.{version.minor}.{version.micro}"
    if not status:
        message += f" (Se requiere Python {required[0]}.{required[1]} o superior)"
    return status, message

def check_module(module_name):
    """Verifica si un módulo está instalado"""
    try:
        __import__(module_name)
        return True, f"{module_name} instalado"
    except ImportError:
        return False, f"{module_name} NO instalado - ejecuta: pip install {module_name}"

def check_file_exists(filepath, description):
    """Verifica si un archivo existe"""
    exists = os.path.exists(filepath)
    if exists:
        return True, f"{description} encontrado"
    else:
        return False, f"{description} NO encontrado en: {filepath}"

def check_env_file():
    """Verifica el archivo .env"""
    if not os.path.exists('.env'):
        return False, "Archivo .env no encontrado. Copia .env.example a .env y configúralo"
    
    # Verificar variables críticas
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        critical_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing = [var for var in critical_vars if not os.getenv(var)]
        
        if missing:
            return False, f"Variables faltantes en .env: {', '.join(missing)}"
        
        return True, "Archivo .env configurado"
    except ImportError:
        return False, "python-dotenv no instalado"

def check_database_connection():
    """Verifica la conexión a PostgreSQL"""
    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'Dron1'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'port': os.getenv('DB_PORT', '5432')
        }
        
        conn = psycopg2.connect(**conn_params)
        conn.close()
        return True, f"Conexión exitosa a BD: {conn_params['database']}"
    except Exception as e:
        return False, f"Error de conexión a BD: {str(e)}"

def main():
    """Función principal de verificación"""
    print_header("🚁 VERIFICACIÓN DEL SISTEMA SKYKING 🚁")
    
    # Verificar Python
    print_header("1. Verificando Python")
    status, msg = check_python_version()
    print_check("Versión de Python", status, msg)
    
    # Verificar módulos críticos
    print_header("2. Verificando Dependencias")
    modules = [
        'flask',
        'flask_cors',
        'flask_socketio',
        'psycopg2',
        'cryptography',
        'requests'
    ]
    
    all_modules_ok = True
    for module in modules:
        status, msg = check_module(module)
        print_check(module, status, msg)
        all_modules_ok = all_modules_ok and status
    
    # Verificar archivos críticos
    print_header("3. Verificando Archivos del Proyecto")
    files_to_check = [
        ('run.py', 'Archivo principal'),
        ('requirements.txt', 'Lista de dependencias'),
        ('app/__init__.py', 'Inicialización de Flask'),
        ('app/config.py', 'Configuración'),
        ('app/db.py', 'Funciones de BD')
    ]
    
    all_files_ok = True
    for filepath, description in files_to_check:
        status, msg = check_file_exists(filepath, description)
        print_check(description, status, msg)
        all_files_ok = all_files_ok and status
    
    # Verificar archivo .env
    print_header("4. Verificando Configuración")
    status, msg = check_env_file()
    print_check("Archivo .env", status, msg)
    
    # Verificar conexión a BD
    print_header("5. Verificando Base de Datos")
    status, msg = check_database_connection()
    print_check("Conexión PostgreSQL", status, msg)
    
    # Resumen final
    print_header("📊 RESUMEN")
    if all_modules_ok and all_files_ok and status:
        print("\n✅ ¡TODO LISTO! El sistema está correctamente configurado.")
        print("   Ejecuta: python run.py\n")
    else:
        print("\n⚠️  HAY PROBLEMAS QUE CORREGIR")
        print("   Revisa los errores marcados con ❌ arriba\n")
        print("   Consulta README_RECUPERACION.md para soluciones\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación interrumpida por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error inesperado durante la verificación: {e}")
        import traceback
        traceback.print_exc()
