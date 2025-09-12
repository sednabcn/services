#!/bin/bash
# Quick SMTP Test Script
# Save as test_smtp.sh and run with: bash test_smtp.sh

echo "Quick SMTP Configuration Test"
echo "============================="

# Prompt for SMTP details
read -p "SMTP Host (e.g., smtp.gmail.com): " SMTP_HOST
read -p "SMTP Port (default 587): " SMTP_PORT
SMTP_PORT=${SMTP_PORT:-587}
read -p "SMTP Username/Email: " SMTP_USER
read -s -p "SMTP Password: " SMTP_PASS
echo
read -p "Test email recipient (press Enter to use sender): " TEST_EMAIL
TEST_EMAIL=${TEST_EMAIL:-$SMTP_USER}

echo
echo "Testing configuration:"
echo "Host: $SMTP_HOST"
echo "Port: $SMTP_PORT"
echo "User: $SMTP_USER"
echo "Test recipient: $TEST_EMAIL"
echo

# Test basic connectivity
echo "1. Testing connectivity to $SMTP_HOST:$SMTP_PORT..."
if timeout 10 bash -c "echo >/dev/tcp/$SMTP_HOST/$SMTP_PORT" 2>/dev/null; then
    echo "✅ Connection successful"
else
    echo "❌ Connection failed"
    echo "Check host and port settings"
    exit 1
fi

# Test with Python SMTP
echo
echo "2. Testing SMTP authentication and email sending..."

python3 << EOF
import smtplib
from email.mime.text import MIMEText
import sys

try:
    server = smtplib.SMTP('$SMTP_HOST', $SMTP_PORT, timeout=30)
    server.set_debuglevel(0)
    server.ehlo()
    
    if server.has_extn('STARTTLS'):
        server.starttls()
        server.ehlo()
    
    server.login('$SMTP_USER', '$SMTP_PASS')
    print("✅ Authentication successful")
    
    # Send test email
    msg = MIMEText('SMTP test successful!')
    msg['Subject'] = 'SMTP Test'
    msg['From'] = '$SMTP_USER'
    msg['To'] = '$TEST_EMAIL'
    
    server.sendmail('$SMTP_USER', ['$TEST_EMAIL'], msg.as_string())
    server.quit()
    
    print("✅ Test email sent successfully")
    print(f"Check {('$TEST_EMAIL')} for the test message")
    
except smtplib.SMTPAuthenticationError:
    print("❌ Authentication failed")
    print("Check username and password")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
EOF

echo
echo "SMTP test completed successfully!"
