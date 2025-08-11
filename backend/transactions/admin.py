"""
Configuración del admin para la app transactions
"""
from django.contrib import admin
from .models import Transaction, CardPurchase, AutoDebit


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'description', 'user', 'account', 'category', 'amount', 'currency',
        'transaction_type', 'date', 'is_confirmed'
    ]
    list_filter = [
        'transaction_type', 'currency', 'origin', 'is_confirmed', 'is_recurring'
    ]
    search_fields = ['description', 'reference_number', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'account', 'category', 'target_account'
        )


@admin.register(CardPurchase)
class CardPurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'description', 'user', 'account', 'total_amount', 'currency',
        'total_installments', 'current_installment', 'status'
    ]
    list_filter = ['status', 'currency']
    search_fields = ['description', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'account')


@admin.register(AutoDebit)
class AutoDebitAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'account', 'amount', 'currency', 'frequency',
        'next_execution', 'status', 'execution_count'
    ]
    list_filter = ['frequency', 'status', 'currency']
    search_fields = ['name', 'description', 'user__email']
    readonly_fields = ['execution_count', 'failed_attempts', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'account', 'category')