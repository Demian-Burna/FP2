"""
Supabase authentication for Django REST Framework
"""
import jwt
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from accounts.models import UserProfile


class SupabaseUser:
    """
    Representa un usuario autenticado de Supabase
    """
    def __init__(self, user_data):
        self.id = user_data.get('sub')
        self.email = user_data.get('email')
        self.is_authenticated = True
        self.is_anonymous = False
        self.user_metadata = user_data.get('user_metadata', {})
        self.app_metadata = user_data.get('app_metadata', {})
        self.role = self.app_metadata.get('role', 'user')
        
    def __str__(self):
        return self.email or self.id
    
    @property
    def is_admin(self):
        return self.role == 'admin'


class SupabaseAuthentication(BaseAuthentication):
    """
    Autenticación personalizada para tokens JWT de Supabase
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header.split(' ')[1]
        
        try:
            # Decodificar el token JWT de Supabase
            payload = jwt.decode(
                token,
                settings.SUPABASE_SECRET,
                algorithms=['HS256'],
                audience='authenticated'
            )
            
            # Crear usuario de Supabase
            user = SupabaseUser(payload)
            
            # Obtener o crear perfil de usuario
            try:
                profile = UserProfile.objects.get(supabase_user_id=user.id)
                user.profile = profile
            except UserProfile.DoesNotExist:
                # Crear perfil automáticamente en el primer login
                profile = UserProfile.objects.create(
                    supabase_user_id=user.id,
                    email=user.email,
                    role=user.role
                )
                user.profile = profile
            
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expirado')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Token inválido')
        except Exception as e:
            raise AuthenticationFailed(f'Error de autenticación: {str(e)}')
    
    def authenticate_header(self, request):
        return 'Bearer'