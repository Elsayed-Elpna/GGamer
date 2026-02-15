from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import logging

logger = logging.getLogger('security')


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer with additional security checks.
    Validates that user is active and not banned before issuing tokens.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        # Check if user is banned
        if self.user.is_banned:
            logger.warning(f"Banned user attempted login: {self.user.email}")
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
                'User must be active and not banned.',
    request=CustomTokenObtainPairSerializer,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'access': {'type': 'string', 'description': 'JWT access token'},
                'refresh': {'type': 'string', 'description': 'JWT refresh token'},
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
                'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
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
    Custom JWT login view using enhanced token serializer.
    """
    serializer_class = CustomTokenObtainPairSerializer