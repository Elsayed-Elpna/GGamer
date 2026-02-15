#!/bin/bash
# Comprehensive Endpoint Testing Script
# Tests all verification endpoints for functionality, validation, and security

BASE_URL="http://localhost:8000"
COOKIES_FILE="/tmp/test_cookies.txt"

echo "==================================="
echo "Verification Endpoints Test Suite"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_status="$5"
    local auth_required="$6"
    
    echo -n "Testing: $name... "
    
    if [ "$auth_required" = "true" ]; then
        if [ "$method" = "GET" ]; then
            response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url" -b "$COOKIES_FILE" 2>&1)
        else
            response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url" \
                -H "Content-Type: application/json" \
                -b "$COOKIES_FILE" \
                -d "$data" 2>&1)
        fi
    else
        if [ "$method" = "GET" ]; then
            response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url" 2>&1)
        else
            response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url" \
                -H "Content-Type: application/json" \
                -d "$data" 2>&1)
        fi
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (Status: $status_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected: $expected_status, Got: $status_code)"
        echo "  Response: $body"
        ((FAILED++))
        return 1
    fi
}

# 1. Login first to get authentication cookies
echo "=== Step 1: Authentication ==="
curl -s -X POST "$BASE_URL/api/auth/login/" \
    -H "Content-Type: application/json" \
    -d '{"email":"said.elpna5621@gmail.com","password":"123456"}' \
    -c "$COOKIES_FILE" > /dev/null

if [ -f "$COOKIES_FILE" ]; then
    echo -e "${GREEN}✓ Login successful${NC}"
else
    echo -e "${RED}✗ Login failed - cannot proceed with tests${NC}"
    exit 1
fi
echo ""

# 2. Phone Verification Tests
echo "=== Step 2: Phone Verification Endpoints ==="

# Test send OTP - valid phone
test_endpoint "Send OTP (valid phone)" "POST" "/api/verification/phone/send-otp/" \
    '{"phone_number":"+201033832316"}' "200" "true"

# Test send OTP - invalid phone format
test_endpoint "Send OTP (invalid format)" "POST" "/api/verification/phone/send-otp/" \
    '{"phone_number":"123"}' "400" "true"

# Test send OTP - missing phone
test_endpoint "Send OTP (missing field)" "POST" "/api/verification/phone/send-otp/" \
    '{}' "400" "true"

# Test send OTP - unauthorized
test_endpoint "Send OTP (no auth)" "POST" "/api/verification/phone/send-otp/" \
    '{"phone_number":"+201033832316"}' "401" "false"

# Get OTP from logs for testing
echo "Fetching OTP from backend logs..."
OTP=$(docker compose logs backend --tail 20 | grep "OTP for" | tail -1 | grep -oP '\d{6}' | head -1)
echo "OTP: $OTP"

# Test verify OTP - valid
if [ -n "$OTP" ]; then
    test_endpoint "Verify OTP (valid)" "POST" "/api/verification/phone/verify-otp/" \
        "{\"phone_number\":\"+201033832316\",\"otp\":\"$OTP\"}" "200" "true"
fi

# Test verify OTP - invalid code
test_endpoint "Verify OTP (invalid code)" "POST" "/api/verification/phone/verify-otp/" \
    '{"phone_number":"+201033832316","otp":"000000"}' "400" "true"

# Test phone status
test_endpoint "Phone Status" "GET" "/api/verification/phone/status/" "" "200" "true"

echo ""

# 3. Seller Verification Tests
echo "=== Step 3: Seller Verification Endpoints ==="

# Test can create offers (before verification)
test_endpoint "Can Create Offers (not verified)" "GET" "/api/verification/seller/can-create-offers/" "" "200" "true"

# Test seller status (no submission yet)
test_endpoint "Seller Status (no submission)" "GET" "/api/verification/seller/status/" "" "404" "true"

# Test submit seller verification - missing fields
test_endpoint "Submit Seller (missing fields)" "POST" "/api/verification/seller/submit/" \
    '{"national_id":"12345678901234"}' "400" "true"

# Test submit seller verification - invalid national ID
test_endpoint "Submit Seller (invalid ID)" "POST" "/api/verification/seller/submit/" \
    '{"national_id":"123","date_of_birth":"1990-01-01","billing_address":"Cairo"}' "400" "true"

echo ""

# 4. Admin Verification Tests
echo "=== Step 4: Admin Verification Endpoints ==="

# Test list pending verifications
test_endpoint "List Pending (admin)" "GET" "/api/verification/admin/pending/" "" "200" "true"

# Test verification details (non-existent)
test_endpoint "Verification Details (not found)" "GET" "/api/verification/admin/999/" "" "404" "true"

# Test approve verification (non-existent)
test_endpoint "Approve Verification (not found)" "POST" "/api/verification/admin/999/approve/" "" "404" "true"

# Test reject verification (no reason)
test_endpoint "Reject Verification (no reason)" "POST" "/api/verification/admin/1/reject/" \
    '{}' "400" "true"

echo ""

# 5. Security Tests
echo "=== Step 5: Security Tests ==="

# Test SQL injection in phone number
test_endpoint "SQL Injection Test" "POST" "/api/verification/phone/send-otp/" \
    '{"phone_number":"01012345678; DROP TABLE users;"}' "400" "true"

# Test XSS in phone number
test_endpoint "XSS Test" "POST" "/api/verification/phone/send-otp/" \
    '{"phone_number":"<script>alert(1)</script>"}' "400" "true"

# Test extremely long phone number
test_endpoint "Long Input Test" "POST" "/api/verification/phone/send-otp/" \
    "{\"phone_number\":\"$(printf '1%.0s' {1..1000})\"}" "400" "true"

echo ""

# Summary
echo "==================================="
echo "Test Summary"
echo "==================================="
echo -e "Total Tests: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${YELLOW}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
