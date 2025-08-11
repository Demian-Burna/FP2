"""
Servicios para conversión de divisas
"""
import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
from .models import Currency, ExchangeRate, CurrencyCache, ConversionLog
import logging

logger = logging.getLogger(__name__)


class CurrencyService:
    """
    Servicio principal para conversión de divisas
    """
    
    def __init__(self):
        self.cache_ttl = getattr(settings, 'CURRENCY_CACHE_TTL', 15 * 60)  # 15 minutos
        self.api_key = settings.EXCHANGE_API_KEY
        self.base_url = settings.EXCHANGE_BASE_URL
        self.base_currency = 'ARS'  # Moneda base del sistema
    
    def convert_amount(self, amount, from_currency, to_currency, context='general', user_id=None):
        """
        Convertir un monto entre monedas
        """
        if from_currency == to_currency:
            return amount
        
        # Obtener tasa de cambio
        rate = self.get_exchange_rate(from_currency, to_currency)
        
        if not rate:
            raise ValueError(f"No se pudo obtener la tasa de cambio de {from_currency} a {to_currency}")
        
        # Realizar conversión
        converted_amount = amount * rate
        
        # Redondear según la moneda de destino
        decimal_places = self._get_currency_decimal_places(to_currency)
        converted_amount = converted_amount.quantize(
            Decimal('0.' + '0' * decimal_places), 
            rounding=ROUND_HALF_UP
        )
        
        # Log de auditoría
        self._log_conversion(
            from_currency=from_currency,
            to_currency=to_currency,
            original_amount=amount,
            converted_amount=converted_amount,
            exchange_rate=rate,
            context=context,
            user_id=user_id
        )
        
        return converted_amount
    
    def get_exchange_rate(self, from_currency, to_currency):
        """
        Obtener tasa de cambio entre dos monedas
        """
        if from_currency == to_currency:
            return Decimal('1.00')
        
        # Buscar en cache primero
        cached_rate = self._get_cached_rate(from_currency, to_currency)
        if cached_rate:
            return cached_rate
        
        # Buscar en base de datos (últimas 24 horas)
        db_rate = self._get_db_rate(from_currency, to_currency)
        if db_rate:
            self._cache_rate(from_currency, to_currency, db_rate)
            return db_rate
        
        # Obtener de API externa
        api_rate = self._fetch_rate_from_api(from_currency, to_currency)
        if api_rate:
            self._save_rate_to_db(from_currency, to_currency, api_rate)
            self._cache_rate(from_currency, to_currency, api_rate)
            return api_rate
        
        # Fallback: usar tasa inversa si existe
        inverse_rate = self._get_inverse_rate(from_currency, to_currency)
        if inverse_rate:
            return inverse_rate
        
        logger.error(f"No se pudo obtener tasa de cambio: {from_currency} -> {to_currency}")
        return None
    
    def _get_cached_rate(self, from_currency, to_currency):
        """Obtener tasa desde cache de Django"""
        cache_key = f"exchange_rate_{from_currency}_{to_currency}"
        return cache.get(cache_key)
    
    def _cache_rate(self, from_currency, to_currency, rate):
        """Guardar tasa en cache"""
        cache_key = f"exchange_rate_{from_currency}_{to_currency}"
        cache.set(cache_key, rate, self.cache_ttl)
    
    def _get_db_rate(self, from_currency, to_currency):
        """Obtener tasa desde base de datos (últimas 24 horas)"""
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        try:
            rate_obj = ExchangeRate.objects.filter(
                from_currency_id=from_currency,
                to_currency_id=to_currency,
                date__gte=cutoff_time
            ).first()
            
            return rate_obj.rate if rate_obj else None
            
        except Exception as e:
            logger.error(f"Error obteniendo tasa de DB: {e}")
            return None
    
    def _fetch_rate_from_api(self, from_currency, to_currency):
        """Obtener tasa desde API externa (ExchangeRatesAPI)"""
        try:
            if not self.api_key:
                logger.warning("API key no configurada para exchange rates")
                return None
            
            # Si queremos convertir a ARS (peso argentino), necesitamos la tasa inversa
            # porque muchas APIs usan USD como base
            if to_currency == 'ARS':
                # Obtener USD -> ARS y FROM_CURRENCY -> USD, luego calcular
                usd_to_ars = self._fetch_single_rate('USD', 'ARS')
                from_to_usd = self._fetch_single_rate(from_currency, 'USD')
                
                if usd_to_ars and from_to_usd:
                    return from_to_usd * usd_to_ars
            
            # Para otras conversiones
            return self._fetch_single_rate(from_currency, to_currency)
            
        except Exception as e:
            logger.error(f"Error obteniendo tasa de API: {e}")
            return None
    
    def _fetch_single_rate(self, from_currency, to_currency):
        """Obtener una tasa específica de la API"""
        try:
            url = f"{self.base_url}latest"
            params = {
                'access_key': self.api_key,
                'base': from_currency,
                'symbols': to_currency
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success') and to_currency in data.get('rates', {}):
                return Decimal(str(data['rates'][to_currency]))
            
            logger.warning(f"API no retornó tasa válida: {data}")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error en request a API de exchange rates: {e}")
            return None
    
    def _get_inverse_rate(self, from_currency, to_currency):
        """Obtener tasa inversa si existe"""
        try:
            rate_obj = ExchangeRate.objects.filter(
                from_currency_id=to_currency,
                to_currency_id=from_currency
            ).first()
            
            if rate_obj and rate_obj.rate > 0:
                return Decimal('1') / rate_obj.rate
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo tasa inversa: {e}")
            return None
    
    def _save_rate_to_db(self, from_currency, to_currency, rate):
        """Guardar tasa en base de datos"""
        try:
            from_curr = Currency.objects.get_or_create(code=from_currency)[0]
            to_curr = Currency.objects.get_or_create(code=to_currency)[0]
            
            ExchangeRate.objects.update_or_create(
                from_currency=from_curr,
                to_currency=to_curr,
                date__date=timezone.now().date(),
                defaults={
                    'rate': rate,
                    'source': 'api',
                    'provider': 'exchangeratesapi'
                }
            )
            
        except Exception as e:
            logger.error(f"Error guardando tasa en DB: {e}")
    
    def _get_currency_decimal_places(self, currency_code):
        """Obtener número de decimales para una moneda"""
        try:
            currency = Currency.objects.get(code=currency_code)
            return currency.decimal_places
        except Currency.DoesNotExist:
            return 2  # Default para la mayoría de monedas
    
    def _log_conversion(self, from_currency, to_currency, original_amount, 
                       converted_amount, exchange_rate, context, user_id):
        """Log de conversión para auditoría"""
        try:
            ConversionLog.objects.create(
                from_currency=from_currency,
                to_currency=to_currency,
                original_amount=original_amount,
                converted_amount=converted_amount,
                exchange_rate=exchange_rate,
                source='api',
                user_id=str(user_id) if user_id else '',
                context=context
            )
        except Exception as e:
            logger.error(f"Error logging conversion: {e}")
    
    def get_supported_currencies(self):
        """Obtener lista de monedas soportadas"""
        return Currency.objects.filter(is_active=True).order_by('code')
    
    def refresh_all_rates(self):
        """Actualizar todas las tasas de cambio (para job/cron)"""
        currencies = self.get_supported_currencies()
        base_currency = self.base_currency
        
        updated = 0
        errors = []
        
        for currency in currencies:
            if currency.code == base_currency:
                continue
            
            try:
                # Actualizar tasa hacia ARS
                rate = self._fetch_rate_from_api(currency.code, base_currency)
                if rate:
                    self._save_rate_to_db(currency.code, base_currency, rate)
                    updated += 1
                
                # Actualizar tasa desde ARS
                inverse_rate = self._fetch_rate_from_api(base_currency, currency.code)
                if inverse_rate:
                    self._save_rate_to_db(base_currency, currency.code, inverse_rate)
                    updated += 1
                    
            except Exception as e:
                errors.append(f"{currency.code}: {str(e)}")
        
        logger.info(f"Tasas actualizadas: {updated}, errores: {len(errors)}")
        
        return {
            'updated': updated,
            'errors': errors
        }


class CurrencyConversionMixin:
    """
    Mixin para agregar funcionalidad de conversión a otros servicios
    """
    
    def __init__(self):
        self.currency_service = CurrencyService()
    
    def convert_to_ars(self, amount, from_currency, context='general', user_id=None):
        """Convertir cualquier monto a pesos argentinos"""
        return self.currency_service.convert_amount(
            amount=amount,
            from_currency=from_currency,
            to_currency='ARS',
            context=context,
            user_id=user_id
        )
    
    def convert_from_ars(self, amount, to_currency, context='general', user_id=None):
        """Convertir desde pesos argentinos a otra moneda"""
        return self.currency_service.convert_amount(
            amount=amount,
            from_currency='ARS',
            to_currency=to_currency,
            context=context,
            user_id=user_id
        )