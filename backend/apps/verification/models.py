from django.db import models
from django.conf import settings
from common.services.encryption import encryption_service


class PhoneVerification(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="phone_verification")
    phone_number = models.CharField(max_length=20)
    phone_number_hash = models.CharField(max_length=255, unique=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "phone_verifications"
    
    def __str__(self):
        return f"{self.user.email} - {self.phone_number[:5]}****"


class SellerVerification(models.Model):
    STATUS_CHOICES = [("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("RESUBMITTED", "Resubmitted")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_verification")
    national_id_encrypted = models.TextField()
    national_id_hash = models.CharField(max_length=255, unique=True)
    date_of_birth = models.DateField()
    billing_address = models.TextField()
    id_front_photo = models.ImageField(upload_to="verifications/id_front/")
    id_back_photo = models.ImageField(upload_to="verifications/id_back/")
    selfie_photo = models.ImageField(upload_to="verifications/selfie/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    rejection_reason = models.TextField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_verifications")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "seller_verifications"
    
    def __str__(self):
        return f"{self.user.email} - {self.get_status_display()}"
    
    @property
    def is_verified(self):
        return self.status == "APPROVED"
    
    @property
    def national_id_decrypted(self):
        try:
            return encryption_service.decrypt_national_id(self.national_id_encrypted)
        except:
            return None
    
    def approve(self, admin_user):
        self.status = "APPROVED"
        self.reviewed_by = admin_user
        from django.utils import timezone
        self.reviewed_at = timezone.now()
        self.rejection_reason = None
        self.save()
    
    def reject(self, admin_user, reason):
        self.status = "REJECTED"
        self.reviewed_by = admin_user
        from django.utils import timezone
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class VerificationAuditLog(models.Model):
    ACTION_CHOICES = [("OTP_SENT", "OTP Sent"), ("OTP_VERIFIED", "OTP Verified"), ("SELLER_SUBMITTED", "Submitted"), ("SELLER_APPROVED", "Approved"), ("SELLER_REJECTED", "Rejected"), ("ADMIN_VIEWED", "Viewed")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_audit_logs")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="performed_verification_actions")
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "verification_audit_logs"
        ordering = ["-timestamp"]
