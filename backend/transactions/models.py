"""
Modelos para transacciones y operaciones financieras
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from accounts.models import UserProfile, Account, Category


class Transaction(models.Model):
    """
    Transacciones financieras (ingresos, egresos, transferencias)
    """
    TRANSACTION_TYPES = [
        ('income', 'Ingreso'),
        ('expense', 'Egreso'),
        ('transfer', 'Transferencia'),
    ]
    
    ORIGIN_TYPES = [
        ('manual', 'Manual'),
        ('card', 'Tarjeta'),
        ('auto_debit', 'Débito Automático'),
        ('installment', 'Cuota'),
        ('transfer', 'Transferencia'),
        ('import', 'Importación'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions')
    
    # Datos básicos de la transacción
    date = models.DateTimeField(default=timezone.now, db_index=True)
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, db_index=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.TextField()
    
    # Transferencias
    target_account = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='received_transfers'
    )
    
    # Metadatos
    origin = models.CharField(max_length=20, choices=ORIGIN_TYPES, default='manual')
    reference_number = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Relaciones con otras entidades
    card_purchase = models.ForeignKey(
        'CardPurchase', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='installment_transactions'
    )
    auto_debit = models.ForeignKey(
        'AutoDebit', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='executed_transactions'
    )
    
    # Control
    is_confirmed = models.BooleanField(default=True)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['account', 'date']),
            models.Index(fields=['category', 'date']),
            models.Index(fields=['transaction_type', 'date']),
            models.Index(fields=['currency', 'date']),
        ]
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.description} - {self.amount} {self.currency} ({self.date.strftime('%Y-%m-%d')})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que la cuenta pertenece al usuario
        if self.account.user != self.user:
            raise ValidationError("La cuenta debe pertenecer al usuario")
        
        # Validar que la categoría pertenece al usuario
        if self.category.user != self.user:
            raise ValidationError("La categoría debe pertenecer al usuario")
        
        # Validar tipo de transacción vs tipo de categoría
        if self.transaction_type in ['income', 'expense']:
            expected_cat_type = 'income' if self.transaction_type == 'income' else 'expense'
            if self.category.transaction_type != expected_cat_type:
                raise ValidationError(
                    f"La categoría debe ser de tipo {expected_cat_type} para esta transacción"
                )
        
        # Validar transferencias
        if self.transaction_type == 'transfer':
            if not self.target_account:
                raise ValidationError("Las transferencias requieren una cuenta destino")
            if self.target_account.user != self.user:
                raise ValidationError("La cuenta destino debe pertenecer al usuario")
            if self.target_account == self.account:
                raise ValidationError("No se puede transferir a la misma cuenta")


class CardPurchase(models.Model):
    """
    Compras en cuotas con tarjeta de crédito
    """
    STATUS_CHOICES = [
        ('active', 'Activa'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='card_purchases')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='card_purchases')
    original_transaction = models.OneToOneField(
        Transaction, 
        on_delete=models.CASCADE, 
        related_name='card_purchase_origin'
    )
    
    # Datos de la compra
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    total_installments = models.IntegerField(validators=[MinValueValidator(2), MaxValueValidator(60)])
    installment_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Intereses y comisiones
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Tasa de interés mensual como porcentaje"
    )
    total_with_interest = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Fechas
    first_installment_date = models.DateField()
    purchase_date = models.DateField()
    
    # Control
    current_installment = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    description = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'card_purchases'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['account', 'first_installment_date']),
        ]
    
    def __str__(self):
        return f"{self.description} - {self.total_installments} cuotas de {self.installment_amount} {self.currency}"
    
    @property
    def remaining_installments(self):
        """Cuotas pendientes"""
        return self.total_installments - self.current_installment
    
    @property
    def remaining_amount(self):
        """Monto pendiente"""
        return self.installment_amount * self.remaining_installments
    
    @property
    def progress_percentage(self):
        """Porcentaje de progreso"""
        return (self.current_installment / self.total_installments) * 100


class AutoDebit(models.Model):
    """
    Débitos automáticos programados
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('yearly', 'Anual'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('paused', 'Pausado'),
        ('cancelled', 'Cancelado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='auto_debits')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='auto_debits')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='auto_debits')
    
    # Configuración del débito
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    
    # Fechas
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_execution = models.DateField(db_index=True)
    last_execution = models.DateField(null=True, blank=True)
    
    # Control
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    execution_count = models.IntegerField(default=0)
    failed_attempts = models.IntegerField(default=0)
    
    # Configuración adicional
    day_of_month = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Día del mes para débitos mensuales"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auto_debits'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['next_execution', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.amount} {self.currency} ({self.get_frequency_display()})"
    
    def calculate_next_execution(self):
        """Calcular próxima fecha de ejecución"""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        if not self.last_execution:
            return self.start_date
        
        last = self.last_execution
        
        if self.frequency == 'daily':
            return last + timedelta(days=1)
        elif self.frequency == 'weekly':
            return last + timedelta(weeks=1)
        elif self.frequency == 'biweekly':
            return last + timedelta(weeks=2)
        elif self.frequency == 'monthly':
            next_date = last + relativedelta(months=1)
            if self.day_of_month:
                next_date = next_date.replace(day=min(self.day_of_month, 28))
            return next_date
        elif self.frequency == 'quarterly':
            return last + relativedelta(months=3)
        elif self.frequency == 'yearly':
            return last + relativedelta(years=1)
        
        return last
    
    def can_execute(self):
        """Verificar si se puede ejecutar el débito"""
        from django.utils import timezone
        today = timezone.now().date()
        
        return (
            self.status == 'active' and
            self.next_execution <= today and
            (not self.end_date or today <= self.end_date)
        )