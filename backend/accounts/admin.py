"""
Configuración del admin para la app accounts
"""
from django.contrib import admin
from .models import UserProfile, AccountType, Account, Category, Budget


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'role', 'currency_preference', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'currency_preference']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['supabase_user_id', 'created_at', 'updated_at']


@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'allows_negative_balance', 'is_credit_account']
    list_filter = ['allows_negative_balance', 'is_credit_account']
    search_fields = ['name', 'code']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'account_type', 'currency', 'balance', 'is_active']
    list_filter = ['account_type', 'currency', 'is_active', 'include_in_total']
    search_fields = ['name', 'user__email', 'bank_name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'account_type')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'transaction_type', 'monthly_budget', 'is_active']
    list_filter = ['transaction_type', 'is_active']
    search_fields = ['name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'user', 'period', 'amount', 'currency', 'start_date', 'end_date']
    list_filter = ['period', 'currency', 'is_active']
    search_fields = ['category__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']