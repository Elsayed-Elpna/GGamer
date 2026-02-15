from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from common.services.logging_service import LoggingService
from common.models import AuthenticationLog
import logging

logger = logging.getLogger('security')


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer with additional security checks and logging.
    Validates that user is active and not banned before issuing tokens.
    """

    def validate(self, attrs):
        email = attrs.get('email', '')
        
        try:
            data = super().validate(attrs)
        except AuthenticationFailed as e:
            # Log failed login attempt
            if hasattr(self, 'context') and 'request' in self.context:
                LoggingService.log_authentication(
                    user=None,
                    email=email,
                    action=AuthenticationLog.Action.FAILED_LOGIN,
                    request=self.context['request'],
                    success=False,
                    failure_reason=str(e)
                )
                
                # Check for multiple failed attempts
                ip_address = LoggingService.get_client_ip(self.context['request'])
                is_locked, attempts = LoggingService.check_failed_login_attempts(email, ip_address)
                
                if is_locked:
                    raise AuthenticationFailed(
                        f"Account temporarily locked due to multiple failed login attempts. "
                        f"Please try again later or contact support."
                    )
            raise

        # Check if user is banned
        if self.user.is_banned:
            logger.warning(f"Banned user attempted login: {self.user.email}")
            
            # Log banned user attempt
            if hasattr(self, 'context') and 'request' in self.context:
                LoggingService.log_banned_user_attempt(self.user, self.context['request'])
            
            raise AuthenticationFailed(
                "Your account has been banned. Please contact support."
            )

        # Check if user is active
        if not self.user.is_active:
            logger.warning(f"Inactive user attempted login: {self.user.email}")
            raise AuthenticationFailed(
                "Your account is inactive. Please contact support."
            )

        logger.info(f"Successful login: {self.user.email}")
        return data


@extend_schema(
    tags=['Authentication'],
    summary='Login with email and password',
    description='Authenticate user and obtain JWT access and refresh tokens. '
                'Tokens are set in HTTP-Only cookies for enhanced security. '
                'User must be active and not banned.',
    request=CustomTokenObtainPairSerializer,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string', 'description': 'Success message'},
                'user': {
                    'type': 'object',
                    'properties': {
                        'email': {'type': 'string'},
                        'role': {'type': 'string'},
                        'username': {'type': 'string'},
                    }
                }
            }
        },
        401: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            'Login Request',
            value={
                'email': 'user@example.com',
                'password': 'SecurePass123!'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Login Success',
            value={
                'message': 'Login successful',
                'user': {
                    'email': 'user@example.com',
                    'role': 'BUYER',
                    'username': 'johndoe'
                }
            },
            response_only=True,
            status_codes=['200'],
        ),
        OpenApiExample(
            'Invalid Credentials',
            value={
                'detail': 'No active account found with the given credentials'
            },
            response_only=True,
            status_codes=['401'],
        ),
        OpenApiExample(
            'Banned User',
            value={
                'detail': 'Your account has been banned. Please contact support.'
            },
            response_only=True,
            status_codes=['401'],
        ),
    ],
)
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT login view that sets tokens in HTTP-Only cookies.
    Tokens are NOT returned in response body for security.
    """
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        # Get the standard response with tokens
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Extract tokens from response
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')
            
            # Set HTTP-Only cookies
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,  # Prevents JavaScript access
                secure=True,  # HTTPS only (set to False for development)
                samesite='Lax',  # CSRF protection
                max_age=3600,  # 1 hour
                path='/',
            )
            
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=True,  # HTTPS only (set to False for development)
                samesite='Lax',
                max_age=86400 * 7,  # 7 days
                path='/',
            )
            
            # Get user from serializer (request.user is AnonymousUser at this point)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.user
            
            # Log successful login
            LoggingService.log_authentication(
                user=user,
                email=user.email,
                action=AuthenticationLog.Action.LOGIN,
                request=request,
                success=True
            )
            
            # Replace response data (remove tokens from body)
            response.data = {
                'message': 'Login successful',
                'user': {
                    'email': user.email,
                    'role': user.role,
                    'username': user.public_profile.username if hasattr(user, 'public_profile') else user.email.split('@')[0],
                }
            }
        
        return response