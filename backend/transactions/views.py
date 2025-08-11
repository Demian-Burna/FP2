"""
Views para la app transactions
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Transaction, CardPurchase, AutoDebit
from .serializers import TransactionSerializer, CardPurchaseSerializer, AutoDebitSerializer
from .services import TransactionService


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet para transacciones"""
    
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'account', 'category', 'transaction_type', 'currency', 'origin', 'is_confirmed'
    ]
    
    def get_queryset(self):
        # Solo transacciones del usuario actual
        queryset = Transaction.objects.filter(
            user=self.request.user.profile
        ).select_related('account', 'category', 'target_account')
        
        # Filtros de fecha
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # Filtro de búsqueda de texto
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(reference_number__icontains=search) |
                Q(location__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Resumen de transacciones por período"""
        # Parámetros de fecha (último mes por defecto)
        date_to = timezone.now().date()
        date_from = date_to - timedelta(days=30)
        
        date_from_param = request.query_params.get('date_from')
        date_to_param = request.query_params.get('date_to')
        
        if date_from_param:
            date_from = datetime.strptime(date_from_param, '%Y-%m-%d').date()
        if date_to_param:
            date_to = datetime.strptime(date_to_param, '%Y-%m-%d').date()
        
        transactions = self.get_queryset().filter(
            date__date__range=[date_from, date_to],
            is_confirmed=True
        )
        
        # Resumen por tipo
        summary = {
            'period': {
                'from': date_from,
                'to': date_to
            },
            'totals': {
                'income': 0,
                'expense': 0,
                'net': 0,
                'count': 0
            },
            'by_currency': {},
            'by_category': {},
            'by_account': {}
        }
        
        for transaction in transactions:
            currency = transaction.currency
            amount = float(transaction.amount)
            
            # Totales generales (asumiendo ARS como base)
            summary['totals']['count'] += 1
            
            if transaction.transaction_type == 'income':
                summary['totals']['income'] += amount
            elif transaction.transaction_type == 'expense':
                summary['totals']['expense'] += amount
            
            # Por moneda
            if currency not in summary['by_currency']:
                summary['by_currency'][currency] = {'income': 0, 'expense': 0, 'net': 0}
            
            if transaction.transaction_type == 'income':
                summary['by_currency'][currency]['income'] += amount
            elif transaction.transaction_type == 'expense':
                summary['by_currency'][currency]['expense'] += amount
            
            summary['by_currency'][currency]['net'] = (
                summary['by_currency'][currency]['income'] - 
                summary['by_currency'][currency]['expense']
            )
            
            # Por categoría
            category_name = transaction.category.name
            if category_name not in summary['by_category']:
                summary['by_category'][category_name] = {'amount': 0, 'count': 0}
            
            summary['by_category'][category_name]['amount'] += amount
            summary['by_category'][category_name]['count'] += 1
            
            # Por cuenta
            account_name = transaction.account.name
            if account_name not in summary['by_account']:
                summary['by_account'][account_name] = {'income': 0, 'expense': 0}
            
            if transaction.transaction_type == 'income':
                summary['by_account'][account_name]['income'] += amount
            elif transaction.transaction_type == 'expense':
                summary['by_account'][account_name]['expense'] += amount
        
        summary['totals']['net'] = summary['totals']['income'] - summary['totals']['expense']
        
        return Response(summary)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Crear múltiples transacciones"""
        data_list = request.data if isinstance(request.data, list) else [request.data]
        
        serializer = self.get_serializer(data=data_list, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirmar una transacción pendiente"""
        transaction = self.get_object()
        transaction.is_confirmed = True
        transaction.save(update_fields=['is_confirmed'])
        
        serializer = self.get_serializer(transaction)
        return Response(serializer.data)


class CardPurchaseViewSet(viewsets.ModelViewSet):
    """ViewSet para compras en cuotas"""
    
    serializer_class = CardPurchaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['account', 'status', 'currency']
    
    def get_queryset(self):
        return CardPurchase.objects.filter(
            user=self.request.user.profile
        ).select_related('account', 'original_transaction')
    
    @action(detail=False, methods=['get'])
    def active_summary(self, request):
        """Resumen de compras en cuotas activas"""
        active_purchases = self.get_queryset().filter(status='active')
        
        summary = {
            'total_purchases': active_purchases.count(),
            'total_remaining_amount': 0,
            'total_remaining_installments': 0,
            'by_currency': {},
            'next_installments': []
        }
        
        for purchase in active_purchases:
            currency = purchase.currency
            remaining_amount = float(purchase.remaining_amount)
            remaining_installments = purchase.remaining_installments
            
            summary['total_remaining_amount'] += remaining_amount
            summary['total_remaining_installments'] += remaining_installments
            
            # Por moneda
            if currency not in summary['by_currency']:
                summary['by_currency'][currency] = {
                    'remaining_amount': 0,
                    'remaining_installments': 0,
                    'purchases_count': 0
                }
            
            summary['by_currency'][currency]['remaining_amount'] += remaining_amount
            summary['by_currency'][currency]['remaining_installments'] += remaining_installments
            summary['by_currency'][currency]['purchases_count'] += 1
        
        # Próximas cuotas (próximos 30 días)
        from django.utils import timezone
        next_month = timezone.now().date() + timedelta(days=30)
        
        next_installments = Transaction.objects.filter(
            user=request.user.profile,
            origin='installment',
            date__date__lte=next_month,
            is_confirmed=False
        ).select_related('account', 'card_purchase')[:10]
        
        summary['next_installments'] = TransactionSerializer(
            next_installments, many=True, context={'request': request}
        ).data
        
        return Response(summary)
    
    @action(detail=True, methods=['post'])
    def pay_early(self, request, pk=None):
        """Pago anticipado de cuotas restantes"""
        purchase = self.get_object()
        
        if purchase.status != 'active':
            return Response(
                {'error': 'Solo se puede pagar anticipadamente compras activas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Marcar compra como completada
        purchase.status = 'completed'
        purchase.current_installment = purchase.total_installments
        purchase.save()
        
        # Cancelar transacciones pendientes
        Transaction.objects.filter(
            card_purchase=purchase,
            is_confirmed=False
        ).delete()
        
        serializer = self.get_serializer(purchase)
        return Response(serializer.data)


class AutoDebitViewSet(viewsets.ModelViewSet):
    """ViewSet para débitos automáticos"""
    
    serializer_class = AutoDebitSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['account', 'category', 'frequency', 'status']
    
    def get_queryset(self):
        return AutoDebit.objects.filter(
            user=self.request.user.profile
        ).select_related('account', 'category')
    
    @action(detail=False, methods=['get'])
    def pending_executions(self, request):
        """Débitos pendientes de ejecución"""
        today = timezone.now().date()
        
        pending = self.get_queryset().filter(
            status='active',
            next_execution__lte=today
        )
        
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Ejecutar débito automático manualmente"""
        auto_debit = self.get_object()
        
        if not auto_debit.can_execute():
            return Response(
                {'error': 'El débito no puede ejecutarse en este momento'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = TransactionService()
            transaction = service.execute_auto_debit(auto_debit)
            
            transaction_serializer = TransactionSerializer(
                transaction, context={'request': request}
            )
            
            return Response({
                'message': 'Débito ejecutado exitosamente',
                'transaction': transaction_serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error al ejecutar débito: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pausar débito automático"""
        auto_debit = self.get_object()
        auto_debit.status = 'paused'
        auto_debit.save(update_fields=['status'])
        
        serializer = self.get_serializer(auto_debit)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Reanudar débito automático"""
        auto_debit = self.get_object()
        auto_debit.status = 'active'
        auto_debit.save(update_fields=['status'])
        
        serializer = self.get_serializer(auto_debit)
        return Response(serializer.data)