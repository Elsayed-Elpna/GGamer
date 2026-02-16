"""
Dispute serializers.
"""
from rest_framework import serializers
from decimal import Decimal
from apps.disputes.models import (
    Dispute, DisputeEvidence, DisputeMessage, DisputeDecision
)


class DisputeEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for dispute evidence."""
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    
    class Meta:
        model = DisputeEvidence
        fields = [
            'id', 'uploaded_by_email', 'file', 'file_type',
            'file_size', 'description', 'created_at'
        ]
        read_only_fields = ['id', 'uploaded_by_email', 'file_type', 'file_size', 'created_at']


class DisputeMessageSerializer(serializers.ModelSerializer):
    """Serializer for dispute messages."""
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    
    class Meta:
        model = DisputeMessage
        fields = ['id', 'sender_email', 'message', 'is_internal', 'created_at']
        read_only_fields = fields


class DisputeDecisionSerializer(serializers.ModelSerializer):
    """Serializer for dispute decisions."""
    admin_email = serializers.EmailField(source='admin.email', read_only=True)
    
    class Meta:
        model = DisputeDecision
        fields = [
            'id', 'admin_email', 'decision_type', 'buyer_refund_amount',
            'seller_release_amount', 'reason', 'created_at'
        ]
        read_only_fields = fields


class DisputeListSerializer(serializers.ModelSerializer):
    """Serializer for dispute list."""
    order_id = serializers.UUIDField(source='order.id', read_only=True)
    created_by_email = serializers.EmailField(source='created_by_user.email', read_only=True)
    
    class Meta:
        model = Dispute
        fields = [
            'id', 'order_id', 'created_by_email', 'created_by_role',
            'reason', 'status', 'created_at', 'resolved_at'
        ]
        read_only_fields = fields


class DisputeDetailSerializer(serializers.ModelSerializer):
    """Serializer for dispute detail."""
    order_id = serializers.UUIDField(source='order.id', read_only=True)
    created_by_email = serializers.EmailField(source='created_by_user.email', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    evidence = DisputeEvidenceSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    decisions = DisputeDecisionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Dispute
        fields = [
            'id', 'order_id', 'created_by_email', 'created_by_role',
            'reason', 'description', 'status', 'assigned_to_email',
            'evidence', 'messages', 'decisions',
            'created_at', 'updated_at', 'resolved_at'
        ]
        read_only_fields = fields
    
    def get_messages(self, obj):
        """Get messages (filter internal if not staff)."""
        request = self.context.get('request')
        messages = obj.messages.all()
        
        # Non-staff cannot see internal messages
        if request and not request.user.is_staff:
            messages = messages.filter(is_internal=False)
        
        return DisputeMessageSerializer(messages, many=True).data


class CreateDisputeSerializer(serializers.Serializer):
    """Serializer for creating disputes."""
    reason = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=2000)


class UploadEvidenceSerializer(serializers.Serializer):
    """Serializer for uploading evidence."""
    file = serializers.FileField()
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_file(self, value):
        """Validate file size."""
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        return value


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending messages."""
    message = serializers.CharField(max_length=2000)
    is_internal = serializers.BooleanField(default=False)


class AdminDecisionSerializer(serializers.Serializer):
    """Base serializer for admin decisions."""
    reason = serializers.CharField(max_length=1000)


class PartialRefundSerializer(AdminDecisionSerializer):
    """Serializer for partial refund decision."""
    buyer_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    seller_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    def validate(self, data):
        """Validate amounts are positive."""
        if data['buyer_amount'] < 0 or data['seller_amount'] < 0:
            raise serializers.ValidationError("Amounts must be non-negative")
        return data
