"""
URLs para la app transactions
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, CardPurchaseViewSet, AutoDebitViewSet

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'card-purchases', CardPurchaseViewSet, basename='cardpurchase')
router.register(r'auto-debits', AutoDebitViewSet, basename='autodebit')

urlpatterns = [
    path('', include(router.urls)),
]