# Arquitectura del Sistema de Gestión de Finanzas Personales

## Decisiones Arquitectónicas

### Stack Tecnológico Seleccionado

**Backend: Django + Django REST Framework**
- **Justificación**: Django ofrece un ORM robusto, sistema de migraciones maduro, y excelente manejo de transacciones atómicas (crítico para operaciones financieras). DRF proporciona serialización automática, validación y documentación OpenAPI.
- **Alternativa considerada**: FastAPI sería más performante pero Django ofrece mayor estabilidad y funcionalidades built-in para un sistema financiero.

**Base de Datos: Supabase (PostgreSQL)**
- **Justificación**: PostgreSQL para integridad ACID en transacciones financieras, Supabase Auth para manejo seguro de autenticación JWT.

**Frontend: React + Vite**
- **Justificación**: Vite para desarrollo rápido, React Query para manejo de estado servidor, Recharts para visualizaciones.

## Arquitectura en Capas

```
Frontend (React)
    ├── Components (UI)
    ├── Services (API calls)
    ├── Hooks (Estado y lógica)
    └── Context (Estado global)

Backend (Django)
    ├── Models (Entidades de dominio)
    ├── Serializers (Validación y transformación)
    ├── Views (Controllers)
    ├── Services (Lógica de negocio)
    └── Utils (Utilidades transversales)

Base de Datos (PostgreSQL)
    ├── Tablas relacionales
    ├── Índices para performance
    └── Constraints para integridad
```

## Modelos de Datos Principales

### Usuario y Autenticación
- **Supabase Auth**: Maneja registro, login, JWT tokens
- **Profile**: Extiende usuario de Supabase con datos adicionales

### Núcleo Financiero
- **Account**: Cuentas bancarias, tarjetas, efectivo (multi-moneda)
- **Category**: Categorización de ingresos/egresos (user-scoped)
- **Transaction**: Movimientos financieros con integridad ACID
- **CardPurchase**: Compras en cuotas con generación automática
- **AutoDebit**: Débitos programados con jobs

### Conversión de Divisas
- **CurrencyService**: Caché de tasas, fallback, precisión decimal
- **Provider seleccionado**: ExchangeRatesAPI (gratuito, confiable)

## Patrones de Diseño Aplicados

### SOLID Principles
- **S**: Servicios especializados (CurrencyService, BalanceService)
- **O**: Extensible para nuevos tipos de cuenta/transacción
- **L**: Interfaces para servicios externos (exchange rates)
- **I**: Interfaces segregadas por responsabilidad
- **D**: Inyección de dependencias en servicios

### Repository Pattern
- Abstracción de acceso a datos
- Facilita testing con mocks
- Separación clara entre lógica de negocio y persistencia

## Seguridad y Integridad

### Manejo de Transacciones
```python
@transaction.atomic
def create_transaction_with_balance_update():
    # SELECT ... FOR UPDATE para evitar race conditions
    # Validación de saldos
    # Actualización atómica
```

### Validaciones Críticas
- Montos no pueden ser negativos (excepto transferencias)
- Validación de monedas ISO 4217
- Rate limiting en endpoints sensibles
- Log de auditoría para operaciones críticas

## Performance

### Base de Datos
- Índices en: user_id, account_id, fecha, categoría
- Agregaciones en DB para reportes
- Paginación en endpoints de transacciones

### Cache
- Tasas de cambio (15 minutos TTL)
- Balances calculados (invalidación inteligente)
- Redis para producción (Render Redis)

## Deployment y DevOps

### CI/CD Pipeline
```yaml
Trigger: Push a main
├── Linting (flake8, black, isort)
├── Tests (pytest + coverage)
├── Build (Docker images)
├── Deploy Backend (Render Web Service)
└── Deploy Frontend (Render Static Site)
```

### Monitoreo
- Logs estructurados (JSON)
- Métricas de performance
- Health checks para servicios externos

## Escalabilidad Futura

### Horizontal Scaling
- Servicios stateless
- Base de datos puede sharding por user_id
- Queue para jobs pesados (Celery + Redis)

### Funcionalidades Extensibles
- Plugin system para nuevas categorías
- API externa para importar transacciones bancarias
- Machine learning para categorización automática

## Variables de Entorno Requeridas

```env
# Database
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SECRET=

# External APIs  
EXCHANGE_API_KEY=
EXCHANGE_BASE_URL=

# Django
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=

# Render específicas
DATABASE_URL=
REDIS_URL=
```

## Testing Strategy

### Backend (pytest)
- Unitarios: Servicios de lógica crítica
- Integración: APIs con base de datos real
- Coverage mínimo: 80% en servicios críticos

### Frontend (Cypress)
- E2E: Flujos completos de usuario
- Smoke tests: Funcionalidades críticas
- Visual regression: Componentes clave

## Consideraciones de Producción

### Seguridad
- HTTPS obligatorio
- Validación server-side estricta
- Sanitización de inputs
- Rate limiting por usuario/IP

### Performance
- CDN para assets estáticos
- Compresión Gzip
- Optimización de queries N+1
- Lazy loading en frontend

### Monitoring
- Error tracking (Sentry)
- Performance monitoring
- Business metrics (transacciones/día)