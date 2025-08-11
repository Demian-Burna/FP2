"""
Serializers para la app transactions
"""
from rest_framework import serializers
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Transaction, CardPurchase, AutoDebit
from accounts.models import Account, Category


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer para transacciones"""
    
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    target_account_name = serializers.CharField(source='target_account.name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    origin_display = serializers.CharField(source='get_origin_display', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'account', 'account_name', 'category', 'category_name',
            'target_account', 'target_account_name', 'date', 'amount', 'currency',
            'transaction_type', 'transaction_type_display', 'description',
            'origin', 'origin_display', 'reference_number', 'location', 'tags',
            'metadata', 'is_confirmed', 'is_recurring',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validaciones cruzadas"""
        request_user = self.context['request'].user.profile
        
        # Validar que la cuenta pertenece al usuario
        if data['account'].user != request_user:
            raise serializers.ValidationError("La cuenta debe pertenecerte")
        
        # Validar que la categoría pertenece al usuario
        if data['category'].user != request_user:
            raise serializers.ValidationError("La categoría debe pertenecerte")
        
        # Validar transferencias
        if data['transaction_type'] == 'transfer':
            if not data.get('target_account'):
                raise serializers.ValidationError("Las transferencias requieren una cuenta destino")
            if data['target_account'].user != request_user:
                raise serializers.ValidationError("La cuenta destino debe pertenecerte")
            if data['target_account'] == data['account']:
                raise serializers.ValidationError("No se puede transferir a la misma cuenta")
        
        # Validar tipo de categoría vs transacción
        if data['transaction_type'] in ['income', 'expense']:
            expected_cat_type = data['transaction_type']
            if data['category'].transaction_type != expected_cat_type:
                raise serializers.ValidationError(
                    f"La categoría debe ser de tipo {expected_cat_type}"
                )
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        # Asignar usuario actual
        validated_data['user'] = self.context['request'].user.profile
        
        # Crear transacción
        transaction_obj = super().create(validated_data)
        
        # Actualizar balance de la cuenta
        self._update_account_balance(transaction_obj, 'add')
        
        # Si es transferencia, crear transacción espejo
        if transaction_obj.transaction_type == 'transfer':
            self._create_transfer_counterpart(transaction_obj)
        
        return transaction_obj
    
    @transaction.atomic
    def update(self, instance, validated_data):
        # Revertir balance anterior
        self._update_account_balance(instance, 'subtract')
        
        # Actualizar transacción
        updated_instance = super().update(instance, validated_data)
        
        # Aplicar nuevo balance
        self._update_account_balance(updated_instance, 'add')
        
        return updated_instance
    
    def _update_account_balance(self, transaction_obj, operation):
        """Actualizar balance de la cuenta"""
        account = transaction_obj.account
        amount = transaction_obj.amount
        
        if operation == 'add':
            if transaction_obj.transaction_type == 'income':
                account.balance += amount
            elif transaction_obj.transaction_type in ['expense', 'transfer']:
                account.balance -= amount
        elif operation == 'subtract':
            if transaction_obj.transaction_type == 'income':
                account.balance -= amount
            elif transaction_obj.transaction_type in ['expense', 'transfer']:
                account.balance += amount
        
        account.save(update_fields=['balance'])
    
    def _create_transfer_counterpart(self, transaction_obj):
        """Crear transacción espejo para transferencias"""
        # Buscar categoría de transferencia para la cuenta destino
        try:
            transfer_category = Category.objects.get(
                user=transaction_obj.user,
                name='Transferencia',
                transaction_type='income'
            )
        except Category.DoesNotExist:
            # Crear categoría si no existe
            transfer_category = Category.objects.create(
                user=transaction_obj.user,
                name='Transferencia',
                transaction_type='income',
                description='Transferencias entre cuentas'
            )
        
        # Crear transacción de ingreso en cuenta destino
        Transaction.objects.create(
            user=transaction_obj.user,
            account=transaction_obj.target_account,
            category=transfer_category,
            date=transaction_obj.date,
            amount=transaction_obj.amount,
            currency=transaction_obj.currency,
            transaction_type='income',
            description=f"Transferencia desde {transaction_obj.account.name}",
            origin='transfer',
            reference_number=transaction_obj.reference_number,
            metadata={'transfer_source': str(transaction_obj.id)}
        )
        
        # Actualizar balance de cuenta destino
        transaction_obj.target_account.balance += transaction_obj.amount
        transaction_obj.target_account.save(update_fields=['balance'])


