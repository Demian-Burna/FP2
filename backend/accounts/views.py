"""
Views para la app accounts
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import UserProfile, AccountType, Account, Category, Budget
from .serializers import (
    UserProfileSerializer, AccountTypeSerializer, AccountSerializer,
    CategorySerializer, BudgetSerializer
)


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet para perfiles de usuario"""
    
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo el propio perfil del usuario
        return UserProfile.objects.filter(id=self.request.user.profile.id)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener perfil del usuario actual"""
        serializer = self.get_serializer(request.user.profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """Actualizar perfil del usuario actual"""
        serializer = self.get_serializer(
            request.user.profile, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para tipos de cuenta (solo lectura)"""
    
    queryset = AccountType.objects.all()
    serializer_class = AccountTypeSerializer
    permission_classes = [IsAuthenticated]


class AccountViewSet(viewsets.ModelViewSet):
    """ViewSet para cuentas financieras"""
    
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['account_type', 'currency', 'is_active', 'include_in_total']
    
    def get_queryset(self):
        # Solo cuentas del usuario actual
        return Account.objects.filter(
            user=self.request.user.profile
        ).select_related('account_type', 'user')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Resumen de cuentas por tipo y moneda"""
        accounts = self.get_queryset().filter(is_active=True)
        
        summary = {}
        for account in accounts:
            currency = account.currency
            if currency not in summary:
                summary[currency] = {
                    'total_balance': 0,
                    'accounts_count': 0,
                    'by_type': {}
                }
            
            summary[currency]['total_balance'] += float(account.balance)
            summary[currency]['accounts_count'] += 1
            
            account_type = account.account_type.name
            if account_type not in summary[currency]['by_type']:
                summary[currency]['by_type'][account_type] = {
                    'balance': 0,
                    'count': 0
                }
            
            summary[currency]['by_type'][account_type]['balance'] += float(account.balance)
            summary[currency]['by_type'][account_type]['count'] += 1
        
        return Response(summary)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet para categorías"""
    
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['transaction_type', 'is_active']
    
    def get_queryset(self):
        # Solo categorías del usuario actual
        queryset = Category.objects.filter(
            user=self.request.user.profile
        ).select_related('parent_category')
        
        # Filtro por búsqueda de texto
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Obtener categorías en estructura de árbol"""
        categories = self.get_queryset().filter(is_active=True)
        
        # Categorías principales (sin padre)
        main_categories = categories.filter(parent_category=None)
        
        def build_tree(category):
            data = CategorySerializer(category, context={'request': request}).data
            # Agregar subcategorías
            subcategories = categories.filter(parent_category=category)
            if subcategories.exists():
                data['subcategories'] = [build_tree(sub) for sub in subcategories]
            return data
        
        tree = [build_tree(cat) for cat in main_categories]
        return Response(tree)


class BudgetViewSet(viewsets.ModelViewSet):
    """ViewSet para presupuestos"""
    
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['period', 'currency', 'is_active']
    
    def get_queryset(self):
        # Solo presupuestos del usuario actual
        return Budget.objects.filter(
            user=self.request.user.profile
        ).select_related('category')
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtener presupuestos activos para el período actual"""
        from django.utils import timezone
        current_date = timezone.now().date()
        
        budgets = self.get_queryset().filter(
            is_active=True,
            start_date__lte=current_date,
            end_date__gte=current_date
        )
        
        serializer = self.get_serializer(budgets, many=True)
        return Response(serializer.data)