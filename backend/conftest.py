"""
Configuración global para pytest
"""
import pytest
from django.conf import settings
from django.test import override_settings
from decimal import Decimal
from accounts.models import UserProfile, AccountType, Account, Category
from transactions.models import Transaction
from currency.models import Currency, ExchangeRate


@pytest.fixture
def api_settings():
    """Configuración de API para tests"""
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        EXCHANGE_API_KEY='test-key',
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
        }
    ):
        yield


@pytest.fixture
def test_user():
    """Usuario de prueba"""
    return UserProfile.objects.create(
        supabase_user_id='test-user-123',
        email='test@example.com',
        first_name='Test',
        last_name='User',
        role='user'
    )


@pytest.fixture
def admin_user():
    """Usuario administrador de prueba"""
    return UserProfile.objects.create(
        supabase_user_id='admin-user-123',
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        role='admin'
    )


@pytest.fixture
def account_types():
    """Tipos de cuenta para testing"""
    bank_type = AccountType.objects.create(
        name='Cuenta Bancaria',
        code='bank_account',
        allows_negative_balance=False,
        is_credit_account=False
    )
    
    credit_type = AccountType.objects.create(
        name='Tarjeta de Crédito',
        code='credit_card',
        allows_negative_balance=True,
        is_credit_account=True
    )
    
    return {
        'bank': bank_type,
        'credit': credit_type
    }


@pytest.fixture
def test_account(test_user, account_types):
    """Cuenta de prueba"""
    return Account.objects.create(
        user=test_user,
        account_type=account_types['bank'],
        name='Cuenta Test',
        currency='ARS',
        balance=Decimal('10000.00')
    )


@pytest.fixture
def test_categories(test_user):
    """Categorías de prueba"""
    income_cat = Category.objects.create(
        user=test_user,
        name='Sueldo',
        transaction_type='income',
        color='#4caf50'
    )
    
    expense_cat = Category.objects.create(
        user=test_user,
        name='Alimentación',
        transaction_type='expense',
        color='#f44336'
    )
    
    return {
        'income': income_cat,
        'expense': expense_cat
    }


@pytest.fixture
def currencies():
    """Monedas para testing"""
    ars = Currency.objects.create(
        code='ARS',
        name='Peso Argentino',
        symbol='$',
        is_base=True
    )
    
    usd = Currency.objects.create(
        code='USD',
        name='Dólar',
        symbol='US$'
    )
    
    return {
        'ARS': ars,
        'USD': usd
    }


@pytest.fixture
def exchange_rates(currencies):
    """Tasas de cambio para testing"""
    from django.utils import timezone
    
    ExchangeRate.objects.create(
        from_currency=currencies['USD'],
        to_currency=currencies['ARS'],
        rate=Decimal('850.00'),
        date=timezone.now(),
        source='test'
    )
    
    ExchangeRate.objects.create(
        from_currency=currencies['ARS'],
        to_currency=currencies['USD'],
        rate=Decimal('0.001176'),
        date=timezone.now(),
        source='test'
    )