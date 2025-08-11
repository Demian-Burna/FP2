"""
Views para la app reports
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import datetime, timedelta
from .models import SavedReport, ReportSchedule, ReportExecution
from .serializers import (
    SavedReportSerializer, ReportScheduleSerializer, ReportExecutionSerializer,
    ReportGenerationRequestSerializer, DashboardDataSerializer,
    ReportComparisonRequestSerializer
)
from .services import ReportService
import logging

logger = logging.getLogger(__name__)


class SavedReportViewSet(viewsets.ModelViewSet):
    """ViewSet para reportes guardados"""
    
    serializer_class = SavedReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'is_public', 'is_favorite']
    
    def get_queryset(self):
        return SavedReport.objects.filter(
            user=self.request.user.profile
        ).order_by('-updated_at')
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generar un reporte guardado"""
        saved_report = self.get_object()
        report_service = ReportService(request.user.profile)
        
        try:
            start_time = timezone.now()
            
            # Generar reporte según el tipo
            if saved_report.report_type == 'balance':
                result_data = report_service.generate_balance_report(
                    target_currency=saved_report.parameters.get('target_currency', 'ARS'),
                    include_inactive=saved_report.parameters.get('include_inactive', False)
                )
            elif saved_report.report_type == 'expenses_by_category':
                result_data = report_service.generate_expenses_by_category_report(
                    date_from=datetime.strptime(saved_report.parameters['date_from'], '%Y-%m-%d').date() if saved_report.parameters.get('date_from') else None,
                    date_to=datetime.strptime(saved_report.parameters['date_to'], '%Y-%m-%d').date() if saved_report.parameters.get('date_to') else None,
                    target_currency=saved_report.parameters.get('target_currency', 'ARS')
                )
            elif saved_report.report_type == 'income_vs_expenses':
                result_data = report_service.generate_income_vs_expenses_report(
                    date_from=datetime.strptime(saved_report.parameters['date_from'], '%Y-%m-%d').date() if saved_report.parameters.get('date_from') else None,
                    date_to=datetime.strptime(saved_report.parameters['date_to'], '%Y-%m-%d').date() if saved_report.parameters.get('date_to') else None,
                    target_currency=saved_report.parameters.get('target_currency', 'ARS')
                )
            elif saved_report.report_type == 'budget_analysis':
                result_data = report_service.generate_budget_analysis_report(
                    target_currency=saved_report.parameters.get('target_currency', 'ARS')
                )
            elif saved_report.report_type == 'installments_projection':
                result_data = report_service.generate_installments_projection_report(
                    months_ahead=saved_report.parameters.get('months_ahead', 12),
                    target_currency=saved_report.parameters.get('target_currency', 'ARS')
                )
            else:
                return Response(
                    {'error': f'Tipo de reporte no soportado: {saved_report.report_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calcular tiempo de ejecución
            execution_time_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            
            # Guardar ejecución
            report_service.save_report_execution(
                saved_report=saved_report,
                result_data=result_data,
                execution_time_ms=execution_time_ms
            )
            
            return Response({
                'report_data': result_data,
                'execution_time_ms': execution_time_ms,
                'generated_at': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error generando reporte {saved_report.name}: {str(e)}")
            
            # Guardar ejecución fallida
            report_service.save_report_execution(
                saved_report=saved_report,
                result_data=None,
                error_message=str(e)
            )
            
            return Response(
                {'error': f'Error generando reporte: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet para programación de reportes"""
    
    serializer_class = ReportScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['frequency', 'delivery_method', 'is_active']
    
    def get_queryset(self):
        return ReportSchedule.objects.filter(
            user=self.request.user.profile
        ).select_related('saved_report').order_by('-created_at')


class ReportExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ejecuciones de reportes (solo lectura)"""
    
    serializer_class = ReportExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'saved_report']
    
    def get_queryset(self):
        return ReportExecution.objects.filter(
            user=self.request.user.profile
        ).select_related('saved_report', 'schedule').order_by('-started_at')


class ReportsViewSet(viewsets.ViewSet):
    """ViewSet principal para generación de reportes"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generar reporte dinámico"""
        serializer = ReportGenerationRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        report_service = ReportService(request.user.profile)
        
        try:
            start_time = timezone.now()
            
            # Generar reporte según el tipo solicitado
            if data['report_type'] == 'balance':
                result_data = report_service.generate_balance_report(
                    target_currency=data['target_currency'],
                    include_inactive=data.get('include_inactive', False)
                )
            
            elif data['report_type'] == 'expenses_by_category':
                result_data = report_service.generate_expenses_by_category_report(
                    date_from=data.get('date_from'),
                    date_to=data.get('date_to'),
                    target_currency=data['target_currency']
                )
            
            elif data['report_type'] == 'income_vs_expenses':
                result_data = report_service.generate_income_vs_expenses_report(
                    date_from=data.get('date_from'),
                    date_to=data.get('date_to'),
                    target_currency=data['target_currency']
                )
            
            elif data['report_type'] == 'budget_analysis':
                result_data = report_service.generate_budget_analysis_report(
                    target_currency=data['target_currency']
                )
            
            elif data['report_type'] == 'installments_projection':
                result_data = report_service.generate_installments_projection_report(
                    months_ahead=data.get('months_ahead', 12),
                    target_currency=data['target_currency']
                )
            
            else:
                return Response(
                    {'error': f'Tipo de reporte no soportado: {data["report_type"]}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            execution_time_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            
            return Response({
                'report_type': data['report_type'],
                'parameters': data,
                'data': result_data,
                'execution_time_ms': execution_time_ms,
                'generated_at': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error generando reporte {data['report_type']}: {str(e)}")
            return Response(
                {'error': f'Error generando reporte: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Datos para el dashboard principal"""
        serializer = DashboardDataSerializer(data=request.query_params)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        report_service = ReportService(request.user.profile)
        
        try:
            # Balance general
            balance_data = report_service.generate_balance_report(
                target_currency=data['currency']
            )
            
            # Gastos del mes actual
            today = timezone.now().date()
            month_start = today.replace(day=1)
            
            expenses_data = report_service.generate_expenses_by_category_report(
                date_from=month_start,
                date_to=today,
                target_currency=data['currency']
            )
            
            # Ingresos vs gastos del mes
            income_expenses_data = report_service.generate_income_vs_expenses_report(
                date_from=month_start,
                date_to=today,
                target_currency=data['currency']
            )
            
            # Análisis de presupuestos
            budget_data = report_service.generate_budget_analysis_report(
                target_currency=data['currency']
            )
            
            dashboard_data = {
                'balance': balance_data,
                'current_month_expenses': expenses_data,
                'current_month_income_vs_expenses': income_expenses_data,
                'budget_analysis': budget_data,
                'period': data['period'],
                'currency': data['currency'],
                'generated_at': timezone.now().isoformat()
            }
            
            # Incluir proyecciones si se solicita
            if data.get('include_projections', True):
                projections = report_service.generate_installments_projection_report(
                    months_ahead=6,
                    target_currency=data['currency']
                )
                dashboard_data['installments_projection'] = projections
            
            return Response(dashboard_data)
            
        except Exception as e:
            logger.error(f"Error generando dashboard: {str(e)}")
            return Response(
                {'error': f'Error generando dashboard: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def compare(self, request):
        """Comparar reportes entre períodos"""
        serializer = ReportComparisonRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        report_service = ReportService(request.user.profile)
        
        try:
            # Generar reporte para período base
            base_from = datetime.strptime(data['base_period']['from'], '%Y-%m-%d').date()
            base_to = datetime.strptime(data['base_period']['to'], '%Y-%m-%d').date()
            
            # Generar reporte para período de comparación
            compare_from = datetime.strptime(data['compare_period']['from'], '%Y-%m-%d').date()
            compare_to = datetime.strptime(data['compare_period']['to'], '%Y-%m-%d').date()
            
            if data['report_type'] == 'expenses_by_category':
                base_report = report_service.generate_expenses_by_category_report(
                    date_from=base_from,
                    date_to=base_to,
                    target_currency=data['target_currency']
                )
                
                compare_report = report_service.generate_expenses_by_category_report(
                    date_from=compare_from,
                    date_to=compare_to,
                    target_currency=data['target_currency']
                )
                
            elif data['report_type'] == 'income_vs_expenses':
                base_report = report_service.generate_income_vs_expenses_report(
                    date_from=base_from,
                    date_to=base_to,
                    target_currency=data['target_currency']
                )
                
                compare_report = report_service.generate_income_vs_expenses_report(
                    date_from=compare_from,
                    date_to=compare_to,
                    target_currency=data['target_currency']
                )
            
            else:
                return Response(
                    {'error': f'Comparación no soportada para tipo: {data["report_type"]}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calcular diferencias y variaciones
            comparison_data = self._calculate_comparison(base_report, compare_report, data['report_type'])
            
            return Response({
                'report_type': data['report_type'],
                'base_period': data['base_period'],
                'compare_period': data['compare_period'],
                'target_currency': data['target_currency'],
                'base_report': base_report,
                'compare_report': compare_report,
                'comparison': comparison_data,
                'generated_at': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error en comparación de reportes: {str(e)}")
            return Response(
                {'error': f'Error en comparación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_comparison(self, base_report, compare_report, report_type):
        """Calcular métricas de comparación entre reportes"""
        if report_type == 'income_vs_expenses':
            base_totals = base_report['totals']
            compare_totals = compare_report['totals']
            
            income_change = compare_totals['income'] - base_totals['income']
            expense_change = compare_totals['expense'] - base_totals['expense']
            net_change = compare_totals['net'] - base_totals['net']
            
            income_pct = (income_change / base_totals['income'] * 100) if base_totals['income'] > 0 else 0
            expense_pct = (expense_change / base_totals['expense'] * 100) if base_totals['expense'] > 0 else 0
            
            return {
                'income_change': {
                    'absolute': income_change,
                    'percentage': income_pct
                },
                'expense_change': {
                    'absolute': expense_change,
                    'percentage': expense_pct
                },
                'net_change': {
                    'absolute': net_change,
                    'percentage': (net_change / base_totals['net'] * 100) if base_totals['net'] != 0 else 0
                }
            }
        
        elif report_type == 'expenses_by_category':
            base_categories = base_report['categories']
            compare_categories = compare_report['categories']
            
            category_changes = {}
            
            all_categories = set(base_categories.keys()) | set(compare_categories.keys())
            
            for category in all_categories:
                base_amount = base_categories.get(category, {}).get('total_amount', 0)
                compare_amount = compare_categories.get(category, {}).get('total_amount', 0)
                
                change = compare_amount - base_amount
                pct_change = (change / base_amount * 100) if base_amount > 0 else (100 if compare_amount > 0 else 0)
                
                category_changes[category] = {
                    'base_amount': base_amount,
                    'compare_amount': compare_amount,
                    'change': change,
                    'percentage_change': pct_change
                }
            
            return {
                'total_change': {
                    'absolute': compare_report['total_expenses'] - base_report['total_expenses'],
                    'percentage': ((compare_report['total_expenses'] - base_report['total_expenses']) / base_report['total_expenses'] * 100) if base_report['total_expenses'] > 0 else 0
                },
                'category_changes': category_changes
            }
        
        return {}