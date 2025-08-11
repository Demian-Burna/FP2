"""
Modelos para reportes y dashboards
"""
from django.db import models
from django.utils import timezone
from accounts.models import UserProfile
import uuid


class SavedReport(models.Model):
    """
    Reportes guardados por el usuario
    """
    REPORT_TYPES = [
        ('balance', 'Balance General'),
        ('expenses_by_category', 'Gastos por Categoría'),
        ('income_vs_expenses', 'Ingresos vs Gastos'),
        ('monthly_trend', 'Tendencia Mensual'),
        ('budget_analysis', 'Análisis de Presupuesto'),
        ('account_comparison', 'Comparación de Cuentas'),
        ('installments_projection', 'Proyección de Cuotas'),
        ('custom', 'Personalizado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='saved_reports')
    name = models.CharField(max_length=100)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    
    # Configuración del reporte
    filters = models.JSONField(default=dict, help_text="Filtros aplicados al reporte")
    parameters = models.JSONField(default=dict, help_text="Parámetros específicos del reporte")
    
    # Configuración de visualización
    chart_type = models.CharField(max_length=20, blank=True)
    chart_config = models.JSONField(default=dict)
    
    # Control de acceso
    is_public = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_generated = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'saved_reports'
        indexes = [
            models.Index(fields=['user', 'report_type']),
            models.Index(fields=['is_public', 'report_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'], 
                name='unique_report_name_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()}) - {self.user.email}"


class ReportSchedule(models.Model):
    """
    Programación automática de reportes
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
    ]
    
    DELIVERY_METHODS = [
        ('email', 'Email'),
        ('dashboard', 'Dashboard'),
        ('webhook', 'Webhook'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='report_schedules')
    saved_report = models.ForeignKey(SavedReport, on_delete=models.CASCADE, related_name='schedules')
    
    name = models.CharField(max_length=100)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHODS)
    
    # Configuración de entrega
    email_recipients = models.JSONField(default=list, blank=True)
    webhook_url = models.URLField(blank=True)
    
    # Programación
    next_run = models.DateTimeField()
    last_run = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'report_schedules'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['next_run', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"


class ReportExecution(models.Model):
    """
    Log de ejecuciones de reportes
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'Ejecutando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='report_executions')
    saved_report = models.ForeignKey(SavedReport, on_delete=models.CASCADE, related_name='executions')
    schedule = models.ForeignKey(
        ReportSchedule, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='executions'
    )
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Resultados
    result_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    execution_time_ms = models.IntegerField(null=True, blank=True)
    
    # Metadatos
    parameters_used = models.JSONField(default=dict)
    rows_processed = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'report_executions'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['started_at']),
        ]
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.saved_report.name} - {self.status} ({self.started_at})"