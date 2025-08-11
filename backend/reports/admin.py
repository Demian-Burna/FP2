"""
Configuración del admin para la app reports
"""
from django.contrib import admin
from .models import SavedReport, ReportSchedule, ReportExecution


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'report_type', 'is_public', 'is_favorite',
        'last_generated', 'created_at'
    ]
    list_filter = ['report_type', 'is_public', 'is_favorite']
    search_fields = ['name', 'description', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'last_generated']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'frequency', 'delivery_method', 'next_run',
        'last_run', 'is_active'
    ]
    list_filter = ['frequency', 'delivery_method', 'is_active']
    search_fields = ['name', 'user__email']
    readonly_fields = ['last_run', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'saved_report')


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'saved_report', 'user', 'status', 'started_at', 'completed_at',
        'execution_time_ms', 'rows_processed'
    ]
    list_filter = ['status', 'started_at']
    search_fields = ['saved_report__name', 'user__email']
    readonly_fields = ['started_at', 'completed_at']
    date_hierarchy = 'started_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'saved_report')