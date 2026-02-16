"""
Authentication views for logout and token refresh with cookies.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from drf_spectacular.utils import extend_schema, OpenApiExample
from common.services.logging_service import LoggingService
from common.models import AuthenticationLog
import logging

logger = logging.getLogger('security')


@extend_schema(
    tags=['Authentication'],
    summary='Logout user',
    description='Logout user by clearing HTTP-Only cookies containing JWT tokens.',
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string', 'description': 'Success message'}
            }
        }
    },
    examples=[
        OpenApiExample(
            'Logout Success',
            value={'message': 'Logout successful'},
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout user by clearing authentication cookies.
    """
    # Log logout
    LoggingService.log_authentication(
        user=request.user,
        email=request.user.email,
        action=AuthenticationLog.Action.LOGOUT,
        request=request,
        success=True
    )
    
    logger.info(f"User logout: {request.user.email}")
    
    response = Response({
        'message': 'Logout successful'
    }, status=status.HTTP_200_OK)
    
    # Delete cookies
    response.delete_cookie('access_token', path='/')
    response.delete_cookie('refresh_token', path='/')
    
    return response


@extend_schema(
    tags=['Authentication'],
    summary='Refresh access token',
    description='Refresh JWT access token using refresh token from cookie. '
                'New access token is set in HTTP-Only cookie.',
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string', 'description': 'Success message'}
            }
        },
        401: {
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'description': 'Error message'}
            }
        }
    },
    examples=[
        OpenApiExample(
            'Refresh Success',
            value={'message': 'Token refreshed successfully'},
            response_only=True,
            status_codes=['200'],
        ),
        OpenApiExample(
            'Invalid Token',
            value={'detail': 'Token is invalid or expired'},
            response_only=True,
            status_codes=['401'],
        ),
    ],
)
@api_view(['POST'])
def refresh_token_view(request):
    """
    Refresh access token using refresh token from cookie.
    """
    refresh_token = request.COOKIES.get('refresh_token')
    
    if not refresh_token:
        return Response({
            'detail': 'Refresh token not found'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        from rest_framework_simplejwt.tokens import RefreshToken
        
        # Validate and refresh token
        token = RefreshToken(refresh_token)
        new_access_token = str(token.access_token)
        
        logger.info(f"Token refreshed for user")
        
        response = Response({
            'message': 'Token refreshed successfully'
        }, status=status.HTTP_200_OK)
        
        # Set new access token in cookie
        response.set_cookie(
            key='access_token',
            value=new_access_token,
            httponly=True,
            secure=True,  # HTTPS only (set to False for development)
            samesite='Lax',
            max_age=3600,  # 1 hour
            path='/',
        )
        
        return response
        
    except (TokenError, InvalidToken) as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        return Response({
            'detail': 'Token is invalid or expired'
        }, status=status.HTTP_401_UNAUTHORIZED)
