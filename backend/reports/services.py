"""
Servicios para generación de reportes
"""
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
from accounts.models import Account, Category
from transactions.models import Transaction, CardPurchase
from currency.services import CurrencyService
from .models import SavedReport, ReportExecution
import logging

logger = logging.getLogger(__name__)


class ReportService:
    """
    Servicio principal para generación de reportes
    """
    
    def __init__(self, user):
        self.user = user
        self.currency_service = CurrencyService()
        self.base_currency = 'ARS'
    
    def generate_balance_report(self, target_currency='ARS', include_inactive=False):
        """
        Reporte de balance general convertido a una moneda específica
        """
        accounts = self.user.accounts.all()
        if not include_inactive:
            accounts = accounts.filter(is_active=True)
        
        balance_data = {
            'total_balance': Decimal('0'),
            'by_account_type': defaultdict(lambda: {'balance': Decimal('0'), 'accounts': []}),
            'by_currency': defaultdict(lambda: {'balance': Decimal('0'), 'converted_balance': Decimal('0')}),
            'accounts': [],
            'conversion_date': timezone.now(),
            'target_currency': target_currency
        }
        
        for account in accounts:
            # Balance original
            original_balance = account.balance
            
            # Convertir a moneda objetivo
            if account.currency == target_currency:
                converted_balance = original_balance
            else:
                converted_balance = self.currency_service.convert_amount(
                    amount=original_balance,
                    from_currency=account.currency,
                    to_currency=target_currency,
                    context='balance_report',
                    user_id=self.user.id
                )
            
            balance_data['total_balance'] += converted_balance
            
            # Por tipo de cuenta
            account_type = account.account_type.name
            balance_data['by_account_type'][account_type]['balance'] += converted_balance
            balance_data['by_account_type'][account_type]['accounts'].append({
                'id': str(account.id),
                'name': account.name,
                'original_balance': float(original_balance),
                'original_currency': account.currency,
                'converted_balance': float(converted_balance),
                'available_balance': float(account.available_balance)
            })
            
            # Por moneda
            balance_data['by_currency'][account.currency]['balance'] += original_balance
            balance_data['by_currency'][account.currency]['converted_balance'] += converted_balance
            
            # Lista de cuentas
            balance_data['accounts'].append({
                'id': str(account.id),
                'name': account.name,
                'type': account_type,
                'currency': account.currency,
                'balance': float(original_balance),
                'converted_balance': float(converted_balance),
                'is_active': account.is_active
            })
        
        # Convertir defaultdicts a dicts normales para JSON
        balance_data['by_account_type'] = dict(balance_data['by_account_type'])
        balance_data['by_currency'] = dict(balance_data['by_currency'])
        balance_data['total_balance'] = float(balance_data['total_balance'])
        
        return balance_data
    
    def generate_expenses_by_category_report(self, date_from=None, date_to=None, target_currency='ARS'):
        """
        Reporte de gastos por categoría
        """
        if not date_from:
            date_from = timezone.now().date().replace(day=1)  # Primer día del mes actual
        if not date_to:
            date_to = timezone.now().date()
        
        transactions = Transaction.objects.filter(
            user=self.user,
            transaction_type='expense',
            date__date__range=[date_from, date_to],
            is_confirmed=True
        ).select_related('category', 'account')
        
        category_data = defaultdict(lambda: {
            'total_amount': Decimal('0'),
            'transaction_count': 0,
            'transactions': [],
            'percentage': 0
        })
        
        total_expenses = Decimal('0')
        
        for transaction in transactions:
            # Convertir a moneda objetivo
            if transaction.currency == target_currency:
                converted_amount = transaction.amount
            else:
                converted_amount = self.currency_service.convert_amount(
                    amount=transaction.amount,
                    from_currency=transaction.currency,
                    to_currency=target_currency,
                    context='expenses_report',
                    user_id=self.user.id
                )
            
            category_name = transaction.category.name
            category_data[category_name]['total_amount'] += converted_amount
            category_data[category_name]['transaction_count'] += 1
            category_data[category_name]['transactions'].append({
                'id': str(transaction.id),
                'date': transaction.date.isoformat(),
                'description': transaction.description,
                'amount': float(transaction.amount),
                'currency': transaction.currency,
                'converted_amount': float(converted_amount),
                'account': transaction.account.name
            })
            
            total_expenses += converted_amount
        
        # Calcular porcentajes
        for category_name, data in category_data.items():
            if total_expenses > 0:
                data['percentage'] = float((data['total_amount'] / total_expenses) * 100)
            data['total_amount'] = float(data['total_amount'])
        
        return {
            'period': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'target_currency': target_currency,
            'total_expenses': float(total_expenses),
            'categories': dict(category_data),
            'category_count': len(category_data),
            'transaction_count': transactions.count()
        }
    
    def generate_income_vs_expenses_report(self, date_from=None, date_to=None, target_currency='ARS'):
        """
        Reporte comparativo de ingresos vs gastos
        """
        if not date_from:
            date_from = timezone.now().date().replace(day=1)
        if not date_to:
            date_to = timezone.now().date()
        
        transactions = Transaction.objects.filter(
            user=self.user,
            date__date__range=[date_from, date_to],
            transaction_type__in=['income', 'expense'],
            is_confirmed=True
        ).select_related('category', 'account')
        
        income_total = Decimal('0')
        expense_total = Decimal('0')
        monthly_data = defaultdict(lambda: {'income': Decimal('0'), 'expense': Decimal('0')})
        
        for transaction in transactions:
            # Convertir a moneda objetivo
            if transaction.currency == target_currency:
                converted_amount = transaction.amount
            else:
                converted_amount = self.currency_service.convert_amount(
                    amount=transaction.amount,
                    from_currency=transaction.currency,
                    to_currency=target_currency,
                    context='income_expenses_report',
                    user_id=self.user.id
                )
            
            month_key = transaction.date.strftime('%Y-%m')
            
            if transaction.transaction_type == 'income':
                income_total += converted_amount
                monthly_data[month_key]['income'] += converted_amount
            else:
                expense_total += converted_amount
                monthly_data[month_key]['expense'] += converted_amount
        
        # Convertir a formato serializable
        monthly_breakdown = []
        for month, data in sorted(monthly_data.items()):
            monthly_breakdown.append({
                'month': month,
                'income': float(data['income']),
                'expense': float(data['expense']),
                'net': float(data['income'] - data['expense'])
            })
        
        net_income = income_total - expense_total
        savings_rate = float((net_income / income_total * 100)) if income_total > 0 else 0
        
        return {
            'period': {
                'from': date_from.isoformat(),
                'to': date_to.isoformat()
            },
            'target_currency': target_currency,
            'totals': {
                'income': float(income_total),
                'expense': float(expense_total),
                'net': float(net_income),
                'savings_rate': savings_rate
            },
            'monthly_breakdown': monthly_breakdown
        }
    
    def generate_budget_analysis_report(self, target_currency='ARS'):
        """
        Análisis de presupuestos vs gastos reales
        """
        from accounts.models import Budget
        from datetime import date
        
        current_month = date.today().replace(day=1)
        next_month = (current_month.replace(month=current_month.month + 1) 
                     if current_month.month < 12 
                     else current_month.replace(year=current_month.year + 1, month=1))
        
        # Obtener presupuestos activos
        budgets = Budget.objects.filter(
            user=self.user,
            is_active=True,
            start_date__lte=current_month,
            end_date__gte=current_month
        ).select_related('category')
        
        budget_analysis = []
        total_budgeted = Decimal('0')
        total_spent = Decimal('0')
        
        for budget in budgets:
            # Gastos reales en la categoría
            actual_expenses = Transaction.objects.filter(
                user=self.user,
                category=budget.category,
                transaction_type='expense',
                date__date__range=[current_month, next_month - timedelta(days=1)],
                is_confirmed=True
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Convertir presupuesto a moneda objetivo
            if budget.currency == target_currency:
                budget_amount = budget.amount
            else:
                budget_amount = self.currency_service.convert_amount(
                    amount=budget.amount,
                    from_currency=budget.currency,
                    to_currency=target_currency,
                    context='budget_report',
                    user_id=self.user.id
                )
            
            # Convertir gastos reales
            if budget.category.budget_currency == target_currency:
                converted_expenses = actual_expenses
            else:
                converted_expenses = self.currency_service.convert_amount(
                    amount=actual_expenses,
                    from_currency=budget.category.budget_currency,
                    to_currency=target_currency,
                    context='budget_report',
                    user_id=self.user.id
                )
            
            usage_percentage = float((converted_expenses / budget_amount * 100)) if budget_amount > 0 else 0
            remaining = budget_amount - converted_expenses
            
            status = 'ok'
            if usage_percentage >= 100:
                status = 'exceeded'
            elif usage_percentage >= budget.alert_percentage:
                status = 'warning'
            
            budget_analysis.append({
                'category': budget.category.name,
                'budget_amount': float(budget_amount),
                'spent_amount': float(converted_expenses),
                'remaining_amount': float(remaining),
                'usage_percentage': usage_percentage,
                'status': status,
                'alert_percentage': budget.alert_percentage,
                'period': budget.get_period_display()
            })
            
            total_budgeted += budget_amount
            total_spent += converted_expenses
        
        overall_usage = float((total_spent / total_budgeted * 100)) if total_budgeted > 0 else 0
        
        return {
            'period': current_month.isoformat(),
            'target_currency': target_currency,
            'summary': {
                'total_budgeted': float(total_budgeted),
                'total_spent': float(total_spent),
                'total_remaining': float(total_budgeted - total_spent),
                'overall_usage_percentage': overall_usage
            },
            'budgets': budget_analysis,
            'budget_count': len(budget_analysis)
        }
    
    def generate_installments_projection_report(self, months_ahead=12, target_currency='ARS'):
        """
        Proyección de cuotas pendientes
        """
        active_purchases = CardPurchase.objects.filter(
            user=self.user,
            status='active'
        ).select_related('account')
        
        # Obtener transacciones de cuotas pendientes
        pending_installments = Transaction.objects.filter(
            user=self.user,
            origin='installment',
            is_confirmed=False,
            date__date__lte=timezone.now().date() + timedelta(days=months_ahead * 30)
        ).select_related('card_purchase', 'account').order_by('date')
        
        monthly_projections = defaultdict(lambda: {
            'total_amount': Decimal('0'),
            'installments': []
        })
        
        total_pending = Decimal('0')
        
        for installment in pending_installments:
            month_key = installment.date.strftime('%Y-%m')
            
            # Convertir a moneda objetivo
            if installment.currency == target_currency:
                converted_amount = installment.amount
            else:
                converted_amount = self.currency_service.convert_amount(
                    amount=installment.amount,
                    from_currency=installment.currency,
                    to_currency=target_currency,
                    context='installments_report',
                    user_id=self.user.id
                )
            
            monthly_projections[month_key]['total_amount'] += converted_amount
            monthly_projections[month_key]['installments'].append({
                'id': str(installment.id),
                'description': installment.description,
                'amount': float(installment.amount),
                'currency': installment.currency,
                'converted_amount': float(converted_amount),
                'account': installment.account.name,
                'date': installment.date.isoformat(),
                'purchase_id': str(installment.card_purchase.id) if installment.card_purchase else None
            })
            
            total_pending += converted_amount
        
        # Convertir a formato serializable
        projections = []
        for month, data in sorted(monthly_projections.items()):
            projections.append({
                'month': month,
                'total_amount': float(data['total_amount']),
                'installment_count': len(data['installments']),
                'installments': data['installments']
            })
        
        return {
            'target_currency': target_currency,
            'projection_months': months_ahead,
            'summary': {
                'total_pending_amount': float(total_pending),
                'active_purchases': active_purchases.count(),
                'total_installments': pending_installments.count()
            },
            'monthly_projections': projections
        }
    
    def save_report_execution(self, saved_report, result_data, execution_time_ms=None, error_message=None):
        """
        Guardar resultado de ejecución de reporte
        """
        status = 'completed' if not error_message else 'failed'
        
        execution = ReportExecution.objects.create(
            user=self.user,
            saved_report=saved_report,
            status=status,
            completed_at=timezone.now() if status == 'completed' else None,
            result_data=result_data,
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            rows_processed=len(result_data.get('accounts', [])) if result_data else 0
        )
        
        # Actualizar fecha de última generación en el reporte guardado
        saved_report.last_generated = timezone.now()
        saved_report.save(update_fields=['last_generated'])
        
        return execution