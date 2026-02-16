"""
Production deployment checklist and security verification.

This script helps verify that all security measures are in place before production.
"""

# ============================================
# PRODUCTION SECURITY CHECKLIST
# ============================================

## 1. HTTPS ENFORCEMENT

### Django Settings (backend/config/settings.py)
```python
# In production settings, add these:

if not DEBUG:
    # Force HTTPS
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Secure cookies
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Prevent clickjacking
    X_FRAME_OPTIONS = 'DENY'
    
    # XSS protection
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
```

### Nginx Configuration (if using Nginx)
```nginx
server {
    listen 80;
    server_name api.ggamer.com;
    
    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.ggamer.com;
    
    # SSL certificates
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    
    # SSL configuration (Mozilla Modern)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 2. ENVIRONMENT VARIABLES VERIFICATION

### Required Production Variables (.env)
```bash
# Database
DB_NAME=ggamer_production
DB_USER=ggamer_prod_user
DB_PASSWORD=<strong-random-password>
DB_HOST=<production-db-host>
DB_PORT=5432

# Django
DEBUG=False
SECRET_KEY=<generate-new-random-50+-char-key>
ALLOWED_HOSTS=api.ggamer.com,www.ggamer.com

# Email (SendGrid)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<your-sendgrid-api-key>
DEFAULT_FROM_EMAIL=noreply@ggamer.com

# Frontend URL
FRONTEND_URL=https://ggamer.com

# Encryption
ENCRYPTION_KEY=<generate-new-fernet-key>

# JWT
JWT_ACCESS_LIFETIME=15
JWT_REFRESH_LIFETIME=1

# Redis (for caching/throttling)
REDIS_URL=redis://:<password>@<redis-host>:6379/0
```

### Generate New Encryption Key
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Generate New Secret Key
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

## 3. IP LOGGING VERIFICATION

✅ IP logging is implemented in these admin endpoints:
- `approve_verification()` - Logs admin IP when approving
- `reject_verification()` - Logs admin IP when rejecting
- `verification_details()` - Logs admin IP when viewing details

**Implementation location:** `apps/verification/views.py`
**Helper function:** `apps/verification/utils.py::get_client_ip()`

**How it works:**
1. Uses `X-Forwarded-For` header (for proxy/load balancer)
2. Falls back to `REMOTE_ADDR` (direct connection)
3. Stores IP in audit log/verification record

**Verify in production:**
```bash
# Check audit logs
docker exec ggamer-backend python manage.py shell
>>> from apps.verification.models import SellerVerification
>>> v = SellerVerification.objects.filter(status='APPROVED').latest('reviewed_at')
>>> print(v.reviewed_by, v.reviewed_at, v.admin_ip)  # Should show IP
```

## 4. ADMIN ACCESS SECURITY

### Create Admin Users Securely
```bash
docker exec -it ggamer-backend python manage.py shell
```

```python
from apps.accounts.models import User

# Create admin
admin = User.objects.create_user(
    email='admin@ggamer.com',
    password='<strong-password>',
    first_name='Admin',
    last_name='User',
    is_staff=True,
    is_superuser=True,
    is_phone_verified=True
)

print(f"Admin created: {admin.email}")
```

### Admin Best Practices
- ✅ Use password manager for admin credentials
- ✅ Enable 2FA (future enhancement)
- ✅ Limit number of admin users (principle of least privilege)
- ✅ Review admin user list monthly
- ✅ Disable former staff accounts immediately
- ✅ Never share admin credentials

## 5. PRODUCTION DEPLOYMENT STEPS

### Step 1: Update Environment Variables (5 min)
```bash
cd /home/el-banna/Desktop/GGamer/backend
nano .env

# Update these:
# - DEBUG=False
# - SECRET_KEY=<new-random-key>
# - SENDGRID_API_KEY=<real-api-key>
# - FRONTEND_URL=<production-url>
# - ENCRYPTION_KEY=<new-key>
# - DB credentials
```

### Step 2: Update Django Settings (10 min)
```bash
nano config/settings.py

# Add production security settings (see HTTPS section above)
```

### Step 3: Collect Static Files (2 min)
```bash
docker exec ggamer-backend python manage.py collectstatic --noinput
```

### Step 4: Run Migrations (2 min)
```bash
docker exec ggamer-backend python manage.py migrate
```

### Step 5: Create Superuser (2 min)
```bash
docker exec -it ggamer-backend python manage.py createsuperuser
```

### Step 6: Run Security Checks (2 min)
```bash
docker exec ggamer-backend python manage.py check --deploy
```

### Step 7: Test Email Sending (5 min)
```bash
docker exec -it ggamer-backend python manage.py shell
```

```python
from django.core.mail import send_mail

