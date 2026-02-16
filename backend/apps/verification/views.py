"""
Verification API views with comprehensive Swagger documentation.
Production-ready with detailed examples and security.
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from common.throttling import OTPThrottle, OTPVerifyThrottle, VerificationThrottle
from apps.verification.serializers import (
    PhoneVerificationSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    SellerVerificationSerializer,
    SellerVerificationAdminSerializer,
    ApproveVerificationSerializer,
    RejectVerificationSerializer
)
from apps.verification.models import PhoneVerification, SellerVerification
from apps.verification.permissions import IsAdminOrSupport
from apps.verification.utils import get_client_ip
from common.services.logging_service import LoggingService
from common.services.email_service import email_service
from common.models import AdminActionLog


# ==================== Phone Verification Endpoints ====================

@extend_schema(
    tags=['Phone Verification'],
    summary='Send OTP to phone number',
    description='''
    Sends a 6-digit OTP code to the provided international phone number for verification.
    
    **Security Notes:**
    - Requires authentication
    - Rate limited to 5 OTP requests per hour per user
    - OTP expires in 5 minutes
    - Phone number must be in international format with country code
    
    **Business Rules:**
    - Phone number cannot be verified by another user
    - User can request new OTP if previous one expired
    ''',
    request=SendOTPSerializer,
    examples=[
        OpenApiExample(
            'International Phone (US)',
            value={'phone_number': '+1234567890'},
            request_only=True
        ),
        OpenApiExample(
            'International Phone (UK)',
            value={'phone_number': '+447700900123'},
            request_only=True
        ),
        OpenApiExample(
            'International Phone (Egypt)',
            value={'phone_number': '+201012345678'},
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            description='OTP sent successfully',
            examples=[
                OpenApiExample(
                    'Success Response',
                    value={
                        'message': 'OTP sent successfully',
                        'expires_in': 300
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description='Invalid request',
            examples=[
                OpenApiExample(
                    'Invalid Phone Format',
                    value={
                        'phone_number': ['Phone number must be in international format with country code (e.g., +1234567890, +447700900123)']
                    }
                ),
                OpenApiExample(
                    'Phone Already Verified',
                    value={
                        'phone_number': ['This phone number is already verified with another account']
                    }
                ),
                OpenApiExample(
                    'Missing Field',
                    value={
                        'phone_number': ['This field is required.']
                    }
                )
            ]
        ),
        401: OpenApiResponse(
            description='Authentication required',
            examples=[
                OpenApiExample(
                    'Not Authenticated',
                    value={'detail': 'Authentication credentials were not provided.'}
                )
            ]
        ),
        429: OpenApiResponse(
            description='Rate limit exceeded',
            examples=[
                OpenApiExample(
                    'Too Many Requests',
                    value={'detail': 'Request was throttled. Expected available in 60 seconds.'}
                )
            ]
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([OTPThrottle])  # SECURITY: Limit to 5 OTP per hour
def send_otp(request):
    """Send OTP to phone number for verification."""
    serializer = SendOTPSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'OTP sent successfully',
            'expires_in': 300
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Phone Verification'],
    summary='Verify OTP code',
    description='''
    Verifies the OTP code sent to the phone number.
    
    **Security Notes:**
    - Requires authentication
    - OTP must match the one sent to the phone number
    - OTP expires in 5 minutes
    - Limited attempts to prevent brute force
    
    **Business Rules:**
    - OTP must be exactly 6 digits
    - Phone number must match the one OTP was sent to
    - After successful verification, phone is marked as verified
    ''',
    request=VerifyOTPSerializer,
    examples=[
        OpenApiExample(
            'Valid OTP',
            value={
                'phone_number': '+201012345678',
                'otp': '123456'
            },
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            description='Phone verified successfully',
            examples=[
                OpenApiExample(
                    'Success Response',
                    value={
                        'message': 'Phone verified successfully',
                        'verified': True
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description='Invalid request',
            examples=[
                OpenApiExample(
                    'Invalid OTP',
                    value={
                        'non_field_errors': ['Invalid or expired OTP code']
                    }
                ),
                OpenApiExample(
                    'Invalid OTP Length',
                    value={
                        'otp': ['Ensure this field has at least 6 characters.']
                    }
                ),
                OpenApiExample(
                    'Missing Fields',
                    value={
                        'phone_number': ['This field is required.'],
                        'otp': ['This field is required.']
                    }
                )
            ]
        ),
        401: OpenApiResponse(
            description='Authentication required'
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([OTPVerifyThrottle])  # SECURITY: Limit to 3 attempts per hour
def verify_otp(request):
    """Verify OTP code for phone verification."""
    serializer = VerifyOTPSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Phone verified successfully',
            'verified': True
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Phone Verification'],
    summary='Get phone verification status',
    description='''
    Retrieves the current phone verification status for the authenticated user.
    
    **Returns:**
    - is_verified: Boolean indicating if phone is verified
    - phone_number: Masked phone number (e.g., +2010****78)
    - verified_at: Timestamp when phone was verified (null if not verified)
    ''',
    responses={
        200: OpenApiResponse(
            description='Verification status retrieved',
            examples=[
                OpenApiExample(
                    'Verified Phone',
                    value={
                        'is_verified': True,
                        'phone_number': '+2010****78',
                        'verified_at': '2024-02-15T18:30:00Z'
                    }
                ),
                OpenApiExample(
                    'Not Verified',
                    value={
                        'is_verified': False,
                        'phone_number': None,
                        'verified_at': None
                    }
                )
            ]
        ),
        401: OpenApiResponse(
            description='Authentication required'
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def phone_verification_status(request):
    """Get phone verification status for current user."""
    try:
        phone_verification = PhoneVerification.objects.get(user=request.user)
        phone_masked = phone_verification.phone_number[:5] + '****' + phone_verification.phone_number[-2:] if phone_verification.phone_number else None
        return Response({
            'is_verified': phone_verification.is_verified,
            'phone_number': phone_masked,
            'verified_at': phone_verification.verified_at
        })
    except PhoneVerification.DoesNotExist:
        return Response({
            'is_verified': False,
            'phone_number': None,
            'verified_at': None
        })


# ==================== Seller Verification Endpoints ====================

@extend_schema(
    tags=['Seller Verification'],
    summary='Submit seller KYC verification',
    description='''
    Submits seller verification (KYC) with national ID and documents.
    
    **Required Documents:**
    - National ID front photo (JPEG/PNG, max 5MB)
    - National ID back photo (JPEG/PNG, max 5MB)
    - Selfie photo (JPEG/PNG, max 5MB)
    
    **Security Notes:**
    - All sensitive data is encrypted
    - National ID is hashed for uniqueness check
    - Documents are securely stored
    
    **Business Rules:**
    - National ID must be 5-20 alphanumeric characters
    - National ID cannot be used by another verified seller
    - User can only have one verification submission
    - After submission, status is PENDING until admin reviews
    ''',
    request=SellerVerificationSerializer,
    examples=[
        OpenApiExample(
            'Complete Submission',
            value={
                'national_id': 'A12345678',
                'date_of_birth': '1990-01-15',
                'billing_address': '123 Main Street, New York, USA'
            },
            request_only=True
        ),
    ],
    responses={
        201: OpenApiResponse(
            description='Verification submitted successfully',
            examples=[
                OpenApiExample(
                    'Success Response',
                    value={
                        'message': 'Verification submitted successfully',
                        'status': 'PENDING'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description='Invalid request',
            examples=[
                OpenApiExample(
                    'Invalid National ID',
                    value={
                        'national_id': ['National ID must be between 5 and 20 characters']
                    }
                ),
                OpenApiExample(
                    'Duplicate Submission',
                    value={
                        'non_field_errors': ['You have already submitted a verification request']
                    }
                ),
                OpenApiExample(
                    'Missing Documents',
                    value={
                        'id_front_photo': ['This field is required.'],
                        'id_back_photo': ['This field is required.'],
                        'selfie_photo': ['This field is required.']
                    }
                )
            ],
        ),
        401: OpenApiResponse(
            description='Authentication required'
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([VerificationThrottle])  # SECURITY: Limit to 10 submissions per day
def submit_seller_verification(request):
    """Submit seller verification with KYC documents."""
    serializer = SellerVerificationSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Verification submitted successfully',
            'status': 'PENDING'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Seller Verification'],
    summary='Get seller verification status',
    description='''
    Retrieves the current seller verification status for the authenticated user.
    
    **Possible Statuses:**
    - PENDING: Under review by admin
    - APPROVED: Verification approved, can create offers
    - REJECTED: Verification rejected, see rejection_reason
    - RESUBMITTED: Resubmitted after rejection
    ''',
    responses={
        200: SellerVerificationSerializer,
        404: OpenApiResponse(
            description='No verification found',
            examples=[
                OpenApiExample(
                    'Not Found',
                    value={'detail': 'No verification found'}
                )
            ]
        ),
        401: OpenApiResponse(
            description='Authentication required'
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_verification_status(request):
    """Get seller verification status for current user."""
    try:
        verification = SellerVerification.objects.get(user=request.user)
        serializer = SellerVerificationSerializer(verification)
        return Response(serializer.data)
    except SellerVerification.DoesNotExist:
        return Response({'detail': 'No verification found'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Seller Verification'],
    summary='Check if user can create offers',
    description='''
    Checks if the authenticated user is eligible to create game boosting offers.
    
    **Eligibility Requirements:**
    - Seller verification must be APPROVED
    
    **Returns:**
    - can_create_offers: Boolean indicating eligibility
    - reason: Explanation if not eligible (null if eligible)
    ''',
    responses={
        200: OpenApiResponse(
            description='Eligibility status',
            examples=[
                OpenApiExample(
                    'Can Create Offers',
                    value={
                        'can_create_offers': True,
                        'reason': None
                    }
                ),
                OpenApiExample(
                    'Pending Verification',
                    value={
                        'can_create_offers': False,
                        'reason': 'Seller verification pending'
                    }
                ),
                OpenApiExample(
                    'Not Submitted',
                    value={
                        'can_create_offers': False,
                        'reason': 'Seller verification not submitted'
                    }
                )
            ]
        ),
        401: OpenApiResponse(
            description='Authentication required'
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def can_create_offers(request):
    """Check if user can create game boosting offers."""
    try:
        verification = SellerVerification.objects.get(user=request.user)
        if verification.is_verified:
            return Response({'can_create_offers': True, 'reason': None})
        return Response({
            'can_create_offers': False,
            'reason': f'Seller verification {verification.get_status_display().lower()}'
        })
    except SellerVerification.DoesNotExist:
        return Response({
            'can_create_offers': False,
            'reason': 'Seller verification not submitted'
        })


# ==================== Admin Verification Endpoints ====================

@extend_schema(
    tags=['Admin - Verification'],
    summary='List pending verifications',
    description='''
    Lists all seller verifications with PENDING or RESUBMITTED status.
    
    **Permissions:**
    - Admin or Support staff only
    
    **Returns:**
    - Array of verification summaries with user email and submission date
    ''',
    responses={
        200: OpenApiResponse(
            description='List of pending verifications',
            examples=[
                OpenApiExample(
                    'Pending List',
                    value=[
                        {
                            'id': 1,
                            'user_email': 'seller@example.com',
                            'submitted_at': '2024-02-15T10:30:00Z',
                            'status': 'PENDING'
                        },
                        {
                            'id': 2,
                            'user_email': 'seller2@example.com',
                            'submitted_at': '2024-02-15T11:00:00Z',
                            'status': 'RESUBMITTED'
                        }
                    ]
                )
            ]
        ),
        401: OpenApiResponse(description='Authentication required'),
        403: OpenApiResponse(
            description='Permission denied',
            examples=[
                OpenApiExample(
                    'Not Admin',
                    value={'detail': 'You do not have permission to perform this action.'}
                )
            ]
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAdminOrSupport])
def list_pending_verifications(request):
    """List all pending seller verifications (admin only)."""
    verifications = SellerVerification.objects.filter(
        status__in=['PENDING', 'RESUBMITTED']
    ).select_related('user')
    
    data = [{
        'id': v.id,
        'user_email': v.user.email,
        'submitted_at': v.submitted_at,
        'status': v.status
    } for v in verifications]
    
    return Response(data)


@extend_schema(
    tags=['Admin - Verification'],
    summary='Get verification details',
    description='''
    Retrieves complete details of a seller verification for admin review.
    
    **Permissions:**
    - Admin or Support staff only
    
    **Security:**
    - Action is logged for audit trail
    - Sensitive data access is tracked
    ''',
    parameters=[
        OpenApiParameter(
            name='verification_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='ID of the verification to retrieve',
            required=True,
            examples=[
                OpenApiExample('Example ID', value=1)
            ]
        )
    ],
    responses={
        200: SellerVerificationSerializer,
        404: OpenApiResponse(
            description='Verification not found',
            examples=[
                OpenApiExample(
                    'Not Found',
                    value={'detail': 'Verification not found'}
                )
            ]
        ),
        401: OpenApiResponse(description='Authentication required'),
        403: OpenApiResponse(description='Permission denied')
    }
)
@api_view(['GET'])
@permission_classes([IsAdminOrSupport])
def verification_details(request, verification_id):
    """Get detailed verification information (admin only)."""
    try:
        verification = SellerVerification.objects.get(id=verification_id)
        
        # Log admin action
        LoggingService.log_admin_action(
            admin_user=request.user,
            action=AdminActionLog.Action.VIEW_SENSITIVE_DATA,
            request=request,
            target_user=verification.user,
            details={'verification_id': verification_id}
        )
        
        serializer = SellerVerificationSerializer(verification)
        return Response(serializer.data)
    except SellerVerification.DoesNotExist:
        return Response({'detail': 'Verification not found'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Admin - Verification'],
    summary='Approve seller verification',
    description='''
    Approves a seller verification, allowing the user to create game boosting offers.
    
    **Permissions:**
    - Admin or Support staff only
    
    **Effects:**
    - Verification status changed to APPROVED
    - User can now create offers
    - Action logged for audit trail
    - Audit log entry created
    ''',
    parameters=[
        OpenApiParameter(
            name='verification_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='ID of the verification to approve',
            required=True
        )
    ],
    responses={
        200: OpenApiResponse(
            description='Verification approved',
            examples=[
                OpenApiExample(
                    'Success',
                    value={'message': 'Verification approved successfully'}
                )
            ]
        ),
        404: OpenApiResponse(description='Verification not found'),
        401: OpenApiResponse(description='Authentication required'),
        403: OpenApiResponse(description='Permission denied')
    }
)
@api_view(['POST'])
@permission_classes([IsAdminOrSupport])
def approve_verification(request, verification_id):
    """Approve a seller verification (admin only)."""
    try:
        verification = SellerVerification.objects.get(id=verification_id)
        verification.approve(request.user)
        
        # Send email notification
        email_service.send_verification_approved(verification.user.email)
        
        # Log admin action with IP
        LoggingService.log_admin_action(
            admin_user=request.user,
            action=AdminActionLog.Action.APPROVE_VERIFICATION,
            request=request,
            target_user=verification.user,
            details={'verification_id': verification_id}
        )
        
        # Log to audit trail with IP
        VerificationAuditLog.objects.create(
            user=verification.user,
            action='SELLER_APPROVED',
            performed_by=request.user,
            ip_address=get_client_ip(request),
            details={'verification_id': verification_id}
        )
        
        return Response({'message': 'Verification approved successfully'})
    except SellerVerification.DoesNotExist:
        return Response({'detail': 'Verification not found'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Admin - Verification'],
    summary='Reject seller verification',
    description='''
    Rejects a seller verification with a reason.
    
    **Permissions:**
    - Admin or Support staff only
    
    **Required:**
    - reason: Explanation for rejection (will be shown to user)
    
    **Effects:**
    - Verification status changed to REJECTED
    - Rejection reason stored
    - User notified (if notification system enabled)
    - Action logged for audit trail
    ''',
    parameters=[
        OpenApiParameter(
            name='verification_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description='ID of the verification to reject',
            required=True
        )
    ],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'reason': {
                    'type': 'string',
                    'description': 'Reason for rejection',
                    'example': 'National ID photo is not clear. Please resubmit with better quality images.'
                }
            },
            'required': ['reason']
        }
    },
    examples=[
        OpenApiExample(
            'Rejection with Reason',
            value={'reason': 'National ID photo is not clear. Please resubmit with better quality images.'},
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            description='Verification rejected',
            examples=[
                OpenApiExample(
                    'Success',
                    value={'message': 'Verification rejected successfully'}
                )
            ]
        ),
        400: OpenApiResponse(
            description='Missing reason',
            examples=[
                OpenApiExample(
                    'No Reason',
                    value={'detail': 'Rejection reason is required'}
                )
            ]
        ),
        404: OpenApiResponse(description='Verification not found'),
        401: OpenApiResponse(description='Authentication required'),
        403: OpenApiResponse(description='Permission denied')
    }
)
@api_view(['POST'])
@permission_classes([IsAdminOrSupport])
def reject_verification(request, verification_id):
    """Reject a seller verification with reason (admin only)."""
    reason = request.data.get('reason')
    if not reason:
        return Response(
            {'detail': 'Rejection reason is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        verification = SellerVerification.objects.get(id=verification_id)
        verification.reject(request.user, reason)
        
        # Log admin action
        LoggingService.log_admin_action(
            admin_user=request.user,
            action=AdminActionLog.Action.REJECT_VERIFICATION,
            request=request,
            target_user=verification.user,
            details={'verification_id': verification_id, 'reason': reason}
        )
        
        return Response({'message': 'Verification rejected successfully'})
    except SellerVerification.DoesNotExist:
        return Response({'detail': 'Verification not found'}, status=status.HTTP_404_NOT_FOUND)
