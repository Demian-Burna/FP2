"""
Configuración del admin para la app currency
"""
from django.contrib import admin
from .models import Currency, ExchangeRate, ConversionLog


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'decimal_places', 'is_active', 'is_base']
    list_filter = ['is_active', 'is_base', 'decimal_places']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['from_currency', 'to_currency', 'rate', 'date', 'source', 'provider']
    list_filter = ['source', 'provider', 'date']
    search_fields = ['from_currency__code', 'to_currency__code']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('from_currency', 'to_currency')


@admin.register(ConversionLog)
class ConversionLogAdmin(admin.ModelAdmin):
    list_display = [
        'from_currency', 'to_currency', 'original_amount', 
        'converted_amount', 'exchange_rate', 'context', 'created_at'
    ]
    list_filter = ['from_currency', 'to_currency', 'context', 'source']
    search_fields = ['user_id', 'context']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'