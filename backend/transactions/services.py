"""
Servicios de lógica de negocio para transacciones
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Transaction, AutoDebit, CardPurchase
from accounts.models import Category
import logging

logger = logging.getLogger(__name__)


class TransactionService:
    """
    Servicio para operaciones complejas con transacciones
    """
    
    @transaction.atomic
    def execute_auto_debit(self, auto_debit: AutoDebit) -> Transaction:
        """
        Ejecutar un débito automático
        """
        if not auto_debit.can_execute():
            raise ValueError("El débito no puede ejecutarse")
        
        try:
            # Verificar saldo suficiente
            account = auto_debit.account
            if account.balance < auto_debit.amount and not account.account_type.allows_negative_balance:
                auto_debit.failed_attempts += 1
                auto_debit.save(update_fields=['failed_attempts'])
                raise ValueError("Saldo insuficiente para ejecutar el débito")
            
            # Crear transacción
            transaction_obj = Transaction.objects.create(
                user=auto_debit.user,
                account=auto_debit.account,
                category=auto_debit.category,
                date=timezone.now(),
                amount=auto_debit.amount,
                currency=auto_debit.currency,
                transaction_type='expense',
                description=f"Débito automático: {auto_debit.name}",
                origin='auto_debit',
                auto_debit=auto_debit,
                is_confirmed=True
            )
            
            # Actualizar balance de la cuenta
            account.balance -= auto_debit.amount
            account.save(update_fields=['balance'])
            
            # Actualizar información del débito
            auto_debit.last_execution = timezone.now().date()
            auto_debit.execution_count += 1
            auto_debit.failed_attempts = 0
            auto_debit.next_execution = auto_debit.calculate_next_execution()
            auto_debit.save(update_fields=[
                'last_execution', 'execution_count', 
                'failed_attempts', 'next_execution'
            ])
            
            logger.info(f"Débito automático ejecutado: {auto_debit.name} - {auto_debit.amount}")
            
            return transaction_obj
            
        except Exception as e:
            auto_debit.failed_attempts += 1
            auto_debit.save(update_fields=['failed_attempts'])
            logger.error(f"Error ejecutando débito {auto_debit.name}: {str(e)}")
            raise
    
    def execute_pending_debits(self):
        """
        Ejecutar todos los débitos pendientes (para job/cron)
        """
        today = timezone.now().date()
        
        pending_debits = AutoDebit.objects.filter(
            status='active',
            next_execution__lte=today
        )
        
        results = {
            'executed': 0,
            'failed': 0,
            'errors': []
        }
        
        for auto_debit in pending_debits:
            try:
                self.execute_auto_debit(auto_debit)
                results['executed'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'auto_debit': auto_debit.name,
                    'error': str(e)
                })
        
        logger.info(f"Débitos procesados: {results['executed']} exitosos, {results['failed']} fallidos")
        
        return results
    
    @transaction.atomic
    def process_installment_payment(self, card_purchase: CardPurchase, installment_number: int):
        """
        Procesar el pago de una cuota específica
        """
        if card_purchase.status != 'active':
            raise ValueError("La compra no está activa")
        
        if installment_number <= card_purchase.current_installment:
            raise ValueError("Esta cuota ya fue pagada")
        
        if installment_number > card_purchase.total_installments:
            raise ValueError("Número de cuota inválido")
        
        # Buscar la transacción de la cuota
        installment_transaction = Transaction.objects.filter(
            card_purchase=card_purchase,
            origin='installment',
            is_confirmed=False
        ).order_by('date').first()
        
        if not installment_transaction:
            raise ValueError("No hay cuotas pendientes")
        
        # Confirmar la transacción
        installment_transaction.is_confirmed = True
        installment_transaction.save(update_fields=['is_confirmed'])
        
        # Actualizar progreso de la compra
        card_purchase.current_installment = installment_number
        
        # Si es la última cuota, marcar como completada
        if installment_number == card_purchase.total_installments:
            card_purchase.status = 'completed'
        
        card_purchase.save(update_fields=['current_installment', 'status'])
        
        logger.info(f"Cuota procesada: {card_purchase.description} - Cuota {installment_number}")
        
        return installment_transaction
    
    def get_balance_projection(self, account, days_ahead=30):
        """
        Proyección del balance de una cuenta considerando débitos automáticos y cuotas
        """
        from datetime import timedelta
        
        current_balance = account.balance
        projection_date = timezone.now().date() + timedelta(days=days_ahead)
        
        # Débitos automáticos programados
        future_debits = AutoDebit.objects.filter(
            account=account,
            status='active',
            next_execution__lte=projection_date
        )
        
        projected_balance = current_balance
        events = []
        
        for debit in future_debits:
            # Calcular cuántas veces se ejecutará el débito
            current_date = max(debit.next_execution, timezone.now().date())
            execution_count = 0
            
            while current_date <= projection_date:
                projected_balance -= debit.amount
                events.append({
                    'date': current_date,
                    'type': 'auto_debit',
                    'description': debit.name,
                    'amount': -debit.amount,
                    'balance': projected_balance
                })
                
                execution_count += 1
                current_date = debit.calculate_next_execution()
                
                if execution_count > 365:  # Evitar bucles infinitos
                    break
        
        # Cuotas pendientes
        pending_installments = Transaction.objects.filter(
            account=account,
            origin='installment',
            is_confirmed=False,
            date__date__lte=projection_date
        ).order_by('date')
        
        for installment in pending_installments:
            projected_balance -= installment.amount
            events.append({
                'date': installment.date.date(),
                'type': 'installment',
                'description': installment.description,
                'amount': -installment.amount,
                'balance': projected_balance
            })
        
        # Ordenar eventos por fecha
        events.sort(key=lambda x: x['date'])
        
        return {
            'current_balance': float(current_balance),
            'projected_balance': float(projected_balance),
            'projection_date': projection_date,
            'events': events
        }


class BalanceService:
    """
    Servicio para cálculos y consultas de balances
    """
    
    def recalculate_account_balance(self, account):
        """
        Recalcular balance de una cuenta basado en todas sus transacciones
        """
        total_income = Transaction.objects.filter(
            account=account,
            transaction_type='income',
            is_confirmed=True
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        total_expense = Transaction.objects.filter(
            account=account,
            transaction_type='expense',
            is_confirmed=True
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        calculated_balance = total_income - total_expense
        
        if account.balance != calculated_balance:
            logger.warning(f"Balance incorrecto en cuenta {account.name}: {account.balance} vs {calculated_balance}")
            account.balance = calculated_balance
            account.save(update_fields=['balance'])
        
        return calculated_balance
    
    def get_user_total_balance(self, user, currency='ARS'):
        """
        Obtener balance total del usuario en una moneda específica
        """
        from currency.services import CurrencyService
        
        accounts = user.accounts.filter(is_active=True, include_in_total=True)
        currency_service = CurrencyService()
        
        total_balance = Decimal('0')
        
        for account in accounts:
            if account.currency == currency:
                total_balance += account.balance
            else:
                # Convertir a la moneda objetivo
                converted_amount = currency_service.convert_amount(
                    amount=account.balance,
                    from_currency=account.currency,
                    to_currency=currency
                )
                total_balance += converted_amount
        
        return total_balance