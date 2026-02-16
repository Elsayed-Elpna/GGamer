"""
Order views and API endpoints.
Production-ready with full security and audit logging.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.orders.models import Order
from apps.orders.serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    CreateOrderSerializer,
    DeliverOrderSerializer,
    CancelOrderSerializer
)
from apps.orders.permissions import IsOrderParticipant, IsOrderBuyer, IsOrderSeller
from apps.orders.services.order_service import OrderService
from apps.verification.utils import get_client_ip


class OrderListCreateView(generics.ListCreateAPIView):
    """
    List user's orders and create new orders.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateOrderSerializer
        return OrderListSerializer
    
    def get_queryset(self):
        """
        Return orders where user is buyer or seller.
        """
        user = self.request.user
        return Order.objects.filter(
            models.Q(buyer=user) | models.Q(seller=user)
        ).select_related(
            'buyer', 'seller', 'offer'
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Create order."""
        serializer.save()


class OrderDetailView(generics.RetrieveAPIView):
    """
    Get order details.
    Only buyer or seller can view.
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrderParticipant]
    queryset = Order.objects.all()
    
    def get_queryset(self):
        return Order.objects.select_related(
            'buyer', 'seller', 'offer'
        ).prefetch_related(
            'state_logs', 'proofs', 'escrow'
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_order(request, pk):
    """
    Seller starts working on order.
    Transitions: PAID → IN_PROGRESS
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Check permission
    if not order.is_seller(request.user):
        return Response(
            {'error': 'Only the seller can start this order'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        ip_address = get_client_ip(request)
        updated_order = OrderService.start_order(
            order=order,
            seller=request.user,
            ip_address=ip_address
        )
        
        serializer = OrderDetailSerializer(updated_order)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deliver_order(request, pk):
    """
    Seller delivers order with proof.
    Transitions: IN_PROGRESS → DELIVERED
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Check permission
    if not order.is_seller(request.user):
        return Response(
            {'error': 'Only the seller can deliver this order'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = DeliverOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        updated_order = OrderService.deliver_order(
            order=order,
            seller=request.user,
            proof_files=serializer.validated_data['proof_files'],
            description=serializer.validated_data.get('description', ''),
            ip_address=ip_address
        )
        
        response_serializer = OrderDetailSerializer(updated_order)
        return Response(response_serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_delivery(request, pk):
    """
    Buyer confirms receipt of order.
    Transitions: DELIVERED → CONFIRMED
    Releases escrow funds to seller.
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Check permission
    if not order.is_buyer(request.user):
        return Response(
            {'error': 'Only the buyer can confirm this order'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        ip_address = get_client_ip(request)
        updated_order = OrderService.confirm_delivery(
            order=order,
            buyer=request.user,
            ip_address=ip_address
        )
        
        serializer = OrderDetailSerializer(updated_order)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_order(request, pk):
    """
    Cancel order.
    Available to buyer, seller, or admin.
    """
    order = get_object_or_404(Order, pk=pk)
    
    serializer = CancelOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        updated_order = OrderService.cancel_order(
            order=order,
            user=request.user,
            reason=serializer.validated_data['reason'],
            ip_address=ip_address
        )
        
        response_serializer = OrderDetailSerializer(updated_order)
        return Response(response_serializer.data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# Import models at the end
from django.db import models as django_models
models.Q = django_models.Q
