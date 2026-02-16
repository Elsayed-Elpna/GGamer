"""
Email notification service for verification status changes.
Sends professional HTML emails to users when their verification is approved or rejected.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


class EmailNotificationService:
    """Service for sending email notifications"""
    
    @staticmethod
    def send_verification_approved(user_email, dashboard_url=None):
        """
        Send email notification when seller verification is approved.
        
        Args:
            user_email: User's email address
            dashboard_url: URL to seller dashboard
        """
        if dashboard_url is None:
            dashboard_url = f"{settings.FRONTEND_URL}/seller/dashboard" if hasattr(settings, 'FRONTEND_URL') else "#"
        
        context = {
            'user_email': user_email,
            'dashboard_url': dashboard_url
        }
        
        html_content = render_to_string('emails/verification_approved.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject='🎉 Your Seller Verification has been Approved!',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=True)
    
    @staticmethod
    def send_verification_rejected(user_email, rejection_reason, resubmit_url=None):
        """
        Send email notification when seller verification is rejected.
        
        Args:
            user_email: User's email address
            rejection_reason: Reason for rejection
            resubmit_url: URL to resubmit verification
        """
        if resubmit_url is None:
            resubmit_url = f"{settings.FRONTEND_URL}/seller/verification/resubmit" if hasattr(settings, 'FRONTEND_URL') else "#"
        
        context = {
            'user_email': user_email,
            'rejection_reason': rejection_reason,
            'resubmit_url': resubmit_url
        }
        
        html_content = render_to_string('emails/verification_rejected.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject='Action Required: Seller Verification Update',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=True)


# Create global instance
email_service = EmailNotificationService()
