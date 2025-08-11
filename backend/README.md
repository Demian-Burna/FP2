# Finance Manager Backend

Sistema de gestión de finanzas personales desarrollado con Django y Django REST Framework.

## Características

- 🔐 **Autenticación**: Integración con Supabase Auth
- 💳 **Cuentas Múltiples**: Soporte para diferentes tipos de cuenta y monedas
- 📊 **Transacciones**: Gestión completa de ingresos, egresos y transferencias
- 💰 **Cuotas**: Manejo automático de compras en cuotas
- ⚡ **Débitos Automáticos**: Programación de pagos recurrentes
- 💱 **Conversión de Divisas**: Conversión en tiempo real a ARS
- 📈 **Reportes**: Dashboards y reportes detallados
- 🎯 **Presupuestos**: Control y seguimiento de presupuestos

## Stack Tecnológico

- **Framework**: Django 5.0 + Django REST Framework
- **Base de Datos**: PostgreSQL (Supabase)
- **Autenticación**: Supabase Auth + JWT
- **Cache**: Redis (opcional, fallback a memoria)
- **API Externa**: ExchangeRatesAPI para conversión de divisas
- **Deploy**: Render.com

## Instalación y Desarrollo

### Prerequisitos

- Python 3.11+
- PostgreSQL 14+
- Redis (opcional)

### Configuración Local

1. **Clonar el repositorio:**
```bash
git clone <repository-url>
cd backend
```

2. **Crear entorno virtual:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\\Scripts\\activate  # Windows
```

3. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

5. **Ejecutar migraciones:**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Cargar datos iniciales:**
```bash
python manage.py loaddata fixtures/initial_data.json
```

7. **Iniciar servidor de desarrollo:**
```bash
python manage.py runserver
```

La API estará disponible en `http://localhost:8000/`

## Estructura del Proyecto

```
backend/
├── finance_manager/          # Configuración principal
│   ├── settings.py          # Configuración Django
│   ├── urls.py             # URLs principales
│   ├── auth.py             # Autenticación Supabase
│   └── middleware.py       # Middleware personalizado
├── accounts/               # Usuarios, cuentas y categorías
├── transactions/           # Transacciones y operaciones
├── currency/              # Conversión de divisas
├── reports/               # Reportes y dashboards
├── requirements.txt       # Dependencias Python
└── Dockerfile            # Configuración Docker
```

## API Documentation

La documentación completa de la API está disponible en:
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`
- **Schema JSON**: `http://localhost:8000/api/schema/`

## Endpoints Principales

### Autenticación
- `GET /api/auth/profiles/me/` - Perfil del usuario actual

### Cuentas
- `GET/POST /api/accounts/accounts/` - Listar/crear cuentas
- `GET /api/accounts/accounts/summary/` - Resumen de cuentas

### Transacciones
- `GET/POST /api/transactions/transactions/` - Listar/crear transacciones
- `GET /api/transactions/transactions/summary/` - Resumen de transacciones

### Conversión de Divisas
- `POST /api/currency/convert/convert/` - Convertir montos
- `GET /api/currency/convert/to_ars/` - Convertir a ARS

### Reportes
- `GET /api/reports/generate/dashboard/` - Dashboard principal
- `POST /api/reports/generate/generate/` - Generar reportes

## Testing

```bash
# Ejecutar todos los tests
python manage.py test

# Con coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Reporte HTML en htmlcov/
```

## Deployment

### Variables de Entorno para Producción

```env
# Django
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database (Render PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key
SUPABASE_SECRET=your-secret

# External APIs
EXCHANGE_API_KEY=your-exchange-api-key

# Cache (Render Redis)
REDIS_URL=redis://host:port

# Frontend
FRONTEND_URL=https://your-frontend-domain.com
```

### Deploy en Render

1. Crear nuevo Web Service en Render
2. Conectar repositorio GitHub
3. Configurar:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn finance_manager.wsgi:application`
   - **Environment**: Python 3.11
4. Agregar variables de entorno
5. Crear servicio PostgreSQL y Redis
6. Deploy automático

### Comandos Post-Deploy

```bash
# Ejecutar migraciones
python manage.py migrate

# Cargar datos iniciales
python manage.py loaddata fixtures/initial_data.json

# Crear superusuario
python manage.py createsuperuser
```

## Jobs y Tareas Programadas

### Débitos Automáticos

```python
from transactions.services import TransactionService

service = TransactionService()
result = service.execute_pending_debits()
```

### Actualización de Tasas de Cambio

```python
from currency.services import CurrencyService

service = CurrencyService()
result = service.refresh_all_rates()
```

## Monitoreo y Logging

Los logs se escriben en:
- Console (desarrollo)
- Archivo `django.log` (producción)
- Sentry (opcional, configurar SENTRY_DSN)

### Métricas Importantes

- Tiempo de respuesta de endpoints
- Errores de conversión de divisas
- Fallos en débitos automáticos
- Uso de cache de monedas

## Seguridad

- ✅ Validación JWT de Supabase
- ✅ Rate limiting por usuario/IP
- ✅ Validaciones server-side estrictas
- ✅ Logs de auditoría para operaciones críticas
- ✅ HTTPS obligatorio en producción
- ✅ Sanitización de inputs

## Contribución

1. Fork del proyecto
2. Crear branch para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add: AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## Licencia

Este proyecto está bajo la licencia MIT.