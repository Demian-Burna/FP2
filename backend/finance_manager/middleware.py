"""
Middleware personalizado para el sistema de finanzas
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class SupabaseAuthMiddleware(MiddlewareMixin):
    """
    Middleware para procesar la autenticación de Supabase
    """
    
    def process_request(self, request):
        # Log de requests para auditoría (solo en desarrollo)
        if settings.DEBUG:
            logger.debug(f"Request: {request.method} {request.path}")
        
        return None
    
    def process_exception(self, request, exception):
        # Log de errores para auditoría
        logger.error(f"Error in {request.path}: {str(exception)}")
        return None


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware para auditoría de operaciones críticas
    """
    
    CRITICAL_PATHS = [
        '/api/transactions/',
        '/api/accounts/',
        '/api/currency/',
    ]
    
    def process_request(self, request):
        # Auditar operaciones críticas
        if any(request.path.startswith(path) for path in self.CRITICAL_PATHS):
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                logger.info(
                    f"AUDIT: User {getattr(request.user, 'email', 'Anonymous')} "
                    f"performed {request.method} on {request.path}"
                )
        return None