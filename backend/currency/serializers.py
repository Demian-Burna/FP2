"""
Serializers para la app currency
"""
from rest_framework import serializers
from decimal import Decimal
from .models import Currency, ExchangeRate, ConversionLog
from .services import CurrencyService


class CurrencySerializer(serializers.ModelSerializer):
    """Serializer para monedas"""
    
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol', 'decimal_places', 'is_active', 'is_base']


class ExchangeRateSerializer(serializers.ModelSerializer):
    """Serializer para tasas de cambio"""
    
    from_currency_code = serializers.CharField(source='from_currency.code', read_only=True)
    to_currency_code = serializers.CharField(source='to_currency.code', read_only=True)
    from_currency_name = serializers.CharField(source='from_currency.name', read_only=True)
    to_currency_name = serializers.CharField(source='to_currency.name', read_only=True)
    
    class Meta:
        model = ExchangeRate
        fields = [
            'id', 'from_currency', 'from_currency_code', 'from_currency_name',
            'to_currency', 'to_currency_code', 'to_currency_name',
            'rate', 'date', 'source', 'provider', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ConversionRequestSerializer(serializers.Serializer):
    """Serializer para requests de conversión"""
    
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01'))
    from_currency = serializers.CharField(max_length=3)
    to_currency = serializers.CharField(max_length=3)
    context = serializers.CharField(max_length=100, required=False, default='api')
    
    def validate_from_currency(self, value):
        """Validar moneda origen"""
        if not Currency.objects.filter(code=value.upper(), is_active=True).exists():
            raise serializers.ValidationError(f"Moneda '{value}' no soportada")
        return value.upper()
    
    def validate_to_currency(self, value):
        """Validar moneda destino"""
        if not Currency.objects.filter(code=value.upper(), is_active=True).exists():
            raise serializers.ValidationError(f"Moneda '{value}' no soportada")
        return value.upper()


class ConversionResponseSerializer(serializers.Serializer):
    """Serializer para respuestas de conversión"""
    
    original_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    converted_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    from_currency = serializers.CharField(max_length=3)
    to_currency = serializers.CharField(max_length=3)
    exchange_rate = serializers.DecimalField(max_digits=15, decimal_places=6)
    conversion_date = serializers.DateTimeField()
    
    # Información adicional
    from_currency_symbol = serializers.CharField(max_length=10, required=False)
    to_currency_symbol = serializers.CharField(max_length=10, required=False)


class ConversionLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de conversión"""
    
    class Meta:
        model = ConversionLog
        fields = [
            'id', 'from_currency', 'to_currency', 'original_amount',
            'converted_amount', 'exchange_rate', 'source', 'context',
            'created_at'
        ]


class BulkConversionRequestSerializer(serializers.Serializer):
    """Serializer para conversiones múltiples"""
    
    conversions = serializers.ListField(
        child=ConversionRequestSerializer(),
        min_length=1,
        max_length=50
    )
    
    def validate_conversions(self, value):
        """Validar que no hay demasiadas conversiones"""
        if len(value) > 50:
            raise serializers.ValidationError("Máximo 50 conversiones por request")
        return value


class CurrencyRatesUpdateSerializer(serializers.Serializer):
    """Serializer para actualizar tasas manualmente"""
    
    currencies = serializers.ListField(
        child=serializers.CharField(max_length=3),
        required=False,
        help_text="Lista de monedas a actualizar (vacío = todas)"
    )
    force_update = serializers.BooleanField(
        default=False,
        help_text="Forzar actualización aunque ya existan tasas recientes"
    )