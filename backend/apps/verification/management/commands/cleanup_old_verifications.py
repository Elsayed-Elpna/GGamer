"""
Management command to cleanup old rejected verifications.
Removes rejected verifications older than 90 days to comply with data retention policies.

Usage:
    python manage.py cleanup_old_verifications --dry-run  # Preview
    python manage.py cleanup_old_verifications             # Execute
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.verification.models import SellerVerification


class Command(BaseCommand):
    help = 'Cleanup rejected verifications older than 90 days'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview deletions without actually deleting',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Age in days for cleanup (default: 90)',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find old rejected verifications
        old_rejected = SellerVerification.objects.filter(
            status='REJECTED',
            updated_at__lt=cutoff_date
        )
        
        count = old_rejected.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} rejected verifications older than {days} days'
                )
            )
            for verification in old_rejected[:10]:  # Show first 10
                self.stdout.write(f'  - {verification.user.email} (rejected {verification.updated_at})')
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
            return
        
        # Actual deletion
        self.stdout.write(f'Deleting {count} old rejected verifications...')
        
        deleted_count = 0
        for verification in old_rejected:
            try:
                # Delete associated files
                if verification.id_front_photo:
                    verification.id_front_photo.delete(save=False)
                if verification.id_back_photo:
                    verification.id_back_photo.delete(save=False)
                if verification.selfie_photo:
                    verification.selfie_photo.delete(save=False)
                
                # Delete verification record
                verification.delete()
                deleted_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error deleting verification for {verification.user.email}: {e}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {deleted_count} old rejected verifications'
            )
        )
