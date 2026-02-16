#!/bin/bash
# Quick fix script for verification app configuration issue

echo "🔧 Fixing verification app configuration..."

# Fix file ownership
echo "1. Fixing file ownership..."
sudo chown el-banna:el-banna /home/el-banna/Desktop/GGamer/backend/apps/verification/apps.py

# Update apps.py with correct configuration
echo "2. Updating apps.py..."
cat > /home/el-banna/Desktop/GGamer/backend/apps/verification/apps.py << 'EOF'
from django.apps import AppConfig


class VerificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.verification'
    verbose_name = 'Verification'
EOF

# Clear Python cache
echo "3. Clearing Python cache..."
find /home/el-banna/Desktop/GGamer/backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /home/el-banna/Desktop/GGamer/backend -name "*.pyc" -delete 2>/dev/null

# Add encryption key to .env if not exists
echo "4. Checking encryption key..."
if ! grep -q "ENCRYPTION_KEY" /home/el-banna/Desktop/GGamer/backend/.env 2>/dev/null; then
    echo "ENCRYPTION_KEY=KnIuO1P827FPChaFLFbW1KLBwmSX-KokpvjpLUSYMDw=" >> /home/el-banna/Desktop/GGamer/backend/.env
    echo "   Added ENCRYPTION_KEY to .env"
fi

echo ""
echo "✅ Configuration fixed!"
echo ""
echo "Next steps:"
echo "1. cd /home/el-banna/Desktop/GGamer/backend"
echo "2. source ../venv/bin/activate"
echo "3. python manage.py makemigrations verification"
echo "4. python manage.py migrate"
echo "5. cd .. && docker compose up -d --build"
echo ""
echo "Then access Swagger at: http://localhost:8000/api/docs/"
