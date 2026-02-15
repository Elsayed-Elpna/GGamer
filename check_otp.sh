#!/bin/bash
# Quick OTP Checker - Shows the most recent OTP from logs

echo "🔍 Checking for recent OTP codes..."
echo "=================================="
echo ""

# Check backend logs for OTP
OTP_LOGS=$(docker compose logs backend 2>&1 | grep -i "otp for" | tail -5)

if [ -z "$OTP_LOGS" ]; then
    echo "❌ No OTP found in logs yet."
    echo ""
    echo "💡 Tips:"
    echo "1. Make sure you've sent an OTP request first"
    echo "2. The OTP is also returned in the API response (development only)"
    echo "3. Try: docker compose logs -f backend"
else
    echo "✅ Found OTP codes:"
    echo "$OTP_LOGS"
fi

echo ""
echo "=================================="
echo "📝 Note: In development, the OTP is also returned in the API response body"
echo "🚀 For production, integrate Twilio/Vonage - see sms_integration_guide.md"
