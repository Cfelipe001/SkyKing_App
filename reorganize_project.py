#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reorganize_project.py
Script para reorganizar el proyecto SkyKing según estándares profesionales
y requisitos del profesor.
"""

import os
import shutil
from pathlib import Path

def print_header(text):
    """Imprime un encabezado formateado"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def create_directory_structure():
    """Crea la estructura de directorios profesional"""
    
    print_header("CREANDO NUEVA ESTRUCTURA DE DIRECTORIOS")
    
    directories = [
        # Estructura principal
        "app",
        "app/models",
        "app/controllers", 
        "app/views",
        "app/utils",
        "app/config",
        
        # Tests
        "tests",
        "tests/unit",
        "tests/integration",
        
        # Documentación
        "docs",
        "docs/diagramas",
        "docs/manuales",
        "docs/arquitectura",
        
        # CI/CD
        ".github",
        ".github/workflows",
        
        # Recursos estáticos (ya existe pero verificamos)
        "static",
        "static/css",
        "static/js",
        "static/images",
        "static/uploads",
        
        # Templates (ya existe)
        "templates",
        
        # Scripts auxiliares
        "scripts",
        
        # Logs
        "logs",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Creado/Verificado: {directory}/")
    
    print("\n✅ Estructura de directorios creada exitosamente")

def reorganize_app_files():
    """Reorganiza los archivos de la carpeta app según la nueva estructura"""
    
    print_header("REORGANIZANDO ARCHIVOS DE LA APLICACIÓN")
    
    # Mover archivos de configuración
    config_files = ['config.py', 'db.py']
    for file in config_files:
        src = f"app/{file}"
        dst = f"app/config/{file}"
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"✓ Copiado: {src} → {dst}")
    
    # Los routes se consideran controllers
    routes_files = [f for f in os.listdir('app') if f.startswith('routes_') and f.endswith('.py')]
    for file in routes_files:
        src = f"app/{file}"
        dst = f"app/controllers/{file.replace('routes_', '')}"
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"✓ Copiado: {src} → {dst}")
    
    # services.py y sockets.py van a utils
    utils_files = ['services.py', 'sockets.py']
    for file in utils_files:
        src = f"app/{file}"
        dst = f"app/utils/{file}"
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"✓ Copiado: {src} → {dst}")
    
    print("\n✅ Archivos reorganizados (copias de seguridad mantenidas)")
    print("⚠️  Los archivos originales se mantienen. Verifica que todo funcione antes de eliminarlos.")

def copy_documentation():
    """Copia la documentación existente a la carpeta docs"""
    
    print_header("ORGANIZANDO DOCUMENTACIÓN")
    
    # Copiar el PDF principal
    pdf_source = "Documento_SkyKing_-_Proyecto_Ingenieria_del_Software_II.pdf"
    if os.path.exists(pdf_source):
        shutil.copy2(pdf_source, "docs/Documentacion_Tecnica_SkyKing.pdf")
        print(f"✓ Copiado: {pdf_source} → docs/")
    
    # Crear archivos README en subdirectorios
    readme_docs = {
        "docs/diagramas/README.md": "# Diagramas UML del Proyecto SkyKing\n\nAquí se almacenan todos los diagramas UML del sistema.",
        "docs/manuales/README.md": "# Manuales del Sistema SkyKing\n\nContiene:\n- Manual de Usuario\n- Manual Técnico",
        "docs/arquitectura/README.md": "# Arquitectura del Sistema\n\nDiagramas de arquitectura y componentes."
    }
    
    for path, content in readme_docs.items():
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Creado: {path}")
    
    print("\n✅ Documentación organizada")

def create_missing_files():
    """Crea archivos faltantes esenciales"""
    
    print_header("CREANDO ARCHIVOS ESENCIALES")
    
    files_created = []
    
    # Ya tenemos estos, pero verificamos
    essential_files = ['README.md', 'requirements.txt', 'run.py', '.gitignore']
    for file in essential_files:
        if os.path.exists(file):
            print(f"✓ Ya existe: {file}")
        else:
            print(f"⚠️  Falta: {file} (debes crearlo)")
    
    print("\n✅ Verificación de archivos esenciales completada")

