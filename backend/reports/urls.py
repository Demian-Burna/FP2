"""
URLs para la app reports
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SavedReportViewSet, ReportScheduleViewSet, ReportExecutionViewSet, ReportsViewSet

router = DefaultRouter()
router.register(r'saved', SavedReportViewSet, basename='savedreport')
router.register(r'schedules', ReportScheduleViewSet, basename='reportschedule')
router.register(r'executions', ReportExecutionViewSet, basename='reportexecution')
router.register(r'generate', ReportsViewSet, basename='reports')

urlpatterns = [
    path('', include(router.urls)),
]