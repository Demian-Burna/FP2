"""
URLs para la app currency
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, ExchangeRateViewSet, CurrencyConversionViewSet, ConversionLogViewSet

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet, basename='currency')
router.register(r'rates', ExchangeRateViewSet, basename='exchangerate')
router.register(r'convert', CurrencyConversionViewSet, basename='conversion')
router.register(r'logs', ConversionLogViewSet, basename='conversionlog')

urlpatterns = [
    path('', include(router.urls)),
]