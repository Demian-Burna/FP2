"""
Modelos para gestión de usuarios y cuentas financieras
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class UserProfile(models.Model):
    """
    Perfil de usuario que extiende la información de Supabase
    """
    ROLE_CHOICES = [
        ('user', 'Usuario'),
        ('admin', 'Administrador'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supabase_user_id = models.CharField(max_length=255, unique=True, db_index=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    timezone = models.CharField(max_length=50, default='America/Argentina/Buenos_Aires')
    currency_preference = models.CharField(max_length=3, default='ARS')  # ISO 4217
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_profiles'
        indexes = [
            models.Index(fields=['supabase_user_id']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class AccountType(models.Model):
    """
    Tipos de cuenta (banco, tarjeta, efectivo, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    allows_negative_balance = models.BooleanField(default=False)
    is_credit_account = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_types'
    
    def __str__(self):
        return self.name


class Account(models.Model):
    """
    Cuentas financieras del usuario (banco, tarjeta, efectivo, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='accounts')
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=3, default='ARS')  # ISO 4217
    balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Balance actual en la moneda de la cuenta"
    )
    credit_limit = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Límite de crédito para tarjetas"
    )
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text="Color hex para UI")
    is_active = models.BooleanField(default=True)
    include_in_total = models.BooleanField(default=True, help_text="Incluir en totales generales")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata flexible para extensibilidad
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'accounts'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['currency']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'], 
                name='unique_account_name_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.currency}) - {self.user.email}"
    
    @property
    def available_balance(self):
        """Balance disponible considerando límite de crédito"""
        if self.account_type.is_credit_account and self.credit_limit:
            return self.credit_limit + self.balance  # balance negativo en tarjetas
        return self.balance
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar balance negativo solo para cuentas que lo permiten
        if self.balance < 0 and not self.account_type.allows_negative_balance:
            raise ValidationError(
                f"El tipo de cuenta {self.account_type.name} no permite balance negativo"
            )


class Category(models.Model):
    """
    Categorías para clasificar transacciones (ingresos/egresos)
    """
    TRANSACTION_TYPES = [
        ('income', 'Ingreso'),
        ('expense', 'Egreso'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#28a745')
    icon = models.CharField(max_length=50, blank=True)
    
    # Presupuesto mensual (opcional)
    monthly_budget = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    budget_currency = models.CharField(max_length=3, default='ARS')
    
    parent_category = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='subcategories'
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        indexes = [
            models.Index(fields=['user', 'transaction_type', 'is_active']),
            models.Index(fields=['parent_category']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name', 'transaction_type'], 
                name='unique_category_per_user_type'
            )
        ]
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        parent = f"{self.parent_category.name} > " if self.parent_category else ""
        return f"{parent}{self.name} ({self.get_transaction_type_display()})"


class Budget(models.Model):
    """
    Presupuestos por categoría y período
    """
    PERIOD_CHOICES = [
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('yearly', 'Anual'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='ARS')
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Alertas
    alert_percentage = models.IntegerField(
        default=80, 
        help_text="Porcentaje para alerta de presupuesto"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'budgets'
        indexes = [
            models.Index(fields=['user', 'period', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'category', 'period', 'start_date'], 
                name='unique_budget_per_category_period'
            )
        ]
    
    def __str__(self):
        return f"{self.category.name} - {self.amount} {self.currency} ({self.get_period_display()})"