class CardPurchaseSerializer(serializers.ModelSerializer):
    """Serializer para compras en cuotas"""
    
    account_name = serializers.CharField(source='account.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    remaining_installments = serializers.ReadOnlyField()
    remaining_amount = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = CardPurchase
        fields = [
            'id', 'account', 'account_name', 'total_amount', 'currency',
            'total_installments', 'installment_amount', 'interest_rate',
            'total_with_interest', 'first_installment_date', 'purchase_date',
            'current_installment', 'status', 'status_display', 'description',
            'remaining_installments', 'remaining_amount', 'progress_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'installment_amount', 'total_with_interest', 
            'current_installment', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Validaciones para compras en cuotas"""
        request_user = self.context['request'].user.profile
        
        # Validar que la cuenta pertenece al usuario
        if data['account'].user != request_user:
            raise serializers.ValidationError("La cuenta debe pertenecerte")
        
        # Validar que es cuenta de crédito
        if not data['account'].account_type.is_credit_account:
            raise serializers.ValidationError("Solo se pueden crear cuotas en cuentas de crédito")
        
        # Validar fechas
        if data['first_installment_date'] < data['purchase_date']:
            raise serializers.ValidationError(
                "La primera cuota no puede ser anterior a la fecha de compra"
            )
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Crear compra en cuotas con transacciones automáticas"""
        request_user = self.context['request'].user.profile
        validated_data['user'] = request_user
        
        # Calcular montos con interés
        total_amount = validated_data['total_amount']
        installments = validated_data['total_installments']
        interest_rate = validated_data.get('interest_rate', Decimal('0.00'))
        
        # Calcular total con intereses (interés compuesto mensual)
        if interest_rate > 0:
            monthly_rate = interest_rate / 100
            total_with_interest = total_amount * (1 + monthly_rate) ** installments
        else:
            total_with_interest = total_amount
        
        installment_amount = total_with_interest / installments
        
        validated_data['total_with_interest'] = total_with_interest
        validated_data['installment_amount'] = installment_amount
        
        # Crear transacción original de la compra
        original_transaction = Transaction.objects.create(
            user=request_user,
            account=validated_data['account'],
            category=self._get_or_create_credit_category(request_user),
            date=timezone.make_aware(
                timezone.datetime.combine(
                    validated_data['purchase_date'], 
                    timezone.datetime.min.time()
                )
            ),
            amount=total_amount,
            currency=validated_data['currency'],
            transaction_type='expense',
            description=f"Compra en {installments} cuotas: {validated_data['description']}",
            origin='card',
        )
        
        validated_data['original_transaction'] = original_transaction
        
        # Crear compra en cuotas
        card_purchase = super().create(validated_data)
        
        # Generar transacciones de cuotas
        self._generate_installment_transactions(card_purchase)
        
        return card_purchase
    
    def _get_or_create_credit_category(self, user):
        """Obtener o crear categoría para compras con tarjeta"""
        category, _ = Category.objects.get_or_create(
            user=user,
            name='Compras con Tarjeta',
            transaction_type='expense',
            defaults={
                'description': 'Compras realizadas con tarjeta de crédito',
                'color': '#dc3545'
            }
        )
        return category
    
    def _generate_installment_transactions(self, card_purchase):
        """Generar transacciones programadas para cada cuota"""
        from dateutil.relativedelta import relativedelta
        
        installment_category = self._get_or_create_installment_category(card_purchase.user)
        current_date = card_purchase.first_installment_date
        
        for i in range(card_purchase.total_installments):
            Transaction.objects.create(
                user=card_purchase.user,
                account=card_purchase.account,
                category=installment_category,
                date=timezone.make_aware(
                    timezone.datetime.combine(current_date, timezone.datetime.min.time())
                ),
                amount=card_purchase.installment_amount,
                currency=card_purchase.currency,
                transaction_type='expense',
                description=f"Cuota {i+1}/{card_purchase.total_installments} - {card_purchase.description}",
                origin='installment',
                card_purchase=card_purchase,
                is_confirmed=False  # Las cuotas futuras no están confirmadas
            )
            
            # Siguiente mes
            current_date = current_date + relativedelta(months=1)
    
    def _get_or_create_installment_category(self, user):
        """Obtener o crear categoría para cuotas"""
        category, _ = Category.objects.get_or_create(
            user=user,
            name='Cuotas de Tarjeta',
            transaction_type='expense',
            defaults={
                'description': 'Cuotas de compras con tarjeta de crédito',
                'color': '#ffc107'
            }
        )
        return category


class AutoDebitSerializer(serializers.ModelSerializer):
    """Serializer para débitos automáticos"""
    
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AutoDebit
        fields = [
            'id', 'account', 'account_name', 'category', 'category_name',
            'name', 'description', 'amount', 'currency', 'frequency', 'frequency_display',
            'start_date', 'end_date', 'next_execution', 'last_execution',
            'status', 'status_display', 'execution_count', 'failed_attempts',
            'day_of_month', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'next_execution', 'last_execution', 'execution_count', 
            'failed_attempts', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Validaciones para débitos automáticos"""
        request_user = self.context['request'].user.profile
        
        # Validar que la cuenta pertenece al usuario
        if data['account'].user != request_user:
            raise serializers.ValidationError("La cuenta debe pertenecerte")
        
        # Validar que la categoría pertenece al usuario
        if data['category'].user != request_user:
            raise serializers.ValidationError("La categoría debe pertenecerte")
        
        # Validar categoría de egreso
        if data['category'].transaction_type != 'expense':
            raise serializers.ValidationError("La categoría debe ser de tipo egreso")
        
        # Validar fechas
        if data.get('end_date') and data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("La fecha de fin debe ser posterior al inicio")
        
        return data
    
    def create(self, validated_data):
        """Crear débito automático"""
        validated_data['user'] = self.context['request'].user.profile
        validated_data['next_execution'] = validated_data['start_date']
        
        return super().create(validated_data)