def create_init_files():
    """Crea archivos __init__.py donde sean necesarios"""
    
    print_header("CREANDO ARCHIVOS __init__.py")
    
    init_locations = [
        "app/models/__init__.py",
        "app/controllers/__init__.py",
        "app/views/__init__.py",
        "app/utils/__init__.py",
        "app/config/__init__.py",
        "tests/__init__.py",
        "tests/unit/__init__.py",
        "tests/integration/__init__.py",
    ]
    
    for location in init_locations:
        if not os.path.exists(location):
            with open(location, 'w', encoding='utf-8') as f:
                f.write('# -*- coding: utf-8 -*-\n')
            print(f"✓ Creado: {location}")
        else:
            print(f"✓ Ya existe: {location}")
    
    print("\n✅ Archivos __init__.py creados")

def show_new_structure():
    """Muestra la nueva estructura del proyecto"""
    
    print_header("NUEVA ESTRUCTURA DEL PROYECTO SKYKING")
    
    structure = """
    SkyKing_Web/
    │
    ├── app/                           # Código principal de la aplicación
    │   ├── __init__.py               # Inicialización de Flask
    │   ├── models/                   # Modelos de datos (futuro)
    │   │   └── __init__.py
    │   ├── controllers/              # Lógica de negocio (routes reorganizados)
    │   │   ├── __init__.py
    │   │   ├── admin.py
    │   │   ├── auth.py
    │   │   ├── delivery.py
    │   │   └── ...
    │   ├── views/                    # Endpoints y vistas (futuro)
    │   │   └── __init__.py
    │   ├── utils/                    # Funciones auxiliares
    │   │   ├── __init__.py
    │   │   ├── services.py
    │   │   └── sockets.py
    │   └── config/                   # Configuraciones
    │       ├── __init__.py
    │       ├── config.py
    │       └── db.py
    │
    ├── tests/                        # Pruebas unitarias e integración
    │   ├── __init__.py
    │   ├── unit/                     # Pruebas unitarias
    │   │   └── __init__.py
    │   └── integration/              # Pruebas de integración
    │       └── __init__.py
    │
    ├── docs/                         # Documentación técnica
    │   ├── Documentacion_Tecnica_SkyKing.pdf
    │   ├── diagramas/               # Diagramas UML
    │   ├── manuales/                # Manuales de usuario y técnico
    │   └── arquitectura/            # Documentación de arquitectura
    │
    ├── templates/                    # Plantillas HTML (Jinja2)
    │   └── ...
    │
    ├── static/                       # Archivos estáticos
    │   ├── css/
    │   ├── js/
    │   ├── images/
    │   └── uploads/
    │
    ├── scripts/                      # Scripts auxiliares
    │
    ├── logs/                         # Archivos de log
    │
    ├── .github/                      # Configuración CI/CD
    │   └── workflows/
    │       └── ci.yml
    │
    ├── run.py                        # Punto de entrada principal
    ├── requirements.txt              # Dependencias
    ├── README.md                     # Documentación principal
    ├── LICENSE                       # Licencia del proyecto
    ├── .env.example                  # Plantilla de variables
    ├── .gitignore                    # Archivos a ignorar
    └── verify_system.py             # Script de verificación
    """
    
    print(structure)
    print("\n✅ Esta es la nueva estructura profesional")

def main():
    """Función principal"""
    
    print("\n" + "=" * 80)
    print("  🚁 REORGANIZACIÓN DEL PROYECTO SKYKING 🚁")
    print("=" * 80)
    print("\nEste script reorganizará tu proyecto según estándares profesionales")
    print("y los requisitos del profesor.")
    print("\n⚠️  IMPORTANTE: Este script creará COPIAS de los archivos.")
    print("Los archivos originales se mantendrán intactos.")
    print("\nPresiona Enter para continuar o Ctrl+C para cancelar...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario")
        return
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists('app') or not os.path.exists('run.py'):
        print("\n❌ ERROR: Este script debe ejecutarse desde la raíz del proyecto SkyKing_Web")
        print("   Asegúrate de estar en la carpeta que contiene 'app/' y 'run.py'")
        return
    
    # Ejecutar reorganización
    create_directory_structure()
    reorganize_app_files()
    copy_documentation()
    create_missing_files()
    create_init_files()
    show_new_structure()
    
    print_header("✅ REORGANIZACIÓN COMPLETADA")
    print("\nPróximos pasos:")
    print("1. Verifica que la aplicación sigue funcionando: python run.py")
    print("2. Revisa los archivos copiados en las nuevas carpetas")
    print("3. Una vez verificado, puedes eliminar los archivos originales duplicados")
    print("4. Actualiza los imports en __init__.py si es necesario")
    print("5. Corre los tests (cuando los crees): pytest tests/")
    print("\n¡Listo para crear la documentación técnica completa!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Reorganización interrumpida por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error durante la reorganización: {e}")
        import traceback
        traceback.print_exc()
