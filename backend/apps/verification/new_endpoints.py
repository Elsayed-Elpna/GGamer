"""
Additional verification endpoints for resubmission and analytics.
Append these to views.py
"""

# ==================== Resubmission Endpoint ====================

@extend_schema(
    tags=['Seller Verification'],
    summary='Resubmit rejected seller verification',
    description='''
    Allows users to update and resubmit a rejected verification.
    
    **Requirements:**
    - User must have a REJECTED verification
    - Can update any field (national_id, documents, address, etc.)
    
    **Effects:**
    - Status changed to RESUBMITTED
    - Updated documents uploaded
    - Placed back in review queue
    ''',
    request=SellerVerificationSerializer,
    responses={
        200: OpenApiResponse(
            description='Resubmitted successfully',
            examples=[
                OpenApiExample(
                    'Success',
                    value={'message': 'Verification resubmitted successfully', 'status': 'RESUBMITTED'}
                )
            ]
        ),
        400: OpenApiResponse(description='Invalid data'),
        404: OpenApiResponse(description='No rejected verification found'),
    }
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([VerificationThrottle])
def resubmit_seller_verification(request):
    """Resubmit a rejected seller verification."""
    try:
        verification = SellerVerification.objects.get(
            user=request.user,
            status='REJECTED'
        )
    except SellerVerification.DoesNotExist:
        return Response(
            {'detail': 'No rejected verification found to resubmit'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = SellerVerificationSerializer(
        verification,
        data=request.data,
        partial=True,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        # Update status to RESUBMITTED
        verification.status = 'RESUBMITTED'
        verification.rejection_reason = None
        verification.save()
        
        return Response({
            'message': 'Verification resubmitted successfully',
            'status': 'RESUBMITTED'
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==================== Admin Analytics Endpoint ====================

@extend_schema(
    tags=['Admin - Verification'],
    summary='Get verification statistics',
    description='''
    Returns aggregate statistics for seller verifications.
    
    **Admin only**
    
    **Returns:**
    - Total verifications
    - Pending count
    - Approved count
    - Rejected count
    - Resubmitted count
    ''',
    responses={
        200: OpenApiResponse(
            description='Statistics retrieved',
            examples=[
                OpenApiExample(
                    'Stats',
                    value={
                        'total': 100,
                        'pending': 15,
                        'approved': 70,
                        'rejected': 10,
                        'resubmitted': 5
                    }
                )
            ]
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAdminOrSupport])
def verification_statistics(request):
    """Get verification statistics (admin only)."""
    from django.db.models import Count, Q
    
    stats = SellerVerification.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='PENDING')),
        approved=Count('id', filter=Q(status='APPROVED')),
        rejected=Count('id', filter=Q(status='REJECTED')),
        resubmitted=Count('id', filter=Q(status='RESUBMITTED')),
    )
    
    return Response(stats)
