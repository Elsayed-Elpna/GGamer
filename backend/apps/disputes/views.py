"""
Dispute views and API endpoints.
Production-ready with admin decision panel.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.disputes.models import Dispute
from apps.disputes.serializers import (
    DisputeListSerializer,
    DisputeDetailSerializer,
    CreateDisputeSerializer,
    UploadEvidenceSerializer,
    SendMessageSerializer,
    AdminDecisionSerializer,
    PartialRefundSerializer
)
from apps.disputes.permissions import IsDisputeParticipant, IsAdminUser
from apps.disputes.services.dispute_service import DisputeService
from apps.orders.models import Order
from apps.verification.utils import get_client_ip


class DisputeListView(generics.ListAPIView):
    """
    List disputes.
    Users see their own disputes, admins see all.
    """
    serializer_class = DisputeListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            # Admins see all disputes
            return Dispute.objects.select_related(
                'order', 'created_by_user', 'assigned_to'
            ).all()
        else:
            # Users see disputes for their orders
            return Dispute.objects.filter(
                order__buyer=user
            ) | Dispute.objects.filter(
                order__seller=user
            ).select_related('order', 'created_by_user')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_dispute(request, order_id):
    """
    Create a dispute for an order.
    Only order participants can create disputes.
    """
    order = get_object_or_404(Order, id=order_id)
    
    serializer = CreateDisputeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        dispute = DisputeService.create_dispute(
            order=order,
            user=request.user,
            reason=serializer.validated_data['reason'],
            description=serializer.validated_data['description'],
            ip_address=ip_address
        )
        
        response_serializer = DisputeDetailSerializer(
            dispute,
            context={'request': request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


class DisputeDetailView(generics.RetrieveAPIView):
    """
    Get dispute details.
    Only participants and staff can view.
    """
    serializer_class = DisputeDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsDisputeParticipant]
    queryset = Dispute.objects.all()
    
    def get_serializer_context(self):
        return {'request': self.request}


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_evidence(request, pk):
    """Upload evidence for a dispute."""
    dispute = get_object_or_404(Dispute, pk=pk)
    
    # Check permission
    if not (dispute.order.is_participant(request.user) or request.user.is_staff):
        return Response(
            {'error': 'You cannot upload evidence to this dispute'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = UploadEvidenceSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        evidence = DisputeService.upload_evidence(
            dispute=dispute,
            user=request.user,
            file=serializer.validated_data['file'],
            description=serializer.validated_data.get('description', '')
        )
        
        from apps.disputes.serializers import DisputeEvidenceSerializer
        response_serializer = DisputeEvidenceSerializer(evidence)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message(request, pk):
    """Send message in dispute."""
    dispute = get_object_or_404(Dispute, pk=pk)
    
    serializer = SendMessageSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        message = DisputeService.send_message(
            dispute=dispute,
            user=request.user,
            message=serializer.validated_data['message'],
            is_internal=serializer.validated_data.get('is_internal', False)
        )
        
        from apps.disputes.serializers import DisputeMessageSerializer
        response_serializer = DisputeMessageSerializer(message)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )


# ===== ADMIN DECISION ENDPOINTS =====

@api_view(['POST'])
@permission_classes([IsAdminUser])
def refund_buyer(request, pk):
    """Admin: Full refund to buyer."""
    dispute = get_object_or_404(Dispute, pk=pk)
    
    serializer = AdminDecisionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        decision = DisputeService.refund_buyer_full(
            dispute=dispute,
            admin=request.user,
            reason=serializer.validated_data['reason'],
            ip_address=ip_address
        )
        
        from apps.disputes.serializers import DisputeDecisionSerializer
        response_serializer = DisputeDecisionSerializer(decision)
        return Response(response_serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def release_seller(request, pk):
    """Admin: Release funds to seller."""
    dispute = get_object_or_404(Dispute, pk=pk)
    
    serializer = AdminDecisionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        decision = DisputeService.release_to_seller(
            dispute=dispute,
            admin=request.user,
            reason=serializer.validated_data['reason'],
            ip_address=ip_address
        )
        
        from apps.disputes.serializers import DisputeDecisionSerializer
        response_serializer = DisputeDecisionSerializer(decision)
        return Response(response_serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def partial_refund(request, pk):
    """Admin: Partial refund (split funds)."""
    dispute = get_object_or_404(Dispute, pk=pk)
    
    serializer = PartialRefundSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        decision = DisputeService.partial_refund(
            dispute=dispute,
            admin=request.user,
            buyer_amount=serializer.validated_data['buyer_amount'],
            seller_amount=serializer.validated_data['seller_amount'],
            reason=serializer.validated_data['reason'],
            ip_address=ip_address
        )
        
        from apps.disputes.serializers import DisputeDecisionSerializer
        response_serializer = DisputeDecisionSerializer(decision)
        return Response(response_serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def ban_seller(request, pk):
    """Admin: Ban seller and refund buyer."""
    dispute = get_object_or_404(Dispute, pk=pk)
    
    serializer = AdminDecisionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        decision = DisputeService.ban_seller(
            dispute=dispute,
            admin=request.user,
            reason=serializer.validated_data['reason'],
            ip_address=ip_address
        )
        
        from apps.disputes.serializers import DisputeDecisionSerializer
        response_serializer = DisputeDecisionSerializer(decision)
        return Response(response_serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def close_dispute(request, pk):
    """Admin: Close dispute with no action."""
    dispute = get_object_or_404(Dispute, pk=pk)
    
    serializer = AdminDecisionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        decision = DisputeService.close_dispute(
            dispute=dispute,
            admin=request.user,
            reason=serializer.validated_data['reason'],
            ip_address=ip_address
        )
        
        from apps.disputes.serializers import DisputeDecisionSerializer
        response_serializer = DisputeDecisionSerializer(decision)
        return Response(response_serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
