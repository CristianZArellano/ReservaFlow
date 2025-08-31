"""
Middleware personalizado para ReservaFlow
"""
import logging
import time
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Middleware para manejo global de errores"""
    
    def process_exception(self, request, exception):
        """Manejar excepciones no capturadas"""
        
        # Log the error with request context
        logger.error(
            f"Unhandled exception in {request.method} {request.path}: {exception}",
            exc_info=True,
            extra={
                'request_path': request.path,
                'request_method': request.method,
                'user': getattr(request, 'user', None),
                'remote_addr': self.get_client_ip(request),
            }
        )
        
        # Return appropriate JSON response for API endpoints
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Error interno del servidor',
                'details': 'Por favor contacte al administrador si el problema persiste',
                'timestamp': int(time.time())
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Let Django handle non-API errors normally
        return None
    
    def get_client_ip(self, request):
        """Obtener IP del cliente considerando proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware para logging de requests"""
    
    def process_request(self, request):
        """Log incoming requests"""
        request._start_time = time.time()
        
        # Log API requests
        if request.path.startswith('/api/'):
            logger.info(
                f"API Request: {request.method} {request.path}",
                extra={
                    'request_method': request.method,
                    'request_path': request.path,
                    'user': getattr(request, 'user', None),
                    'remote_addr': self.get_client_ip(request),
                }
            )
    
    def process_response(self, request, response):
        """Log response time and status"""
        if hasattr(request, '_start_time') and request.path.startswith('/api/'):
            duration = time.time() - request._start_time
            
            log_level = logging.INFO
            if response.status_code >= 400:
                log_level = logging.WARNING
            if response.status_code >= 500:
                log_level = logging.ERROR
                
            logger.log(
                log_level,
                f"API Response: {request.method} {request.path} - {response.status_code} ({duration:.3f}s)",
                extra={
                    'request_method': request.method,
                    'request_path': request.path,
                    'response_status': response.status_code,
                    'response_time': duration,
                    'user': getattr(request, 'user', None),
                    'remote_addr': self.get_client_ip(request),
                }
            )
        
        return response
    
    def get_client_ip(self, request):
        """Obtener IP del cliente considerando proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class HealthCheckMiddleware(MiddlewareMixin):
    """Middleware para health checks"""
    
    def process_request(self, request):
        """Handle health check requests"""
        if request.path == '/health/':
            from restaurants.services import get_connection_health
            
            try:
                health = get_connection_health()
                
                # Determine overall health
                if health['redis'] and health['database']:
                    status_code = 200
                    health['status'] = 'healthy'
                elif health['database']:
                    status_code = 200  # Still functional without Redis
                    health['status'] = 'degraded'
                else:
                    status_code = 503
                    health['status'] = 'unhealthy'
                
                return JsonResponse(health, status=status_code)
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return JsonResponse({
                    'status': 'unhealthy',
                    'error': 'Health check failed',
                    'timestamp': time.time()
                }, status=503)
        
        return None