send_mail(
    'Test Email',
    'This is a test email from GGamer verification system.',
    'noreply@ggamer.com',
    ['test@example.com'],
    fail_silently=False,
)
```

### Step 8: Restart Services (3 min)
```bash
docker-compose restart
```

### Step 9: Verify HTTPS (2 min)
```bash
curl -I https://api.ggamer.com/api/verification/phone/status/
# Should return HTTPS headers, not redirect to HTTP
```

### Step 10: Test Admin Flow (10 min)
1. Create test seller verification
2. Login as admin
3. View verification details (check IP is logged)
4. Approve verification (check email sent)
5. Verify audit log has IP address

## 6. MONITORING & ALERTS

### Setup Audit Log Monitoring
```python
# Create management command: apps/verification/management/commands/check_admin_actions.py

from django.core.management.base import BaseCommand
from apps.verification.models import SellerVerification
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Check for suspicious admin actions'
    
    def handle(self, *args, **options):
        # Check for reviews in last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        recent_reviews = SellerVerification.objects.filter(
            reviewed_at__gte=yesterday
        ).exclude(reviewed_by__isnull=True)
        
        for verification in recent_reviews:
            self.stdout.write(
                f"Admin: {verification.reviewed_by.email}, "
                f"IP: {verification.admin_ip or 'NOT LOGGED'}, "
                f"Action: {verification.status}, "
                f"Time: {verification.reviewed_at}"
            )
```

### Run Daily
```bash
# Add to crontab
0 9 * * * docker exec ggamer-backend python manage.py check_admin_actions
```

## 7. POST-DEPLOYMENT VERIFICATION

### Checklist
- [ ] HTTPS enforced (no HTTP access)
- [ ] SSL certificate valid (not expired, not self-signed)
- [ ] Email notifications working
- [ ] Admin IP logging working
- [ ] Rate limiting active
- [ ] OTP sending working
- [ ] File uploads working
- [ ] National ID encryption working
- [ ] Audit logs capturing all actions
- [ ] HSTS headers present
- [ ] Security headers present (X-Frame-Options, etc.)

### Run These Tests
```bash
# 1. Test HTTPS redirect
curl -I http://api.ggamer.com
# Should return 301 redirect to https://

# 2. Test security headers
curl -I https://api.ggamer.com
# Should include:
# Strict-Transport-Security: max-age=31536000
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff

# 3. Test API endpoint
curl https://api.ggamer.com/api/verification/phone/status/ \
  -H "Authorization: Bearer <token>"
# Should return 200 with JSON

# 4. Test rate limiting
for i in {1..6}; do
  curl -X POST https://api.ggamer.com/api/verification/phone/send-otp/ \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{"phone_number": "+201012345678"}'
done
# 6th request should return 429 Too Many Requests
```

## 8. INCIDENT RESPONSE

### If Sensitive Data is Exposed
1. **Immediate:**
   - Revoke compromised admin tokens
   - Change admin passwords
   - Review audit logs for unauthorized access
   - Notify affected users (if applicable)

2. **Within 24 hours:**
   - Rotate encryption keys
   - Re-encrypt all national IDs
   - Review all admin actions from suspicious IPs
   - Update firewall rules

3. **Within 1 week:**
   - Full security audit
   - Penetration testing
   - Update incident response plan

### Suspicious Activity Indicators
- Admin access from unknown IPs
- High volume of verifications from single admin
- Admin actions outside business hours
- Failed login attempts (brute force)
- Unusual approval/rejection patterns

---

## SUMMARY

### Security Measures for Admin National ID Access

**Why decryption is necessary:**
- Admins MUST see full national ID to verify against ID photos
- This is core KYC requirement for marketplace trust and safety

**How it's protected:**
1. ✅ **Admin-only access** (is_staff=True required)
2. ✅ **HTTPS encryption** in transit
3. ✅ **Database encryption** at rest
4. ✅ **IP logging** for audit trail
5. ✅ **JWT authentication** required
6. ✅ **Audit logging** all admin actions
7. ✅ **Minimal exposure** (only during active review)

**Production requirements:**
- ⚠️ **MUST use HTTPS** - Never HTTP
- ⚠️ **Monitor audit logs** - Weekly reviews
- ⚠️ **Alert on new IPs** - Unusual admin access
- ⚠️ **Limit admin users** - Principle of least privilege

**Compliance:**
This approach aligns with:
- PCI DSS (encryption at rest and in transit)
- GDPR (minimal data exposure, audit trails)
- SOC 2 (access controls, monitoring)

---

**Last Updated:** 2026-02-16
**Verified By:** Backend Team
**Production Ready:** ✅ YES (after HTTPS setup)
