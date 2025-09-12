#!/usr/bin/env python3
"""
SMTP Configuration Test Suite
Tests SMTP settings with various diagnostic levels
"""

import smtplib
import socket
import ssl
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import time

class SMTPTester:
    def __init__(self, host=None, port=None, username=None, password=None):
        # Try to get from environment variables first
        self.host = host or os.getenv('SMTP_HOST')
        self.port = int(port or os.getenv('SMTP_PORT', '587'))
        self.username = username or os.getenv('SMTP_USER')
        self.password = password or os.getenv('SMTP_PASS')
        
        print("SMTP Configuration Test Suite")
        print("=" * 50)
        print(f"Host: {self.host}")
        print(f"Port: {self.port}")
        print(f"Username: {self.username}")
        print(f"Password: {'*' * len(self.password) if self.password else 'Not set'}")
        print("=" * 50)

    def test_1_basic_connectivity(self):
        """Test basic network connectivity to SMTP server"""
        print("\n1. Testing basic connectivity...")
        
        if not self.host:
            print("❌ FAILED: SMTP_HOST not configured")
            return False
            
        try:
            # Test raw socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            
            if result == 0:
                print(f"✅ SUCCESS: Can connect to {self.host}:{self.port}")
                return True
            else:
                print(f"❌ FAILED: Cannot connect to {self.host}:{self.port} (Error: {result})")
                return False
                
        except Exception as e:
            print(f"❌ FAILED: Connection error: {e}")
            return False

    def test_2_smtp_handshake(self):
        """Test SMTP protocol handshake"""
        print("\n2. Testing SMTP handshake...")
        
        try:
            server = smtplib.SMTP(timeout=30)
            server.set_debuglevel(1)  # Enable verbose logging
            
            print(f"Connecting to {self.host}:{self.port}...")
            server.connect(self.host, self.port)
            
            print("Getting server capabilities...")
            response = server.ehlo()
            print(f"EHLO response: {response}")
            
            server.quit()
            print("✅ SUCCESS: SMTP handshake completed")
            return True
            
        except Exception as e:
            print(f"❌ FAILED: SMTP handshake error: {e}")
            return False

    def test_3_starttls_support(self):
        """Test STARTTLS encryption support"""
        print("\n3. Testing STARTTLS support...")
        
        try:
            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.ehlo()
            
            if server.has_extn('STARTTLS'):
                print("✅ Server supports STARTTLS")
                server.starttls()
                server.ehlo()  # Re-identify after STARTTLS
                print("✅ SUCCESS: STARTTLS encryption established")
                server.quit()
                return True
            else:
                print("❌ FAILED: Server does not support STARTTLS")
                server.quit()
                return False
                
        except Exception as e:
            print(f"❌ FAILED: STARTTLS error: {e}")
            return False

    def test_4_authentication(self):
        """Test SMTP authentication"""
        print("\n4. Testing authentication...")
        
        if not self.username or not self.password:
            print("❌ FAILED: Username or password not configured")
            return False
            
        try:
            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.ehlo()
            
            # Try STARTTLS if available
            if server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo()
            
            print("Attempting authentication...")
            server.login(self.username, self.password)
            print("✅ SUCCESS: Authentication successful")
            
            server.quit()
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ FAILED: Authentication failed: {e}")
            print("Check username and password")
            return False
        except Exception as e:
            print(f"❌ FAILED: Authentication error: {e}")
            return False

    def test_5_send_test_email(self, recipient_email=None):
        """Send a test email"""
        print("\n5. Testing email sending...")
        
        if not recipient_email:
            recipient_email = input("Enter test recipient email (or press Enter to use sender): ").strip()
            if not recipient_email:
                recipient_email = self.username
        
        try:
            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.ehlo()
            
            if server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo()
            
            server.login(self.username, self.password)
            
            # Create test message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = recipient_email
            msg['Subject'] = "SMTP Test Email"
            
            body = f"""
This is a test email sent from the SMTP configuration test suite.

Configuration details:
- SMTP Host: {self.host}
- SMTP Port: {self.port}
- From: {self.username}
- To: {recipient_email}
- Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}

If you received this email, your SMTP configuration is working correctly.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            print(f"Sending test email to {recipient_email}...")
            server.sendmail(self.username, [recipient_email], msg.as_string())
            
            server.quit()
            print("✅ SUCCESS: Test email sent successfully")
            return True
            
        except Exception as e:
            print(f"❌ FAILED: Email sending error: {e}")
            return False

    def test_6_common_configurations(self):
        """Test common SMTP provider configurations"""
        print("\n6. Testing common provider configurations...")
        
        common_configs = {
            'Gmail': {'host': 'smtp.gmail.com', 'port': 587},
            'Outlook/Hotmail': {'host': 'smtp-mail.outlook.com', 'port': 587},
            'Yahoo': {'host': 'smtp.mail.yahoo.com', 'port': 587},
            'Amazon SES': {'host': 'email-smtp.us-east-1.amazonaws.com', 'port': 587},
            'SendGrid': {'host': 'smtp.sendgrid.net', 'port': 587},
            'Mailgun': {'host': 'smtp.mailgun.org', 'port': 587}
        }
        
        current_config = f"{self.host}:{self.port}"
        
        for provider, config in common_configs.items():
            test_config = f"{config['host']}:{config['port']}"
            if current_config == test_config:
                print(f"✅ Configuration matches {provider}")
                
                # Provider-specific notes
                if provider == 'Gmail':
                    print("  📝 Note: Gmail requires App Password, not regular password")
                    print("  📝 Enable 2FA and generate App Password at: https://myaccount.google.com/apppasswords")
                elif provider == 'Outlook/Hotmail':
                    print("  📝 Note: May require enabling 'Less secure app access'")
                elif provider == 'Amazon SES':
                    print("  📝 Note: Requires SES SMTP credentials, not AWS root credentials")
                
                return True
        
        print(f"❌ Configuration {current_config} doesn't match common providers")
        return False

    def run_all_tests(self, test_email=None):
        """Run all SMTP tests in sequence"""
        print("Running complete SMTP test suite...")
        
        results = {}
        results['connectivity'] = self.test_1_basic_connectivity()
        results['handshake'] = self.test_2_smtp_handshake()
        results['starttls'] = self.test_3_starttls_support()
        results['auth'] = self.test_4_authentication()
        results['provider_check'] = self.test_6_common_configurations()
        
        if all([results['connectivity'], results['handshake'], results['auth']]):
            results['email_send'] = self.test_5_send_test_email(test_email)
        else:
            print("\n5. Skipping email test due to previous failures")
            results['email_send'] = False
        
        # Summary
        print("\n" + "=" * 50)
        print("SMTP TEST RESULTS SUMMARY")
        print("=" * 50)
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if results['auth'] and results['email_send']:
            print("🎉 SMTP configuration is fully functional!")
        elif results['auth']:
            print("⚠️  Authentication works, but email sending failed")
        elif results['connectivity']:
            print("⚠️  Can connect to server, but authentication failed")
        else:
            print("❌ Major connectivity issues detected")
        
        return results

def main():
    """Main function to run SMTP tests"""
    print("SMTP Configuration Tester")
    print("This tool will help diagnose SMTP connectivity issues\n")
    
    # Option 1: Use environment variables
    if all(os.getenv(var) for var in ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS']):
        print("Using SMTP configuration from environment variables...")
        tester = SMTPTester()
    else:
        # Option 2: Manual input
        print("Environment variables not found. Please enter SMTP details:")
        host = input("SMTP Host: ").strip()
        port = input("SMTP Port (default 587): ").strip() or "587"
        username = input("SMTP Username/Email: ").strip()
        password = input("SMTP Password: ").strip()
        
        tester = SMTPTester(host, port, username, password)
    
    # Ask for test email
    test_email = input("\nEnter email address for test message (or press Enter to skip): ").strip()
    if not test_email:
        test_email = None
    
    # Run tests
    results = tester.run_all_tests(test_email)
    
    # Troubleshooting tips
    if not all(results.values()):
        print("\n" + "=" * 50)
        print("TROUBLESHOOTING TIPS")
        print("=" * 50)
        
        if not results['connectivity']:
            print("• Check firewall settings")
            print("• Verify SMTP host and port are correct")
            print("• Try different port (25, 465, 587, 2525)")
        
        if not results['auth']:
            print("• Verify username and password are correct")
            print("• Check if 2FA is enabled (may need app password)")
            print("• Ensure account allows less secure apps (if required)")
        
        if not results['email_send']:
            print("• Check sender email reputation")
            print("• Verify recipient email is valid")
            print("• Check for rate limiting")

if __name__ == "__main__":
    main()
