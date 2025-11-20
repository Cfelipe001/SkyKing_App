# SkyKing - Sistema de Entregas con Drones Autónomos

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Descripción

**SkyKing** es un sistema innovador de entregas a domicilio que utiliza **drones autónomos** para realizar envíos rápidos, seguros y eficientes en zonas urbanas. El sistema integra:

- 🚁 Gestión de flotas de drones en tiempo real
- 📱 Plataforma web responsive para clientes y operadores
- 📊 Monitoreo en tiempo real con WebSockets
- 🔐 Sistema de autenticación y autorización por roles
- 🗺️ Integración con Google Maps para tracking
- 💳 Pasarelas de pago (Nequi, PSE)
- ☁️ Integración con Azure IoT Central para telemetría

---

## Equipo de Desarrollo

**Proyecto de Ingeniería del Software II**

- **Autor:** Cristian Felipe Gómez Manrique
- **Institución:** Universidad Autónoma de Bucaramanga (UNAB)
- **Facultad:** Ingeniería de Sistemas
- **Año:** 2025

---

##  Arquitectura del Sistema

### Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| **Backend** | Flask (Python 3.9+) |
| **Base de Datos** | PostgreSQL 14+ |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Tiempo Real** | Flask-SocketIO |
| **IoT** | Azure IoT Central |
| **Mapas** | Google Maps API |
| **Seguridad** | Cryptography, Werkzeug |

### Arquitectura en Capas

```
┌─────────────────────────────────────────┐
│          CAPA DE PRESENTACIÓN           │
│    (Templates HTML + CSS + JS)          │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         CAPA DE CONTROLADORES           │
│  (Routes: Admin, Auth, Delivery, etc.)  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│          CAPA DE NEGOCIO                │
│        (Services, Sockets)              │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         CAPA DE DATOS                   │
│        (PostgreSQL + db.py)             │
└─────────────────────────────────────────┘
```

---

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.9 o superior
- PostgreSQL 14 o superior
- Git (opcional)
- pip y venv

### 1. Clonar o Descargar el Proyecto

```bash
git clone https://github.com/tu-usuario/skyking.git
cd skyking
```

### 2. Crear Entorno Virtual

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
# Copiar plantilla
cp .env.example .env

# Editar .env con tus credenciales
# Asegúrate de configurar:
# - DB_PASSWORD
# - FLASK_SECRET_KEY
# - FLASK_FERNET_KEY
```

### 5. Configurar Base de Datos

```sql
-- Conectar a PostgreSQL
psql -U postgres

-- Crear base de datos
CREATE DATABASE Dron1;

-- Ejecutar scripts de creación de tablas (si los tienes)
-- \i scripts/create_tables.sql
```

### 6. Verificar Instalación

```bash
python verify_system.py
```

### 7. Ejecutar la Aplicación

```bash
# Opción 1: Script directo
python run.py

# Opción 2: Windows batch
start.bat

# Opción 3: Flask CLI
flask run
```

La aplicación estará disponible en: **http://localhost:5000**

---

## 👤 Roles de Usuario

El sistema soporta múltiples roles:

| Rol | Descripción | Acceso |
|-----|-------------|--------|
| **Cliente** | Usuario final que realiza pedidos | Portal de pedidos, seguimiento |
| **Operador** | Supervisa drones y entregas | Dashboard de monitoreo |
| **Administrador** | Gestión completa del sistema | Panel de administración |
| **Aliado Comercial** | Restaurantes/tiendas asociadas | Gestión de productos y pedidos |
| **Técnico** | Mantenimiento de drones | Panel de mantenimiento |

---

## 🔑 Funcionalidades Principales

### Para Clientes
- ✅ Registro e inicio de sesión
- ✅ Realizar pedidos de productos
- ✅ Seguimiento en tiempo real con mapa
- ✅ Historial de pedidos
- ✅ Sistema de puntos
- ✅ Notificaciones de estado

### Para Operadores
- ✅ Dashboard de monitoreo de drones
- ✅ Visualización de telemetría en tiempo real
- ✅ Gestión de alertas
- ✅ Asignación de rutas
- ✅ Reportes de rendimiento

### Para Administradores
- ✅ Gestión de usuarios y permisos
- ✅ Administración de flotas de drones
- ✅ Configuración de zonas de cobertura
- ✅ Reportes estadísticos
- ✅ Gestión de aliados comerciales

---

## Pruebas

### Ejecutar Tests

```bash
# Todos los tests
pytest tests/

# Tests unitarios
pytest tests/unit/

# Tests de integración
pytest tests/integration/

# Con cobertura
pytest --cov=app tests/
```

### Tests Disponibles

- Tests de autenticación
- Tests de base de datos
- Tests de rutas
- Tests de WebSockets
- Tests de integración con Azure IoT

---

## Despliegue

### Desarrollo

```bash
python run.py
# Modo debug activado por defecto
```

### Producción

```bash
# Desactivar modo debug en .env
DEBUG=False

# Usar servidor WSGI (Gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"

# O con SocketIO
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 "app:create_app()"
```

---

## Telemetría y Monitoreo

El sistema recopila las siguientes métricas de cada dron:

-  Altura de vuelo
-  Nivel de batería
-  RPM de motores
-  Velocidad y aceleración
-  Temperatura de motores
-  Ubicación GPS en tiempo real

---

##  Seguridad

-  Contraseñas hasheadas con Werkzeug
-  Encriptación de datos sensibles con Fernet
-  Protección CORS configurada
-  Validación de datos en formularios
-  Sesiones seguras con Flask
-  Variables de entorno para secretos

---

##  Licencia

Este proyecto está licenciado bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

##  Contribuciones

Este es un proyecto académico. Para sugerencias o mejoras:

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/mejora`)
3. Commit tus cambios (`git commit -m 'Añade nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/mejora`)
5. Abre un Pull Request

---

##  Contacto

**Cristian Felipe Gómez Manrique**
- Universidad Autónoma de Bucaramanga
- Facultad de Ingeniería de Sistemas
- cgomez710@unab.edu.co

---

##  Referencias

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Azure IoT Central Documentation](https://docs.microsoft.com/azure/iot-central/)
- [Google Maps API Documentation](https://developers.google.com/maps/documentation)

---

##  Agradecimientos

- Universidad Autónoma de Bucaramanga (UNAB)
- Facultad de Ingeniería
- Comunidad de desarrollo open source

---

<p align="center">
  <strong>Desarrollado con ❤️ en Bucaramanga, Colombia 🇨🇴</strong>
</p>

<p align="center">
  <sub>© 2025 SkyKing Project. Todos los derechos reservados.</sub>
</p>
