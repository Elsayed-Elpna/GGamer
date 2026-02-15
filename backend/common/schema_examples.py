"""
Common schema examples and responses for Swagger documentation.
"""
from drf_spectacular.utils import OpenApiExample

# Authentication Examples
LOGIN_REQUEST_EXAMPLE = OpenApiExample(
    'Login Request',
    value={
        'email': 'user@example.com',
        'password': 'SecurePass123!'
    },
    request_only=True,
)

LOGIN_RESPONSE_EXAMPLE = OpenApiExample(
    'Login Success',
    value={
        'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...'
    },
    response_only=True,
    status_codes=['200'],
)

# Registration Examples
REGISTER_REQUEST_EXAMPLE = OpenApiExample(
    'Registration Request',
    value={
        'email': 'newuser@example.com',
        'password': 'SecurePass123!',
        'password_confirm': 'SecurePass123!'
    },
    request_only=True,
)

# Phone Verification Examples
SEND_OTP_REQUEST_EXAMPLE = OpenApiExample(
    'Send OTP Request',
    value={
        'phone_number': '01012345678'
    },
    request_only=True,
)

VERIFY_OTP_REQUEST_EXAMPLE = OpenApiExample(
    'Verify OTP Request',
    value={
        'phone_number': '01012345678',
        'otp': '123456'
    },
    request_only=True,
)

# Error Response Examples
VALIDATION_ERROR_EXAMPLE = OpenApiExample(
    'Validation Error',
    value={
        'email': ['This field is required.'],
        'password': ['Password must be at least 8 characters.']
    },
    response_only=True,
    status_codes=['400'],
)

AUTHENTICATION_ERROR_EXAMPLE = OpenApiExample(
    'Authentication Error',
    value={
        'detail': 'Invalid email or password'
    },
    response_only=True,
    status_codes=['401'],
)

PERMISSION_ERROR_EXAMPLE = OpenApiExample(
    'Permission Denied',
    value={
        'detail': 'You do not have permission to perform this action.'
    },
    response_only=True,
    status_codes=['403'],
)

RATE_LIMIT_ERROR_EXAMPLE = OpenApiExample(
    'Rate Limit Exceeded',
    value={
        'detail': 'Request was throttled. Expected available in 59 seconds.'
    },
    response_only=True,
    status_codes=['429'],
)
