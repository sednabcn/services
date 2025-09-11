#!/usr/bin/env python3
"""
Real Data Validator - Validates actual contact data and template content
"""

import os
import sys
import json
import csv
import requests
import pandas as pd
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

class RealDataValidator:
    def __init__(self, contacts_dir: str = "contacts", templates_dir: str = "campaign-templates"):
        self.contacts_dir = Path(contacts_dir)
        self.templates_dir = Path(templates_dir)
        self.logger = self._setup_logger()
        self.errors = []
        self.warnings = []
        self.validation_results = {}
        
    def _setup_logger(self):
        """Setup logging"""
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        return logging.getLogger(__name__)
    
    def validate_contact_files(self) -> Dict[str, Any]:
        """Validate actual contact file contents"""
        self.logger.info("Validating contact files...")
        
        contact_validation = {
            'files_processed': 0,
            'total_contacts': 0,
            'valid_emails': 0,
            'invalid_emails': 0,
            'missing_fields': [],
            'files_status': {}
        }
        
        if not self.contacts_dir.exists():
            self.errors.append("Contacts directory does not exist")
            return contact_validation
        
        # Process different file types
        for file_path in self.contacts_dir.glob('*'):
            if not file_path.is_file():
                continue
                
            self.logger.info(f"Validating contact file: {file_path.name}")
            file_status = {'valid': False, 'errors': [], 'contact_count': 0}
            
            try:
                if file_path.suffix.lower() == '.csv':
                    result = self._validate_csv_file(file_path)
                elif file_path.suffix.lower() == '.url':
                    result = self._validate_url_file(file_path)
                elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                    result = self._validate_excel_file(file_path)
                elif file_path.suffix.lower() == '.json':
                    result = self._validate_json_file(file_path)
                else:
                    self.warnings.append(f"Unsupported file type: {file_path.suffix}")
                    continue
                
                file_status.update(result)
                contact_validation['files_status'][file_path.name] = file_status
                contact_validation['files_processed'] += 1
                contact_validation['total_contacts'] += file_status.get('contact_count', 0)
                contact_validation['valid_emails'] += file_status.get('valid_emails', 0)
                contact_validation['invalid_emails'] += file_status.get('invalid_emails', 0)
                
            except Exception as e:
                error_msg = f"Failed to validate {file_path.name}: {e}"
                self.errors.append(error_msg)
                file_status['errors'].append(error_msg)
                contact_validation['files_status'][file_path.name] = file_status
        
        return contact_validation
    
    def _validate_csv_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate CSV contact file"""
        result = {'valid': False, 'errors': [], 'contact_count': 0, 'valid_emails': 0, 'invalid_emails': 0}
        
        try:
            # Read CSV with pandas for better handling
            df = pd.read_csv(file_path)
            result['contact_count'] = len(df)
            
            # Check for required columns
            required_columns = ['email']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                result['errors'].append(f"Missing required columns: {missing_columns}")
                return result
            
            # Validate email addresses
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            import re
            
            for idx, email in enumerate(df['email']):
                if pd.isna(email) or not isinstance(email, str):
                    result['invalid_emails'] += 1
                    result['errors'].append(f"Row {idx+1}: Invalid email format (empty/non-string)")
                elif not re.match(email_pattern, email.strip()):
                    result['invalid_emails'] += 1
                    result['errors'].append(f"Row {idx+1}: Invalid email format: {email}")
                else:
                    result['valid_emails'] += 1
            
            # Check for other useful columns
            recommended_columns = ['name', 'company', 'title', 'phone']
            missing_recommended = [col for col in recommended_columns if col not in df.columns]
            if missing_recommended:
                self.warnings.append(f"{file_path.name}: Missing recommended columns: {missing_recommended}")
            
            result['valid'] = result['invalid_emails'] == 0
            self.logger.info(f"{file_path.name}: {result['valid_emails']} valid, {result['invalid_emails']} invalid emails")
            
        except Exception as e:
            result['errors'].append(f"CSV parsing error: {e}")
        
        return result
    
    def _validate_url_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate URL file (Google Sheets, web URLs)"""
        result = {'valid': False, 'errors': [], 'contact_count': 0, 'valid_emails': 0, 'invalid_emails': 0}
        
        try:
            with open(file_path, 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not urls:
                result['errors'].append("No valid URLs found in file")
                return result
            
            for url in urls:
                if 'docs.google.com' in url or 'sheets.google.com' in url:
                    # Google Sheets validation - just check if URL is accessible
                    self.logger.info(f"Found Google Sheets URL: {url}")
                    result['contact_count'] += 1  # Estimate
                    result['valid_emails'] += 1   # Assume valid for now
                    self.warnings.append(f"Google Sheets URL found - cannot validate content without access: {url}")
                else:
                    # Try to fetch and validate web URL
                    try:
                        response = requests.head(url, timeout=10)
                        if response.status_code == 200:
                            result['contact_count'] += 1
                            result['valid_emails'] += 1
                            self.logger.info(f"URL accessible: {url}")
                        else:
                            result['errors'].append(f"URL not accessible (status {response.status_code}): {url}")
                            result['invalid_emails'] += 1
                    except Exception as e:
                        result['errors'].append(f"URL validation failed for {url}: {e}")
                        result['invalid_emails'] += 1
            
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"URL file parsing error: {e}")
        
        return result
    
    def _validate_excel_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate Excel contact file"""
        result = {'valid': False, 'errors': [], 'contact_count': 0, 'valid_emails': 0, 'invalid_emails': 0}
        
        try:
            df = pd.read_excel(file_path)
            result['contact_count'] = len(df)
            
            # Similar validation as CSV
            if 'email' not in df.columns:
                result['errors'].append("Missing 'email' column")
                return result
            
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            for idx, email in enumerate(df['email']):
                if pd.isna(email) or not isinstance(email, str):
                    result['invalid_emails'] += 1
                elif not re.match(email_pattern, email.strip()):
                    result['invalid_emails'] += 1
                else:
                    result['valid_emails'] += 1
            
            result['valid'] = result['invalid_emails'] == 0
            self.logger.info(f"{file_path.name}: {result['valid_emails']} valid, {result['invalid_emails']} invalid emails")
            
        except Exception as e:
            result['errors'].append(f"Excel parsing error: {e}")
        
        return result
    
    def _validate_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate JSON contact file"""
        result = {'valid': False, 'errors': [], 'contact_count': 0, 'valid_emails': 0, 'invalid_emails': 0}
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                contacts = data
            else:
                contacts = [data]
            
            result['contact_count'] = len(contacts)
            
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            for idx, contact in enumerate(contacts):
                if not isinstance(contact, dict):
                    result['errors'].append(f"Contact {idx}: Not a dictionary object")
                    result['invalid_emails'] += 1
                    continue
                
                email = contact.get('email')
                if not email or not isinstance(email, str):
                    result['invalid_emails'] += 1
                    result['errors'].append(f"Contact {idx}: Missing or invalid email")
                elif not re.match(email_pattern, email.strip()):
                    result['invalid_emails'] += 1
                    result['errors'].append(f"Contact {idx}: Invalid email format: {email}")
                else:
                    result['valid_emails'] += 1
            
            result['valid'] = result['invalid_emails'] == 0
            self.logger.info(f"{file_path.name}: {result['valid_emails']} valid, {result['invalid_emails']} invalid emails")
            
        except Exception as e:
            result['errors'].append(f"JSON parsing error: {e}")
        
        return result
    
    def validate_template_files(self) -> Dict[str, Any]:
        """Validate template files"""
        self.logger.info("Validating template files...")
        
        template_validation = {
            'domains_processed': 0,
            'templates_found': 0,
            'templates_accessible': 0,
            'domains_status': {}
        }
        
        if not self.templates_dir.exists():
            self.errors.append("Templates directory does not exist")
            return template_validation
        
        # Check domain directories
        domains = ['education', 'finance', 'healthcare', 'industry', 'technology', 'government']
        
        for domain in domains:
            domain_path = self.templates_dir / domain
            domain_status = {'exists': False, 'templates': [], 'accessible_templates': 0}
            
            if domain_path.exists() and domain_path.is_dir():
                domain_status['exists'] = True
                templates = list(domain_path.glob('*.docx')) + list(domain_path.glob('*.doc'))
                
                for template in templates:
                    template_info = {
                        'name': template.name,
                        'size_mb': round(template.stat().st_size / (1024*1024), 2),
                        'accessible': template.is_file()
                    }
                    
                    domain_status['templates'].append(template_info)
                    if template_info['accessible']:
                        domain_status['accessible_templates'] += 1
                
                template_validation['templates_found'] += len(templates)
                template_validation['templates_accessible'] += domain_status['accessible_templates']
                
                self.logger.info(f"{domain}: {len(templates)} templates, {domain_status['accessible_templates']} accessible")
            else:
                self.warnings.append(f"Domain directory not found: {domain}")
            
            template_validation['domains_status'][domain] = domain_status
            template_validation['domains_processed'] += 1
        
        return template_validation
    
    def validate_data_consistency(self) -> Dict[str, Any]:
        """Check for data consistency issues"""
        self.logger.info("Checking data consistency...")
        
        consistency_check = {
            'duplicate_emails_found': 0,
            'cross_file_duplicates': [],
            'encoding_issues': [],
            'format_inconsistencies': []
        }
        
        # Collect all emails from all files
        all_emails = {}  # email -> [file1, file2, ...]
        
        for file_path in self.contacts_dir.glob('*'):
            if not file_path.is_file() or file_path.suffix.lower() not in ['.csv', '.xlsx', '.json']:
                continue
            
            try:
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path)
                    if 'email' in df.columns:
                        emails = df['email'].dropna().tolist()
                elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                    df = pd.read_excel(file_path)
                    if 'email' in df.columns:
                        emails = df['email'].dropna().tolist()
                elif file_path.suffix.lower() == '.json':
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        emails = [contact.get('email') for contact in data if contact.get('email')]
                    else:
                        emails = [data.get('email')] if data.get('email') else []
                else:
                    continue
                
                # Track emails by file
                for email in emails:
                    if email and isinstance(email, str):
                        email = email.strip().lower()
                        if email not in all_emails:
                            all_emails[email] = []
                        all_emails[email].append(file_path.name)
                        
            except Exception as e:
                self.errors.append(f"Error reading {file_path.name} for consistency check: {e}")
        
        # Find duplicates
        for email, files in all_emails.items():
            if len(files) > 1:
                consistency_check['duplicate_emails_found'] += 1
                consistency_check['cross_file_duplicates'].append({
                    'email': email,
                    'found_in_files': files
                })
        
        return consistency_check
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        self.logger.info("Generating validation report...")
        
        contacts_result = self.validate_contact_files()
        templates_result = self.validate_template_files()
        consistency_result = self.validate_data_consistency()
        
        report = {
            'validation_timestamp': pd.Timestamp.now().isoformat(),
            'overall_status': 'PASS' if len(self.errors) == 0 else 'FAIL',
            'contacts_validation': contacts_result,
            'templates_validation': templates_result,
            'data_consistency': consistency_result,
            'errors': self.errors,
            'warnings': self.warnings,
            'summary': {
                'total_contact_files': contacts_result['files_processed'],
                'total_contacts': contacts_result['total_contacts'],
                'valid_emails': contacts_result['valid_emails'],
                'invalid_emails': contacts_result['invalid_emails'],
                'email_validation_rate': (
                    contacts_result['valid_emails'] / max(contacts_result['total_contacts'], 1)
                ) * 100,
                'template_domains': templates_result['domains_processed'],
                'total_templates': templates_result['templates_found'],
                'accessible_templates': templates_result['templates_accessible'],
                'duplicate_emails': consistency_result['duplicate_emails_found']
            }
        }
        
        return report
    
    def print_validation_report(self, report: Dict[str, Any]) -> bool:
        """Print human-readable validation report"""
        print("=" * 70)
        print("REAL DATA VALIDATION REPORT")
        print("=" * 70)
        print(f"Status: {report['overall_status']}")
        print(f"Validation Time: {report['validation_timestamp']}")
        print()
        
        # Summary
        summary = report['summary']
        print("SUMMARY:")
        print(f"  Contact Files: {summary['total_contact_files']}")
        print(f"  Total Contacts: {summary['total_contacts']}")
        print(f"  Valid Emails: {summary['valid_emails']} ({summary['email_validation_rate']:.1f}%)")
        print(f"  Invalid Emails: {summary['invalid_emails']}")
        print(f"  Template Domains: {summary['template_domains']}")
        print(f"  Total Templates: {summary['total_templates']}")
        print(f"  Accessible Templates: {summary['accessible_templates']}")
        print(f"  Duplicate Emails: {summary['duplicate_emails']}")
        print()
        
        # Errors
        if report['errors']:
            print("ERRORS:")
            for error in report['errors']:
                print(f"  • {error}")
            print()
        
        # Warnings
        if report['warnings']:
            print("WARNINGS:")
            for warning in report['warnings']:
                print(f"  • {warning}")
            print()
        
        # Contact files details
        print("CONTACT FILES VALIDATION:")
        for filename, status in report['contacts_validation']['files_status'].items():
            status_icon = "✅" if status['valid'] else "❌"
            print(f"  {status_icon} {filename}: {status.get('contact_count', 0)} contacts")
            if status['errors']:
                for error in status['errors'][:3]:  # Show first 3 errors
                    print(f"      • {error}")
                if len(status['errors']) > 3:
                    print(f"      • ... and {len(status['errors']) - 3} more errors")
        print()
        
        # Template domains details
        print("TEMPLATE DOMAINS:")
        for domain, status in report['templates_validation']['domains_status'].items():
            status_icon = "✅" if status['exists'] else "❌"
            template_count = len(status['templates'])
            print(f"  {status_icon} {domain}: {template_count} templates")
            for template in status['templates']:
                accessible_icon = "✅" if template['accessible'] else "❌"
                print(f"      {accessible_icon} {template['name']} ({template['size_mb']} MB)")
        
        return report['overall_status'] == 'PASS'

def main():
    parser = argparse.ArgumentParser(description="Validate real contact and template data")
    parser.add_argument("--contacts", default="contacts", help="Contacts directory path")
    parser.add_argument("--templates", default="campaign-templates", help="Templates directory path")
    parser.add_argument("--json-output", action="store_true", help="Output JSON report")
    parser.add_argument("--output-file", help="Save report to file")
    parser.add_argument("--strict", action="store_true", help="Fail on any warnings")
    
    args = parser.parse_args()
    
    validator = RealDataValidator(args.contacts, args.templates)
    report = validator.generate_validation_report()
    
    if args.json_output:
        output = json.dumps(report, indent=2)
        print(output)
    else:
        success = validator.print_validation_report(report)
        
        if args.strict and report['warnings']:
            print("STRICT MODE: Failing due to warnings")
            success = False
        
        sys.exit(0 if success else 1)
    
    if args.output_file:
        with open(args.output_file, 'w') as f:
            if args.json_output:
                json.dump(report, f, indent=2)
            else:
                f.write("Real Data Validation Report\n")
                f.write("=" * 50 + "\n")
                f.write(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
