"""
Modelos para conversión de divisas
"""
from django.db import models
from decimal import Decimal
from django.utils import timezone
import uuid


class Currency(models.Model):
    """
    Monedas soportadas por el sistema
    """
    code = models.CharField(max_length=3, primary_key=True, help_text="Código ISO 4217")
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    decimal_places = models.IntegerField(default=2)
    is_active = models.BooleanField(default=True)
    is_base = models.BooleanField(default=False, help_text="Moneda base del sistema (ARS)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'currencies'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @classmethod
    def get_base_currency(cls):
        """Obtener la moneda base del sistema"""
        return cls.objects.get(is_base=True)


class ExchangeRate(models.Model):
    """
    Tasas de cambio entre monedas
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_currency = models.ForeignKey(
        Currency, 
        on_delete=models.CASCADE, 
        related_name='rates_from'
    )
    to_currency = models.ForeignKey(
        Currency, 
        on_delete=models.CASCADE, 
        related_name='rates_to'
    )
    rate = models.DecimalField(
        max_digits=15, 
        decimal_places=6,
        help_text="Tasa de conversión: 1 from_currency = rate to_currency"
    )
    date = models.DateTimeField(default=timezone.now, db_index=True)
    source = models.CharField(
        max_length=50, 
        default='api',
        help_text="Fuente de la tasa (api, manual, etc.)"
    )
    
    # Metadatos del proveedor
    provider = models.CharField(max_length=100, blank=True)
    provider_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'exchange_rates'
        indexes = [
            models.Index(fields=['from_currency', 'to_currency', 'date']),
            models.Index(fields=['date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['from_currency', 'to_currency', 'date'],
                name='unique_rate_per_currency_pair_date'
            )
        ]
        ordering = ['-date']
    
    def __str__(self):
        return f"1 {self.from_currency.code} = {self.rate} {self.to_currency.code} ({self.date.strftime('%Y-%m-%d')})"


class CurrencyCache(models.Model):
    """
    Cache para tasas de cambio optimizado
    """
    cache_key = models.CharField(max_length=100, unique=True, db_index=True)
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=15, decimal_places=6)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'currency_cache'
        indexes = [
            models.Index(fields=['cache_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Cache: {self.from_currency} -> {self.to_currency} = {self.rate}"
    
    @property
    def is_expired(self):
        """Verificar si el cache está expirado"""
        return timezone.now() > self.expires_at
    
    @classmethod
    def get_cache_key(cls, from_currency, to_currency):
        """Generar clave de cache"""
        return f"rate_{from_currency}_{to_currency}"
    
    @classmethod
    def cleanup_expired(cls):
        """Limpiar registros expirados"""
        expired_count = cls.objects.filter(expires_at__lt=timezone.now()).count()
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return expired_count


class ConversionLog(models.Model):
    """
    Log de conversiones realizadas para auditoría
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    original_amount = models.DecimalField(max_digits=15, decimal_places=2)
    converted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6)
    source = models.CharField(max_length=50, help_text="Fuente de la conversión")
    
    # Contexto de la conversión
    user_id = models.CharField(max_length=255, blank=True)
    context = models.CharField(max_length=100, blank=True, help_text="balance, transaction, report, etc.")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'conversion_logs'
        indexes = [
            models.Index(fields=['from_currency', 'to_currency']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_amount} {self.from_currency} -> {self.converted_amount} {self.to_currency}"