"""
Serializers para la app accounts
"""
from rest_framework import serializers
from decimal import Decimal
from .models import UserProfile, AccountType, Account, Category, Budget


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer para perfil de usuario"""
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'timezone', 'currency_preference', 'role',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'role', 'created_at', 'updated_at']


class AccountTypeSerializer(serializers.ModelSerializer):
    """Serializer para tipos de cuenta"""
    
    class Meta:
        model = AccountType
        fields = '__all__'


class AccountSerializer(serializers.ModelSerializer):
    """Serializer para cuentas financieras"""
    
    account_type_display = serializers.CharField(source='account_type.name', read_only=True)
    available_balance = serializers.ReadOnlyField()
    
    class Meta:
        model = Account
        fields = [
            'id', 'name', 'account_type', 'account_type_display',
            'currency', 'balance', 'available_balance', 'credit_limit',
            'bank_name', 'account_number', 'description', 'color',
            'is_active', 'include_in_total', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']
    
    def validate_currency(self, value):
        """Validar código de moneda ISO 4217"""
        if len(value) != 3:
            raise serializers.ValidationError("La moneda debe ser un código ISO 4217 de 3 letras")
        return value.upper()
    
    def validate_credit_limit(self, value):
        """Validar límite de crédito"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("El límite de crédito debe ser mayor a 0")
        return value
    
    def create(self, validated_data):
        # Asignar usuario actual
        validated_data['user'] = self.context['request'].user.profile
        return super().create(validated_data)


class CategorySerializer(serializers.ModelSerializer):
    """Serializer para categorías"""
    
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    parent_name = serializers.CharField(source='parent_category.name', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'transaction_type', 'transaction_type_display',
            'description', 'color', 'icon', 'monthly_budget', 'budget_currency',
            'parent_category', 'parent_name', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_monthly_budget(self, value):
        """Validar presupuesto mensual"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("El presupuesto mensual debe ser mayor a 0")
        return value
    
    def validate_parent_category(self, value):
        """Validar categoría padre"""
        if value and value.user != self.context['request'].user.profile:
            raise serializers.ValidationError("La categoría padre debe pertencer al mismo usuario")
        return value
    
    def create(self, validated_data):
        # Asignar usuario actual
        validated_data['user'] = self.context['request'].user.profile
        return super().create(validated_data)


class BudgetSerializer(serializers.ModelSerializer):
    """Serializer para presupuestos"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    period_display = serializers.CharField(source='get_period_display', read_only=True)
    
    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'category_name', 'period', 'period_display',
            'amount', 'currency', 'start_date', 'end_date',
            'alert_percentage', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validaciones cruzadas"""
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("La fecha de inicio debe ser anterior a la fecha de fin")
        
        # Validar que la categoría pertenece al usuario
        request_user = self.context['request'].user.profile
        if data['category'].user != request_user:
            raise serializers.ValidationError("La categoría debe pertenecerte")
        
        return data
    
    def create(self, validated_data):
        # Asignar usuario actual
        validated_data['user'] = self.context['request'].user.profile
        return super().create(validated_data)