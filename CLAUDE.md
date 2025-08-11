# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Finance Manager (FP2)** - Sistema completo de gestión de finanzas personales con arquitectura moderna full-stack:
- **Backend**: Django + Django REST Framework con autenticación Supabase
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Base de datos**: PostgreSQL (Supabase)
- **Deploy**: Render.com (plan gratuito)

## Stack Tecnológico

### Backend (`/backend`)
- Django 5.0 + Django REST Framework
- Supabase Auth con JWT
- PostgreSQL + conversión de divisas en tiempo real
- Celery para tareas asíncronas (débitos automáticos)

### Frontend (`/frontend`)
- React 18 + Vite + TypeScript
- Tailwind CSS para styling
- React Query para state management
- Supabase client para autenticación

## Comandos de Desarrollo

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata fixtures/initial_data.json
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Testing
```bash
# Backend
cd backend && python manage.py test
# o con pytest: pytest

# Frontend  
cd frontend && npm test
```

### Datos de prueba
```bash
cd backend
python manage.py seed_demo_data --user-email tu@email.com
```

## Arquitectura del Sistema

### Modelos Principales
- **UserProfile**: Usuarios con roles (user/admin)
- **Account**: Cuentas financieras multi-moneda (banco, tarjeta, efectivo)
- **Transaction**: Transacciones (ingresos, egresos, transferencias)
- **Category**: Categorización de movimientos
- **CardPurchase**: Compras en cuotas automáticas  
- **AutoDebit**: Débitos automáticos programados
- **Budget**: Presupuestos por categoría

### APIs Principales
- `/api/accounts/` - Gestión de cuentas y usuarios
- `/api/transactions/` - Transacciones y operaciones
- `/api/currency/` - Conversión de divisas
- `/api/reports/` - Reportes y dashboards

### Funcionalidades Clave
- 💰 **Multi-moneda**: Conversión automática a ARS en tiempo real
- 💳 **Cuotas**: Generación automática de transacciones de cuotas
- 📈 **Reportes**: Balance, gastos por categoría, análisis de presupuestos
- ⚡ **Automatización**: Débitos automáticos programables
- 🔒 **Seguridad**: JWT, validaciones server-side, auditoría

## Variables de Entorno Requeridas

### Backend (.env)
```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SECRET=your-secret-key

# External APIs
EXCHANGE_API_KEY=your-exchangeratesapi-key

# Database (local)
DB_NAME=finance_manager
DB_USER=postgres
DB_PASSWORD=your-password
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000/api
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## Estructura del Proyecto

```
fp2/
├── backend/              # Django API
│   ├── finance_manager/  # Configuración principal
│   ├── accounts/         # Usuarios, cuentas, categorías
│   ├── transactions/     # Transacciones y operaciones
│   ├── currency/         # Conversión de divisas
│   ├── reports/         # Reportes y dashboards
│   └── tests/           # Tests automatizados
├── frontend/            # React app
│   └── src/
│       ├── components/  # Componentes UI
│       ├── pages/      # Páginas principales
│       ├── services/   # API clients
│       ├── types/      # Types TypeScript
│       └── store/      # Estado global
└── render.yaml         # Configuración de deploy
```

## Flujo de Trabajo

1. **Desarrollo local**: Backend en :8000, Frontend en :3000
2. **Testing**: Pytest para backend, Vitest para frontend
3. **Deploy**: Push a `main` → GitHub Actions → Render.com automático

## Comandos de Gestión

```bash
# Procesar débitos automáticos
python manage.py process_auto_debits

# Actualizar tasas de cambio
python manage.py update_exchange_rates

# Generar datos demo
python manage.py seed_demo_data --user-email demo@test.com
```

## Notas Importantes

- **Moneda base**: Todas las conversiones se hacen a ARS (peso argentino)
- **API externa**: ExchangeRatesAPI para tasas de cambio
- **Deploy gratuito**: Render.com free tier (PostgreSQL + 2 web services)
- **Jobs programados**: GitHub Actions para tareas cron (plan gratuito)
- **Autenticación**: Supabase Auth con perfiles extendidos en Django

## Próximos Desarrollos

- [ ] Componentes UI completos del frontend
- [ ] Páginas de dashboard y gestión
- [ ] Integración completa con APIs
- [ ] Tests E2E con Cypress
- [ ] CI/CD con GitHub Actions