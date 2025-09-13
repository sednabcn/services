#!/usr/bin/env python3
"""
Email validation and verification system for campaign execution.
Validates email addresses, checks deliverability, and manages bounce handling.
"""

import re
import dns.resolver
import smtplib
import socket
import json
import csv
from datetime import datetime
from pathlib import Path
import argparse
import sys


class EmailValidator:
    """Comprehensive email validation and verification system."""
    
    def __init__(self, verification_level='basic'):
        self.verification_level = verification_level
        self.validation_stats = {
            'total_emails': 0,
            'valid_format': 0,
            'invalid_format': 0,
            'domain_valid': 0,
            'domain_invalid': 0,
            'mx_record_found': 0,
            'mx_record_missing': 0,
            'smtp_verified': 0,
            'smtp_failed': 0,
            'bounce_risk_high': 0,
            'bounce_risk_low': 0
        }
        
        # Common disposable email domains
        self.disposable_domains = {
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email', 'temp-mail.org'
        }
        
        # Common typos in email domains
        self.domain_corrections = {
            'gmai.com': 'gmail.com',
            'gmial.com': 'gmail.com',
            'yahooo.com': 'yahoo.com',
            'hotmial.com': 'hotmail.com',
            'outlok.com': 'outlook.com'
        }
    
    def validate_email_format(self, email):
        """Validate email format using regex."""
        if not email or not isinstance(email, str):
            return False, "Email is empty or not a string"
        
        email = email.strip().lower()
        
        # Basic format validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"
        
        # Check for consecutive dots
        if '..' in email:
            return False, "Consecutive dots not allowed"
        
        # Check email length
        if len(email) > 254:
            return False, "Email too long"
        
        local_part, domain = email.split('@')
        
        # Validate local part
        if len(local_part) > 64:
            return False, "Local part too long"
        
        if local_part.startswith('.') or local_part.endswith('.'):
            return False, "Local part cannot start or end with dot"
        
        # Validate domain
        if len(domain) > 253:
            return False, "Domain too long"
        
        return True, "Valid format"
    
    def suggest_email_correction(self, email):
        """Suggest corrections for common email typos."""
        if '@' not in email:
            return None
        
        local_part, domain = email.split('@', 1)
        
        if domain in self.domain_corrections:
            corrected_email = f"{local_part}@{self.domain_corrections[domain]}"
            return corrected_email
        
        return None
    
    def check_disposable_email(self, email):
        """Check if email is from a disposable email service."""
        if '@' not in email:
            return False
        
        domain = email.split('@')[1].lower()
        return domain in self.disposable_domains
    
    def validate_domain_mx(self, domain):
        """Check if domain has valid MX records."""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return True, len(mx_records), [str(record) for record in mx_records]
        except dns.resolver.NXDOMAIN:
            return False, 0, "Domain does not exist"
        except dns.resolver.NoAnswer:
            return False, 0, "No MX records found"
        except Exception as e:
            return False, 0, f"DNS error: {str(e)}"
    
    def verify_smtp_deliverability(self, email, timeout=10):
        """Verify email deliverability via SMTP (basic check)."""
        if '@' not in email:
            return False, "Invalid email format"
        
        local_part, domain = email.split('@')
        
        try:
            # Get MX record
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_record = str(mx_records[0]).split()[-1].rstrip('.')
            
            # Connect to SMTP server
            with socket.create_connection((mx_record, 25), timeout=timeout) as sock:
                with smtplib.SMTP() as server:
                    server.sock = sock
                    server.ehlo()
                    
                    # Try to verify the email address
                    code, message = server.vrfy(email)
                    
                    if code == 250:
                        return True, "Email address verified"
                    else:
                        return False, f"SMTP verification failed: {message}"
        
        except Exception as e:
            return False, f"SMTP verification error: {str(e)}"
    
    def calculate_bounce_risk(self, email_data):
        """Calculate bounce risk based on various factors."""
        risk_score = 0
        risk_factors = []
        
        email = email_data.get('email', '')
        
        # Format validation
        if not email_data.get('format_valid', False):
            risk_score += 50
            risk_factors.append('Invalid format')
        
        # Domain validation
        if not email_data.get('domain_valid', False):
            risk_score += 40
            risk_factors.append('Invalid domain')
        
        # MX record check
        if not email_data.get('mx_valid', False):
            risk_score += 30
            risk_factors.append('No MX records')
        
        # Disposable email check
        if email_data.get('is_disposable', False):
            risk_score += 25
            risk_factors.append('Disposable email')
        
        # SMTP verification
        if not email_data.get('smtp_verified', False):
            risk_score += 20
            risk_factors.append('SMTP verification failed')
        
        # Common patterns that increase risk
        if email.count('.') > 3:
            risk_score += 10
            risk_factors.append('Many dots in email')
        
        if len(email.split('@')[0]) < 3:
            risk_score += 5
            risk_factors.append('Very short local part')
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = 'HIGH'
        elif risk_score >= 40:
            risk_level = 'MEDIUM'
        elif risk_score >= 15:
            risk_level = 'LOW'
        else:
            risk_level = 'VERY_LOW'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors
        }
    
    def validate_single_email(self, email):
        """Perform comprehensive validation on a single email."""
        validation_result = {
            'email': email,
            'timestamp': datetime.now().isoformat(),
            'format_valid': False,
            'format_message': '',
            'suggested_correction': None,
            'is_disposable': False,
            'domain_valid': False,
            'mx_valid': False,
            'mx_count': 0,
            'mx_records': [],
            'smtp_verified': False,
            'smtp_message': '',
            'bounce_risk': {}
        }
        
        # Format validation
        format_valid, format_message = self.validate_email_format(email)
        validation_result['format_valid'] = format_valid
        validation_result['format_message'] = format_message
        
        if format_valid:
            self.validation_stats['valid_format'] += 1
            
            # Check for typo corrections
            correction = self.suggest_email_correction(email)
            if correction:
                validation_result['suggested_correction'] = correction
            
            # Check disposable email
            validation_result['is_disposable'] = self.check_disposable_email(email)
            
            # Domain validation
            domain = email.split('@')[1]
            if self.verification_level in ['advanced', 'full']:
                mx_valid, mx_count, mx_records = self.validate_domain_mx(domain)
                validation_result['domain_valid'] = mx_valid
                validation_result['mx_valid'] = mx_valid
                validation_result['mx_count'] = mx_count
                validation_result['mx_records'] = mx_records if isinstance(mx_records, list) else []
                
                if mx_valid:
                    self.validation_stats['domain_valid'] += 1
                    self.validation_stats['mx_record_found'] += 1
                else:
                    self.validation_stats['domain_invalid'] += 1
                    self.validation_stats['mx_record_missing'] += 1
            
            # SMTP verification (only for full verification)
            if self.verification_level == 'full':
                smtp_valid, smtp_message = self.verify_smtp_deliverability(email)
                validation_result['smtp_verified'] = smtp_valid
                validation_result['smtp_message'] = smtp_message
                
                if smtp_valid:
                    self.validation_stats['smtp_verified'] += 1
                else:
                    self.validation_stats['smtp_failed'] += 1
        else:
            self.validation_stats['invalid_format'] += 1
        
        # Calculate bounce risk
        validation_result['bounce_risk'] = self.calculate_bounce_risk(validation_result)
        
        if validation_result['bounce_risk']['risk_level'] in ['HIGH', 'MEDIUM']:
            self.validation_stats['bounce_risk_high'] += 1
        else:
            self.validation_stats['bounce_risk_low'] += 1
        
        self.validation_stats['total_emails'] += 1
        
        return validation_result
    
    def validate_email_list(self, emails, progress_callback=None):
        """Validate a list of emails with optional progress callback."""
        results = []
        total = len(emails)
        
        for i, email in enumerate(emails):
            result = self.validate_single_email(email)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, total, email, result)
        
        return results
    
    def validate_csv_file(self, csv_file, email_column='email'):
        """Validate emails from a CSV file."""
        results = []
        
        try:
            with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    email = row.get(email_column, '').strip()
                    if email:
                        result = self.validate_single_email(email)
                        result['row_number'] = row_num
                        result['original_data'] = row
                        results.append(result)
        
        except Exception as e:
            print(f"Error reading CSV file {csv_file}: {e}")
        
        return results
    
    def generate_validation_report(self, results, output_file=None):
        """Generate comprehensive validation report."""
        report = {
            'validation_summary': {
                'timestamp': datetime.now().isoformat(),
                'verification_level': self.verification_level,
                'statistics': self.validation_stats.copy(),
                'total_processed': len(results)
            },
            'recommendations': [],
            'high_risk_emails': [],
            'suggested_corrections': [],
            'disposable_emails': []
        }
        
        # Analyze results
        for result in results:
            # High risk emails
            if result['bounce_risk']['risk_level'] in ['HIGH', 'MEDIUM']:
                report['high_risk_emails'].append({
                    'email': result['email'],
                    'risk_level': result['bounce_risk']['risk_level'],
                    'risk_score': result['bounce_risk']['risk_score'],
                    'risk_factors': result['bounce_risk']['risk_factors']
                })
            
            # Suggested corrections
            if result.get('suggested_correction'):
                report['suggested_corrections'].append({
                    'original': result['email'],
                    'suggested': result['suggested_correction']
                })
            
            # Disposable emails
            if result.get('is_disposable'):
                report['disposable_emails'].append(result['email'])
        
        # Generate recommendations
        invalid_rate = (self.validation_stats['invalid_format'] / self.validation_stats['total_emails']) * 100
        high_risk_rate = (self.validation_stats['bounce_risk_high'] / self.validation_stats['total_emails']) * 100
        
        if invalid_rate > 10:
            report['recommendations'].append(f"High invalid email rate ({invalid_rate:.1f}%). Review data collection process.")
        
        if high_risk_rate > 20:
            report['recommendations'].append(f"High bounce risk rate ({high_risk_rate:.1f}%). Consider email verification service.")
        
        if len(report['suggested_corrections']) > 0:
            report['recommendations'].append(f"Found {len(report['suggested_corrections'])} potential typos. Review corrections.")
        
        if len(report['disposable_emails']) > 0:
            report['recommendations'].append(f"Found {len(report['disposable_emails'])} disposable emails. Consider filtering.")
        
        # Save report if output file specified
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"Validation report saved to: {output_file}")
            except Exception as e:
                print(f"Error saving report: {e}")
        
        return report
    
    def print_validation_summary(self):
        """Print validation statistics summary."""
        print("\n" + "="*50)
        print("EMAIL VALIDATION SUMMARY")
        print("="*50)
        print(f"Total emails processed: {self.validation_stats['total_emails']}")
        print(f"Valid format: {self.validation_stats['valid_format']} ({self.validation_stats['valid_format']/self.validation_stats['total_emails']*100:.1f}%)")
        print(f"Invalid format: {self.validation_stats['invalid_format']} ({self.validation_stats['invalid_format']/self.validation_stats['total_emails']*100:.1f}%)")
        
        if self.verification_level in ['advanced', 'full']:
            print(f"Valid domains: {self.validation_stats['domain_valid']}")
            print(f"Invalid domains: {self.validation_stats['domain_invalid']}")
            print(f"MX records found: {self.validation_stats['mx_record_found']}")
        
        if self.verification_level == 'full':
            print(f"SMTP verified: {self.validation_stats['smtp_verified']}")
            print(f"SMTP failed: {self.validation_stats['smtp_failed']}")
        
        print(f"High bounce risk: {self.validation_stats['bounce_risk_high']}")
        print(f"Low bounce risk: {self.validation_stats['bounce_risk_low']}")
        print("="*50)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Email Validation System')
    parser.add_argument('--input', required=True, help='Input CSV file or single email')
    parser.add_argument('--output', help='Output file for validation report')
    parser.add_argument('--email-column', default='email', help='CSV column name for emails')
    parser.add_argument('--level', choices=['basic', 'advanced', 'full'], default='advanced',
                       help='Validation level (basic, advanced, full)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    validator = EmailValidator(verification_level=args.level)
    
    # Check if input is a file or single email
    if Path(args.input).exists():
        print(f"Validating emails from CSV file: {args.input}")
        results = validator.validate_csv_file(args.input, args.email_column)
    elif '@' in args.input:
        print(f"Validating single email: {args.input}")
        result = validator.validate_single_email(args.input)
        results = [result]
    else:
        print(f"Invalid input: {args.input}")
        return 1
    
    # Generate report
    output_file = args.output or f"email_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = validator.generate_validation_report(results, output_file)
    
    # Print summary
    validator.print_validation_summary()
    
    if args.verbose:
        print("\nDETAILED RESULTS:")
        for result in results:
            print(f"\nEmail: {result['email']}")
            print(f"  Format valid: {result['format_valid']}")
            print(f"  Bounce risk: {result['bounce_risk']['risk_level']} ({result['bounce_risk']['risk_score']})")
            if result['bounce_risk']['risk_factors']:
                print(f"  Risk factors: {', '.join(result['bounce_risk']['risk_factors'])}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
