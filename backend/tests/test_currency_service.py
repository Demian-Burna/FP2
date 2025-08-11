"""
Tests para el servicio de conversión de divisas
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, Mock
from currency.services import CurrencyService
from currency.models import Currency, ExchangeRate


@pytest.mark.django_db
class TestCurrencyService:
    """Tests para CurrencyService"""

    def test_convert_same_currency(self):
        """Conversión entre la misma moneda debe retornar el mismo monto"""
        service = CurrencyService()
        
        result = service.convert_amount(
            amount=Decimal('100.00'),
            from_currency='ARS',
            to_currency='ARS'
        )
        
        assert result == Decimal('100.00')

    @pytest.mark.usefixtures('currencies', 'exchange_rates')
    def test_convert_with_existing_rate(self):
        """Conversión usando tasa existente en DB"""
        service = CurrencyService()
        
        result = service.convert_amount(
            amount=Decimal('100.00'),
            from_currency='USD',
            to_currency='ARS'
        )
        
        # 100 USD * 850 = 85,000 ARS
        assert result == Decimal('85000.00')

    @pytest.mark.usefixtures('currencies')
    @patch('currency.services.requests.get')
    def test_convert_with_api_call(self, mock_get):
        """Conversión que requiere llamada a API"""
        # Mock de respuesta de la API
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'rates': {'ARS': 850.0}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        service = CurrencyService()
        
        result = service.convert_amount(
            amount=Decimal('1.00'),
            from_currency='USD',
            to_currency='ARS'
        )
        
        assert result == Decimal('850.00')
        mock_get.assert_called_once()

    def test_convert_invalid_currency(self):
        """Conversión con moneda inválida debe fallar"""
        service = CurrencyService()
        
        with pytest.raises(ValueError):
            service.convert_amount(
                amount=Decimal('100.00'),
                from_currency='INVALID',
                to_currency='ARS'
            )

    @pytest.mark.usefixtures('currencies', 'exchange_rates')
    def test_get_exchange_rate_from_db(self):
        """Obtener tasa de cambio desde la base de datos"""
        service = CurrencyService()
        
        rate = service.get_exchange_rate('USD', 'ARS')
        
        assert rate == Decimal('850.00')

    @pytest.mark.usefixtures('currencies')
    def test_get_exchange_rate_inverse(self):
        """Obtener tasa inversa cuando no existe la directa"""
        from django.utils import timezone
        
        # Crear solo la tasa ARS -> USD
        ExchangeRate.objects.create(
            from_currency_id='ARS',
            to_currency_id='USD',
            rate=Decimal('0.001176'),
            date=timezone.now()
        )
        
        service = CurrencyService()
        
        # Solicitar USD -> ARS (tasa inversa)
        rate = service.get_exchange_rate('USD', 'ARS')
        
        # Debe calcular la inversa: 1 / 0.001176 ≈ 850
        assert abs(rate - Decimal('850.34')) < Decimal('1.00')

    @pytest.mark.usefixtures('currencies')
    @patch('currency.services.requests.get')
    def test_api_failure_fallback(self, mock_get):
        """Test de fallback cuando falla la API"""
        # Mock de fallo en API
        mock_get.side_effect = Exception("API Error")
        
        service = CurrencyService()
        
        rate = service.get_exchange_rate('EUR', 'ARS')
        
        assert rate is None

    def test_decimal_precision(self):
        """Test de precisión decimal en conversiones"""
        service = CurrencyService()
        
        # Conversión que debería tener alta precisión
        result = service.convert_amount(
            amount=Decimal('123.456789'),
            from_currency='ARS',
            to_currency='ARS'  # Misma moneda
        )
        
        assert result == Decimal('123.46')  # Redondeado a 2 decimales

    @pytest.mark.usefixtures('currencies', 'exchange_rates')
    def test_conversion_logging(self):
        """Verificar que se registra el log de conversión"""
        from currency.models import ConversionLog
        
        service = CurrencyService()
        
        # Realizar conversión
        service.convert_amount(
            amount=Decimal('100.00'),
            from_currency='USD',
            to_currency='ARS',
            context='test',
            user_id='test-user'
        )
        
        # Verificar que se creó el log
        log = ConversionLog.objects.filter(
            from_currency='USD',
            to_currency='ARS',
            context='test'
        ).first()
        
        assert log is not None
        assert log.original_amount == Decimal('100.00')
        assert log.converted_amount == Decimal('85000.00')
        assert log.user_id == 'test-user'

    @pytest.mark.usefixtures('currencies', 'exchange_rates')
    def test_cache_functionality(self):
        """Test de funcionalidad de cache"""
        from django.core.cache import cache
        
        service = CurrencyService()
        
        # Primera llamada
        rate1 = service.get_exchange_rate('USD', 'ARS')
        
        # Verificar que se guardó en cache
        cache_key = 'exchange_rate_USD_ARS'
        cached_rate = cache.get(cache_key)
        assert cached_rate == rate1
        
        # Segunda llamada debería usar cache
        rate2 = service.get_exchange_rate('USD', 'ARS')
        assert rate1 == rate2