"""
Serializers for verification app.
"""
from rest_framework import serializers
from apps.verification.models import PhoneVerification, SellerVerification, VerificationAuditLog
from common.services.otp import otp_service
from common.services.encryption import encryption_service
from common.validators import validate_egyptian_phone_number, validate_egyptian_national_id
from django.utils import timezone


class PhoneVerificationSerializer(serializers.ModelSerializer):
    """Serializer for phone verification"""
    
    phone_number = serializers.CharField(
        max_length=20,
        validators=[validate_egyptian_phone_number],
        write_only=True
    )
    phone_number_masked = serializers.SerializerMethodField()
    
    class Meta:
        model = PhoneVerification
        fields = [
            'id',
            'phone_number',
            'phone_number_masked',
            'is_verified',
            'verified_at',
            'created_at'
        ]
        read_only_fields = ['id', 'is_verified', 'verified_at', 'created_at']
    
    def get_phone_number_masked(self, obj):
        """Mask phone number for display"""
        if obj.phone_number:
            return obj.phone_number[:5] + '****' + obj.phone_number[-2:]
        return None


class SendOTPSerializer(serializers.Serializer):
    """Serializer for sending OTP"""
    
    phone_number = serializers.CharField(
        max_length=20,
        validators=[validate_egyptian_phone_number]
    )
    
    def validate_phone_number(self, value):
        """Check if phone is already verified by another user"""
        phone_hash = encryption_service.hash_national_id(value)
        
        # Exclude current user if they have phone verification
        user = self.context['request'].user
        existing = PhoneVerification.objects.filter(
            phone_number_hash=phone_hash,
            is_verified=True
        ).exclude(user=user)
        
        if existing.exists():
            raise serializers.ValidationError("This phone number is already verified with another account")
        
        return value
    
    def save(self):
        """Send OTP to phone number"""
        phone_number = self.validated_data['phone_number']
        user = self.context['request'].user
        phone_hash = encryption_service.hash_national_id(phone_number)
        
        # Get or create phone verification record
        phone_verification, created = PhoneVerification.objects.get_or_create(
            user=user,
            defaults={
                'phone_number': phone_number,
                'phone_number_hash': phone_hash
            }
        )
        
        # Update phone number if changed
        if not created and phone_verification.phone_number != phone_number:
            phone_verification.phone_number = phone_number
            phone_verification.phone_number_hash = phone_hash
            phone_verification.is_verified = False
            phone_verification.verified_at = None
            phone_verification.save()
        
        # Send OTP
        result = otp_service.send_otp(phone_number)
        return result


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP"""
    
    phone_number = serializers.CharField(
        max_length=20,
        validators=[validate_egyptian_phone_number]
    )
    otp = serializers.CharField(min_length=6, max_length=6)
    
    def validate(self, attrs):
        """Verify OTP matches"""
        phone_number = attrs['phone_number']
        otp = attrs['otp']
        
        # Verify OTP
        result = otp_service.verify_otp(phone_number, otp)
        if not result['success']:
            raise serializers.ValidationError(result['message'])
        
        return attrs
    
    def save(self):
        """Mark phone as verified"""
        phone_number = self.validated_data['phone_number']
        user = self.context['request'].user
        phone_hash = encryption_service.hash_national_id(phone_number)
        
        # Get or create phone verification
        phone_verification, created = PhoneVerification.objects.get_or_create(
            user=user,
            defaults={
                'phone_number': phone_number,
                'phone_number_hash': phone_hash
            }
        )
        
        # Mark as verified
        phone_verification.is_verified = True
        phone_verification.verified_at = timezone.now()
        phone_verification.save()
        
        return phone_verification


class SellerVerificationSerializer(serializers.ModelSerializer):
    """Serializer for seller verification submission"""
    
    national_id = serializers.CharField(
        max_length=14,
        write_only=True,
        validators=[validate_egyptian_national_id]
    )
    national_id_masked = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)
    
    class Meta:
        model = SellerVerification
        fields = [
            'id',
            'national_id',
            'national_id_masked',
            'date_of_birth',
            'billing_address',
            'id_front_photo',
            'id_back_photo',
            'selfie_photo',
            'status',
            'status_display',
            'rejection_reason',
            'reviewed_by_email',
            'reviewed_at',
            'submitted_at',
            'is_verified'
        ]
        read_only_fields = [
            'id',
            'status',
            'rejection_reason',
            'reviewed_by_email',
            'reviewed_at',
            'submitted_at',
            'is_verified'
        ]
    
    def get_national_id_masked(self, obj):
        """Mask national ID for display"""
        if obj.national_id_encrypted:
            decrypted = obj.national_id_decrypted
            if decrypted:
                return decrypted[:5] + '*********'
        return None
    
    def validate_national_id(self, value):
        """Validate national ID is not duplicate"""
        from apps.verification.services import verification_service
        
        user = self.context['request'].user
        if verification_service.check_duplicate_national_id(value, exclude_user_id=user.id):
            raise serializers.ValidationError("This National ID is already registered with another account")
        
        return value
    
    def validate(self, attrs):
        """Validate all required photos are provided"""
        if not self.instance:  # Only for creation
            required_photos = ['id_front_photo', 'id_back_photo', 'selfie_photo']
            for photo_field in required_photos:
                if photo_field not in attrs or not attrs[photo_field]:
                    raise serializers.ValidationError({
                        photo_field: "This photo is required"
                    })
        
        return attrs


class SellerVerificationAdminSerializer(SellerVerificationSerializer):
    """Extended serializer for admin with decrypted national ID"""
    
    national_id_decrypted = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.public_profile.username', read_only=True)
    
    class Meta(SellerVerificationSerializer.Meta):
        fields = SellerVerificationSerializer.Meta.fields + [
            'national_id_decrypted',
            'user_email',
            'user_username'
        ]
    
    def get_national_id_decrypted(self, obj):
        """Return decrypted national ID for admin"""
        return obj.national_id_decrypted


class ApproveVerificationSerializer(serializers.Serializer):
    """Serializer for approving verification"""
    
    notes = serializers.CharField(required=False, allow_blank=True)


class RejectVerificationSerializer(serializers.Serializer):
    """Serializer for rejecting verification"""
    
    reason = serializers.CharField(min_length=10, max_length=500)


class VerificationAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    performed_by_email = serializers.EmailField(source='performed_by.email', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = VerificationAuditLog
        fields = [
            'id',
            'user_email',
            'action',
            'action_display',
            'performed_by_email',
            'details',
            'ip_address',
            'timestamp'
        ]
        read_only_fields = '__all__'
