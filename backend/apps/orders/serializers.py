"""
Order serializers.
Handles API input/output for order operations.
"""
from rest_framework import serializers
from apps.orders.models import Order, OrderStateLog, ProofUpload, EscrowAccount
from apps.accounts.models import User
from apps.marketplace.models import Offer


class OrderStateLogSerializer(serializers.ModelSerializer):
    """Serializer for order state change logs."""
    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True)
    
    class Meta:
        model = OrderStateLog
        fields = [
            'id', 'from_state', 'to_state', 'changed_by_email',
            'reason', 'ip_address', 'created_at'
        ]
        read_only_fields = fields


class ProofUploadSerializer(serializers.ModelSerializer):
    """Serializer for delivery proof uploads."""
    
    class Meta:
        model = ProofUpload
        fields = ['id', 'file_type', 'file', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class EscrowAccountSerializer(serializers.ModelSerializer):
    """Serializer for escrow account details."""
    remaining_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        source='remaining_balance'
    )
    
    class Meta:
        model = EscrowAccount
        fields = [
            'id', 'amount_held', 'amount_released', 'amount_refunded',
            'remaining_balance', 'status', 'held_at', 'released_at'
        ]
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list view."""
    buyer_email = serializers.EmailField(source='buyer.email', read_only=True)
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    offer_title = serializers.CharField(source='offer.title', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'buyer_email', 'seller_email', 'offer_title',
            'quantity', 'total_amount', 'state', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed order view."""
    buyer_email = serializers.EmailField(source='buyer.email', read_only=True)
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    offer_title = serializers.CharField(source='offer.title', read_only=True)
    offer_id = serializers.UUIDField(source='offer.id', read_only=True)
    state_logs = OrderStateLogSerializer(many=True, read_only=True)
    proofs = ProofUploadSerializer(many=True, read_only=True)
    escrow = EscrowAccountSerializer(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'buyer_email', 'seller_email', 'offer_id', 'offer_title',
            'quantity', 'unit_price', 'total_amount', 'platform_fee',
            'seller_amount', 'delivery_method', 'buyer_notes', 'seller_notes',
            'state', 'created_at', 'updated_at', 'paid_at', 'completed_at',
            'state_logs', 'proofs', 'escrow'
        ]
        read_only_fields = [
            'id', 'buyer_email', 'seller_email', 'unit_price', 'total_amount',
            'platform_fee', 'seller_amount', 'state', 'created_at', 'updated_at',
            'paid_at', 'completed_at', 'state_logs', 'proofs', 'escrow'
        ]


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating a new order."""
    offer_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=1000) # SECURITY: Max 1000 items
    buyer_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_offer_id(self, value):
        """Validate offer exists and is active."""
        try:
            offer = Offer.objects.get(id=value, status=Offer.ACTIVE)
            self.context['offer'] = offer
            return value
        except Offer.DoesNotExist:
            raise serializers.ValidationError("Offer not found or not available")
    
    def create(self, validated_data):
        """Create order via OrderService."""
        from apps.orders.services.order_service import OrderService
        
        buyer = self.context['request'].user
        offer = self.context['offer']
        
        order = OrderService.create_order(
            buyer=buyer,
            offer=offer,
            quantity=validated_data['quantity'],
            buyer_notes=validated_data.get('buyer_notes', '')
        )
        
        return order


class DeliverOrderSerializer(serializers.Serializer):
    """Serializer for seller delivering order."""
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )
    proof_files = serializers.ListField(
        child=serializers.FileField(),
        max_length=5,
        help_text="Max 5 proof files"
    )
    
    def validate_proof_files(self, value):
        """Validate proof files."""
        if not value:
            raise serializers.ValidationError("At least one proof file is required")
        
        # Validate file sizes (max 10MB each)
        max_size = 10 * 1024 * 1024  # 10MB
        for file in value:
            if file.size > max_size:
                raise serializers.ValidationError(
                    f"File {file.name} exceeds max size of 10MB"
                )
        
        return value


class CancelOrderSerializer(serializers.Serializer):
    """Serializer for cancelling orders."""
    reason = serializers.CharField(max_length=500)
