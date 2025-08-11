"""
Views para la app currency
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Currency, ExchangeRate, ConversionLog
from .serializers import (
    CurrencySerializer, ExchangeRateSerializer, ConversionRequestSerializer,
    ConversionResponseSerializer, ConversionLogSerializer,
    BulkConversionRequestSerializer, CurrencyRatesUpdateSerializer
)
from .services import CurrencyService
import logging

logger = logging.getLogger(__name__)


class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para monedas (solo lectura)"""
    
    queryset = Currency.objects.filter(is_active=True).order_by('code')
    serializer_class = CurrencySerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def supported(self, request):
        """Lista de monedas soportadas con información adicional"""
        currencies = self.get_queryset()
        
        result = {
            'base_currency': None,
            'currencies': [],
            'total_count': currencies.count()
        }
        
        for currency in currencies:
            currency_data = self.get_serializer(currency).data
            
            if currency.is_base:
                result['base_currency'] = currency_data
            
            result['currencies'].append(currency_data)
        
        return Response(result)


class ExchangeRateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para tasas de cambio (solo lectura)"""
    
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['from_currency', 'to_currency', 'source', 'provider']
    
    def get_queryset(self):
        return ExchangeRate.objects.select_related(
            'from_currency', 'to_currency'
        ).order_by('-date')
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Obtener las tasas más recientes"""
        from_currency = request.query_params.get('from_currency')
        to_currency = request.query_params.get('to_currency')
        
        queryset = self.get_queryset()
        
        if from_currency:
            queryset = queryset.filter(from_currency__code=from_currency.upper())
        
        if to_currency:
            queryset = queryset.filter(to_currency__code=to_currency.upper())
        
        # Obtener la más reciente de cada par de monedas
        rates = {}
        for rate in queryset:
            pair_key = f"{rate.from_currency.code}_{rate.to_currency.code}"
            if pair_key not in rates:
                rates[pair_key] = rate
        
        serializer = self.get_serializer(list(rates.values()), many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Historial de tasas para un par de monedas"""
        from_currency = request.query_params.get('from_currency')
        to_currency = request.query_params.get('to_currency')
        days = int(request.query_params.get('days', 30))
        
        if not from_currency or not to_currency:
            return Response(
                {'error': 'Se requieren parámetros from_currency y to_currency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        
        rates = self.get_queryset().filter(
            from_currency__code=from_currency.upper(),
            to_currency__code=to_currency.upper(),
            date__gte=cutoff_date
        )[:100]  # Limitar resultados
        
        serializer = self.get_serializer(rates, many=True)
        return Response({
            'pair': f"{from_currency.upper()}/{to_currency.upper()}",
            'period_days': days,
            'rates': serializer.data
        })


class CurrencyConversionViewSet(viewsets.ViewSet):
    """ViewSet para conversiones de moneda"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.currency_service = CurrencyService()
    
    @action(detail=False, methods=['post'])
    def convert(self, request):
        """Convertir un monto entre monedas"""
        serializer = ConversionRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            converted_amount = self.currency_service.convert_amount(
                amount=data['amount'],
                from_currency=data['from_currency'],
                to_currency=data['to_currency'],
                context=data.get('context', 'api'),
                user_id=request.user.profile.id
            )
            
            # Obtener información adicional de las monedas
            from_curr = Currency.objects.get(code=data['from_currency'])
            to_curr = Currency.objects.get(code=data['to_currency'])
            
            # Calcular tasa usada
            exchange_rate = converted_amount / data['amount'] if data['amount'] > 0 else 0
            
            response_data = {
                'original_amount': data['amount'],
                'converted_amount': converted_amount,
                'from_currency': data['from_currency'],
                'to_currency': data['to_currency'],
                'exchange_rate': exchange_rate,
                'conversion_date': timezone.now(),
                'from_currency_symbol': from_curr.symbol,
                'to_currency_symbol': to_curr.symbol
            }
            
            response_serializer = ConversionResponseSerializer(response_data)
            return Response(response_serializer.data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error en conversión: {str(e)}")
            return Response(
                {'error': 'Error interno al realizar la conversión'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_convert(self, request):
        """Convertir múltiples montos"""
        serializer = BulkConversionRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        conversions = serializer.validated_data['conversions']
        results = []
        errors = []
        
        for i, conversion_data in enumerate(conversions):
            try:
                converted_amount = self.currency_service.convert_amount(
                    amount=conversion_data['amount'],
                    from_currency=conversion_data['from_currency'],
                    to_currency=conversion_data['to_currency'],
                    context=conversion_data.get('context', 'api'),
                    user_id=request.user.profile.id
                )
                
                exchange_rate = converted_amount / conversion_data['amount'] if conversion_data['amount'] > 0 else 0
                
                results.append({
                    'index': i,
                    'original_amount': conversion_data['amount'],
                    'converted_amount': converted_amount,
                    'from_currency': conversion_data['from_currency'],
                    'to_currency': conversion_data['to_currency'],
                    'exchange_rate': exchange_rate,
                    'success': True
                })
                
            except Exception as e:
                errors.append({
                    'index': i,
                    'error': str(e),
                    'success': False
                })
        
        return Response({
            'results': results,
            'errors': errors,
            'total_conversions': len(conversions),
            'successful_conversions': len(results),
            'failed_conversions': len(errors)
        })
    
    @action(detail=False, methods=['get'])
    def to_ars(self, request):
        """Convertir cualquier monto a pesos argentinos (ARS)"""
        amount = request.query_params.get('amount')
        from_currency = request.query_params.get('from_currency', '').upper()
        
        if not amount or not from_currency:
            return Response(
                {'error': 'Se requieren parámetros amount y from_currency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = float(amount)
            converted_amount = self.currency_service.convert_amount(
                amount=amount,
                from_currency=from_currency,
                to_currency='ARS',
                context='to_ars',
                user_id=request.user.profile.id
            )
            
            return Response({
                'original_amount': amount,
                'converted_amount': converted_amount,
                'from_currency': from_currency,
                'to_currency': 'ARS',
                'conversion_date': timezone.now()
            })
            
        except (ValueError, TypeError) as e:
            return Response(
                {'error': f'Monto inválido: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def refresh_rates(self, request):
        """Actualizar tasas de cambio manualmente"""
        if not request.user.profile.is_admin:
            return Response(
                {'error': 'Solo administradores pueden actualizar tasas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CurrencyRatesUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = self.currency_service.refresh_all_rates()
            return Response({
                'message': 'Tasas actualizadas exitosamente',
                'updated_count': result['updated'],
                'errors': result['errors']
            })
            
        except Exception as e:
            logger.error(f"Error actualizando tasas: {str(e)}")
            return Response(
                {'error': 'Error al actualizar las tasas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConversionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para logs de conversión (solo lectura, admin)"""
    
    serializer_class = ConversionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['from_currency', 'to_currency', 'context']
    
    def get_queryset(self):
        # Solo admins pueden ver todos los logs, usuarios ven solo los suyos
        if self.request.user.profile.is_admin:
            return ConversionLog.objects.all().order_by('-created_at')
        else:
            return ConversionLog.objects.filter(
                user_id=str(self.request.user.profile.id)
            ).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas de conversiones"""
        if not request.user.profile.is_admin:
            return Response(
                {'error': 'Solo administradores pueden ver estadísticas'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from datetime import timedelta
        from django.db.models import Count, Sum
        
        # Estadísticas de los últimos 30 días
        cutoff_date = timezone.now() - timedelta(days=30)
        
        logs = ConversionLog.objects.filter(created_at__gte=cutoff_date)
        
        stats = {
            'total_conversions': logs.count(),
            'by_currency_pair': list(
                logs.values('from_currency', 'to_currency')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            ),
            'by_context': list(
                logs.values('context')
                .annotate(count=Count('id'))
                .order_by('-count')
            ),
            'total_volume_ars': logs.filter(to_currency='ARS').aggregate(
                total=Sum('converted_amount')
            )['total'] or 0
        }
        
        return Response(stats)