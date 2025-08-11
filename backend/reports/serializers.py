"""
Serializers para la app reports
"""
from rest_framework import serializers
from .models import SavedReport, ReportSchedule, ReportExecution


class SavedReportSerializer(serializers.ModelSerializer):
    """Serializer para reportes guardados"""
    
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    
    class Meta:
        model = SavedReport
        fields = [
            'id', 'name', 'report_type', 'report_type_display', 'description',
            'filters', 'parameters', 'chart_type', 'chart_config',
            'is_public', 'is_favorite', 'created_at', 'updated_at', 'last_generated'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_generated']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user.profile
        return super().create(validated_data)


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer para programación de reportes"""
    
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    delivery_method_display = serializers.CharField(source='get_delivery_method_display', read_only=True)
    saved_report_name = serializers.CharField(source='saved_report.name', read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'saved_report', 'saved_report_name', 'name', 'frequency', 'frequency_display',
            'delivery_method', 'delivery_method_display', 'email_recipients',
            'webhook_url', 'next_run', 'last_run', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_run', 'created_at', 'updated_at']
    
    def validate_saved_report(self, value):
        """Validar que el reporte pertenece al usuario"""
        if value.user != self.context['request'].user.profile:
            raise serializers.ValidationError("El reporte debe pertenecerte")
        return value
    
    def validate(self, data):
        """Validaciones cruzadas"""
        delivery_method = data.get('delivery_method')
        
        if delivery_method == 'email' and not data.get('email_recipients'):
            raise serializers.ValidationError({
                'email_recipients': 'Se requieren destinatarios para entrega por email'
            })
        
        if delivery_method == 'webhook' and not data.get('webhook_url'):
            raise serializers.ValidationError({
                'webhook_url': 'Se requiere URL para entrega por webhook'
            })
        
        return data
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user.profile
        return super().create(validated_data)


class ReportExecutionSerializer(serializers.ModelSerializer):
    """Serializer para ejecuciones de reportes"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    saved_report_name = serializers.CharField(source='saved_report.name', read_only=True)
    schedule_name = serializers.CharField(source='schedule.name', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportExecution
        fields = [
            'id', 'saved_report', 'saved_report_name', 'schedule', 'schedule_name',
            'status', 'status_display', 'started_at', 'completed_at',
            'duration_seconds', 'result_data', 'error_message',
            'execution_time_ms', 'parameters_used', 'rows_processed'
        ]
        read_only_fields = ['id', 'started_at']
    
    def get_duration_seconds(self, obj):
        """Calcular duración en segundos"""
        if obj.completed_at and obj.started_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class ReportGenerationRequestSerializer(serializers.Serializer):
    """Serializer para requests de generación de reportes"""
    
    REPORT_TYPE_CHOICES = [
        ('balance', 'Balance General'),
        ('expenses_by_category', 'Gastos por Categoría'),
        ('income_vs_expenses', 'Ingresos vs Gastos'),
        ('budget_analysis', 'Análisis de Presupuesto'),
        ('installments_projection', 'Proyección de Cuotas'),
    ]
    
    report_type = serializers.ChoiceField(choices=REPORT_TYPE_CHOICES)
    target_currency = serializers.CharField(max_length=3, default='ARS')
    
    # Filtros opcionales
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    include_inactive = serializers.BooleanField(default=False)
    months_ahead = serializers.IntegerField(default=12, min_value=1, max_value=36)
    
    # Parámetros adicionales
    parameters = serializers.JSONField(required=False, default=dict)
    
    def validate(self, data):
        """Validaciones cruzadas"""
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        if date_from and date_to and date_from >= date_to:
            raise serializers.ValidationError({
                'date_to': 'La fecha fin debe ser posterior a la fecha inicio'
            })
        
        # Validar moneda objetivo
        target_currency = data.get('target_currency', '').upper()
        data['target_currency'] = target_currency
        
        return data


class DashboardDataSerializer(serializers.Serializer):
    """Serializer para datos del dashboard principal"""
    
    period = serializers.CharField(max_length=20, default='current_month')
    currency = serializers.CharField(max_length=3, default='ARS')
    include_projections = serializers.BooleanField(default=True)


class ReportComparisonRequestSerializer(serializers.Serializer):
    """Serializer para comparar reportes entre períodos"""
    
    report_type = serializers.ChoiceField(choices=ReportGenerationRequestSerializer.REPORT_TYPE_CHOICES)
    base_period = serializers.JSONField(help_text="Período base {from: YYYY-MM-DD, to: YYYY-MM-DD}")
    compare_period = serializers.JSONField(help_text="Período a comparar")
    target_currency = serializers.CharField(max_length=3, default='ARS')
    
    def validate_base_period(self, value):
        """Validar período base"""
        if not isinstance(value, dict) or 'from' not in value or 'to' not in value:
            raise serializers.ValidationError("Formato inválido. Usar: {from: YYYY-MM-DD, to: YYYY-MM-DD}")
        return value
    
    def validate_compare_period(self, value):
        """Validar período de comparación"""
        if not isinstance(value, dict) or 'from' not in value or 'to' not in value:
            raise serializers.ValidationError("Formato inválido. Usar: {from: YYYY-MM-DD, to: YYYY-MM-DD}")
        return value