"""
Comando para generar datos de demostración
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import random

from accounts.models import UserProfile, Account, Category, Budget
from transactions.models import Transaction
from currency.models import ExchangeRate, Currency


class Command(BaseCommand):
    help = 'Generar datos de demostración para el sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            required=True,
            help='Email del usuario para crear datos demo'
        )

    def handle(self, *args, **options):
        user_email = options['user_email']
        
        try:
            # Buscar o crear usuario
            user = UserProfile.objects.get(email=user_email)
            self.stdout.write(f"Creando datos demo para usuario: {user.email}")
            
        except UserProfile.DoesNotExist:
            self.stderr.write(f"Usuario con email {user_email} no encontrado")
            return

        # Limpiar datos existentes del usuario
        self.stdout.write("Limpiando datos existentes...")
        user.transactions.all().delete()
        user.accounts.all().delete()
        user.categories.all().delete()
        user.budgets.all().delete()

        # Crear cuentas
        self.stdout.write("Creando cuentas...")
        self._create_accounts(user)

        # Crear categorías
        self.stdout.write("Creando categorías...")
        self._create_categories(user)

        # Crear presupuestos
        self.stdout.write("Creando presupuestos...")
        self._create_budgets(user)

        # Crear transacciones
        self.stdout.write("Creando transacciones...")
        self._create_transactions(user)

        # Crear tasas de cambio de ejemplo
        self.stdout.write("Creando tasas de cambio...")
        self._create_exchange_rates()

        self.stdout.write(self.style.SUCCESS('Datos de demostración creados exitosamente'))

    def _create_accounts(self, user):
        """Crear cuentas de ejemplo"""
        from accounts.models import AccountType
        
        bank_type = AccountType.objects.get(code='bank_account')
        credit_type = AccountType.objects.get(code='credit_card')
        cash_type = AccountType.objects.get(code='cash')
        digital_type = AccountType.objects.get(code='digital_wallet')

        accounts_data = [
            {
                'name': 'Cuenta Corriente Banco Nación',
                'account_type': bank_type,
                'currency': 'ARS',
                'balance': Decimal('250000.00'),
                'bank_name': 'Banco de la Nación Argentina',
                'account_number': '****1234',
                'color': '#1e88e5'
            },
            {
                'name': 'Caja de Ahorro en Dólares',
                'account_type': bank_type,
                'currency': 'USD',
                'balance': Decimal('1500.00'),
                'bank_name': 'Banco Galicia',
                'account_number': '****5678',
                'color': '#43a047'
            },
            {
                'name': 'Visa Crédito',
                'account_type': credit_type,
                'currency': 'ARS',
                'balance': Decimal('-45000.00'),
                'credit_limit': Decimal('200000.00'),
                'bank_name': 'Banco Santander',
                'account_number': '****9012',
                'color': '#e53935'
            },
            {
                'name': 'Efectivo',
                'account_type': cash_type,
                'currency': 'ARS',
                'balance': Decimal('15000.00'),
                'description': 'Dinero en efectivo',
                'color': '#ff9800'
            },
            {
                'name': 'MercadoPago',
                'account_type': digital_type,
                'currency': 'ARS',
                'balance': Decimal('32500.00'),
                'description': 'Billetera digital MercadoPago',
                'color': '#00bcd4'
            }
        ]

        for account_data in accounts_data:
            Account.objects.create(user=user, **account_data)

    def _create_categories(self, user):
        """Crear categorías de ejemplo"""
        
        # Categorías de egresos
        expense_categories = [
            ('Alimentación', '#f44336', 'Supermercado, restaurantes, delivery'),
            ('Transporte', '#9c27b0', 'Combustible, transporte público, Uber'),
            ('Servicios', '#3f51b5', 'Luz, gas, internet, celular'),
            ('Entretenimiento', '#009688', 'Cine, streaming, salidas'),
            ('Salud', '#4caf50', 'Farmacia, médicos, obra social'),
            ('Educación', '#ff9800', 'Cursos, libros, materiales'),
            ('Compras', '#795548', 'Ropa, electrónicos, hogar'),
            ('Impuestos', '#607d8b', 'AFIP, patentes, municipal'),
            ('Ahorro e Inversión', '#2196f3', 'Plazo fijo, inversiones'),
            ('Otros Gastos', '#9e9e9e', 'Gastos varios')
        ]

        # Categorías de ingresos
        income_categories = [
            ('Sueldo', '#4caf50', 'Salario principal'),
            ('Freelance', '#8bc34a', 'Trabajos independientes'),
            ('Inversiones', '#cddc39', 'Rendimientos de inversiones'),
            ('Ventas', '#ffeb3b', 'Ventas personales'),
            ('Otros Ingresos', '#ffc107', 'Ingresos varios')
        ]

        for name, color, description in expense_categories:
            Category.objects.create(
                user=user,
                name=name,
                transaction_type='expense',
                description=description,
                color=color
            )

        for name, color, description in income_categories:
            Category.objects.create(
                user=user,
                name=name,
                transaction_type='income',
                description=description,
                color=color
            )

    def _create_budgets(self, user):
        """Crear presupuestos de ejemplo"""
        import datetime
        
        current_date = datetime.now().date()
        start_of_month = current_date.replace(day=1)
        
        # Calcular fin de mes
        if current_date.month == 12:
            end_of_month = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)

        budget_data = [
            ('Alimentación', Decimal('80000.00')),
            ('Transporte', Decimal('25000.00')),
            ('Servicios', Decimal('35000.00')),
            ('Entretenimiento', Decimal('20000.00')),
            ('Salud', Decimal('15000.00')),
        ]

        for category_name, budget_amount in budget_data:
            try:
                category = Category.objects.get(user=user, name=category_name, transaction_type='expense')
                Budget.objects.create(
                    user=user,
                    category=category,
                    period='monthly',
                    amount=budget_amount,
                    currency='ARS',
                    start_date=start_of_month,
                    end_date=end_of_month,
                    alert_percentage=80
                )
            except Category.DoesNotExist:
                pass

    def _create_transactions(self, user):
        """Crear transacciones de ejemplo"""
        accounts = list(user.accounts.all())
        categories = list(user.categories.all())
        
        # Generar transacciones de los últimos 3 meses
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        transactions_data = []
        
        # Ingresos mensuales (sueldo)
        sueldo_category = next((cat for cat in categories if cat.name == 'Sueldo'), None)
        cuenta_principal = next((acc for acc in accounts if 'Corriente' in acc.name), accounts[0])
        
        if sueldo_category:
            # Generar 3 sueldos
            for i in range(3):
                salary_date = end_date - timedelta(days=30 * i + 25)
                transactions_data.append({
                    'account': cuenta_principal,
                    'category': sueldo_category,
                    'date': timezone.make_aware(datetime.combine(salary_date, datetime.min.time())),
                    'amount': Decimal('180000.00'),
                    'currency': 'ARS',
                    'transaction_type': 'income',
                    'description': 'Sueldo mensual',
                    'origin': 'manual'
                })

        # Gastos varios
        expense_transactions = [
            # Alimentación
            ('Supermercado Disco', 'Alimentación', Decimal('15000'), 'ARS', -5),
            ('Restaurant La Parolaccia', 'Alimentación', Decimal('8500'), 'ARS', -3),
            ('PedidosYa - Burger King', 'Alimentación', Decimal('2300'), 'ARS', -1),
            
            # Transporte
            ('Carga Nafta YPF', 'Transporte', Decimal('12000'), 'ARS', -7),
            ('SUBE Recarga', 'Transporte', Decimal('3000'), 'ARS', -4),
            
            # Servicios
            ('Edenor - Luz', 'Servicios', Decimal('8500'), 'ARS', -15),
            ('Metrogas - Gas', 'Servicios', Decimal('4200'), 'ARS', -10),
            ('Fibertel Internet', 'Servicios', Decimal('5500'), 'ARS', -8),
            
            # Entretenimiento
            ('Netflix Suscripción', 'Entretenimiento', Decimal('1200'), 'ARS', -2),
            ('Cine Hoyts', 'Entretenimiento', Decimal('3500'), 'ARS', -6),
            
            # Compras
            ('Amazon - Auriculares', 'Compras', Decimal('15000'), 'ARS', -12),
            ('Zara - Ropa', 'Compras', Decimal('25000'), 'ARS', -20),
        ]

        for description, category_name, amount, currency, days_ago in expense_transactions:
            category = next((cat for cat in categories if cat.name == category_name), None)
            if category:
                transaction_date = end_date + timedelta(days=days_ago)
                account = random.choice([acc for acc in accounts if acc.currency == currency])
                
                transactions_data.append({
                    'account': account,
                    'category': category,
                    'date': timezone.make_aware(datetime.combine(transaction_date, datetime.min.time())),
                    'amount': amount,
                    'currency': currency,
                    'transaction_type': 'expense',
                    'description': description,
                    'origin': 'manual'
                })

        # Crear todas las transacciones
        for transaction_data in transactions_data:
            Transaction.objects.create(user=user, **transaction_data)

    def _create_exchange_rates(self):
        """Crear tasas de cambio de ejemplo"""
        currencies = Currency.objects.all()
        base_currency = Currency.objects.get(is_base=True)
        
        # Tasas aproximadas (solo para demo)
        sample_rates = {
            'USD': Decimal('850.00'),
            'EUR': Decimal('920.00'),
            'BRL': Decimal('170.00'),
            'CLP': Decimal('0.95'),
            'UYU': Decimal('22.50')
        }

        current_time = timezone.now()
        
        for currency in currencies:
            if currency.code != base_currency.code and currency.code in sample_rates:
                # Tasa desde ARS a otra moneda
                ExchangeRate.objects.get_or_create(
                    from_currency=base_currency,
                    to_currency=currency,
                    date=current_time,
                    defaults={
                        'rate': Decimal('1') / sample_rates[currency.code],
                        'source': 'manual',
                        'provider': 'demo_data'
                    }
                )
                
                # Tasa desde otra moneda a ARS
                ExchangeRate.objects.get_or_create(
                    from_currency=currency,
                    to_currency=base_currency,
                    date=current_time,
                    defaults={
                        'rate': sample_rates[currency.code],
                        'source': 'manual',
                        'provider': 'demo_data'
                    }
                )