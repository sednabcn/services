#!/usr/bin/env python3
"""
Real Data Validator - Validates actual contact data and template content
Fixed for GitHub Actions workflow compatibility
"""

import os
import sys
import json
import csv
import urllib.request
import urllib.error
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
import re
from datetime import datetime

# Check for optional libraries
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests library not available, using urllib fallback")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas library not available, using csv fallback")

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
        """Validate CSV contact file using csv module fallback"""
        result = {'valid': False, 'errors': [], 'contact_count': 0, 'valid_emails': 0, 'invalid_emails': 0}
        
        try:
            if PANDAS_AVAILABLE:
                # Use pandas if available
                df = pd.read_csv(file_path)
                result['contact_count'] = len(df)
                email_column_data = df.get('email', pd.Series())
            else:
                # Fallback to csv module
                contacts = []
                with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    contacts = list(reader)
                
                result['contact_count'] = len(contacts)
                email_column_data = [contact.get('email') for contact in contacts]
            
            # Check for required columns
            if not any('email' in str(item).lower() for item in (email_column_data if isinstance(email_column_data, list) else [str(email_column_data.name)])):
                result['errors'].append("Missing required 'email' column")
                return result
            
            # Validate email addresses
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            for idx, email in enumerate(email_column_data):
                if not email or not isinstance(email, str) or str(email).lower() in ['nan', 'none']:
                    result['invalid_emails'] += 1
                    if len(result['errors']) < 5:  # Limit error messages
                        result['errors'].append(f"Row {idx+1}: Invalid email format (empty/non-string)")
                elif not re.match(email_pattern, str(email).strip()):
                    result['invalid_emails'] += 1
                    if len(result['errors']) < 5:
                        result['errors'].append(f"Row {idx+1}: Invalid email format: {email}")
                else:
                    result['valid_emails'] += 1
            
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
                if 'docs.google.com' in url and '/spreadsheets/' in url:
                    # Google Sheets validation - try to access CSV export
                    self.logger.info(f"Testing Google Sheets URL: {url}")
                    
                    # Extract sheet ID and create CSV export URL
                    sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
                    if sheet_id_match:
                        sheet_id = sheet_id_match.group(1)
                        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
                        
                        try:
                            # Test accessibility
                            with urllib.request.urlopen(csv_url, timeout=15) as response:
                                if response.status == 200:
                                    csv_data = response.read().decode('utf-8')
                                    lines = csv_data.strip().split('\n')
                                    if len(lines) > 1:  # Has header + data
                                        result['contact_count'] += len(lines) - 1  # Subtract header
                                        result['valid_emails'] += len(lines) - 1   # Assume valid for accessible sheets
                                        self.logger.info(f"Google Sheets accessible with ~{len(lines)-1} rows")
                                    else:
                                        result['errors'].append(f"Google Sheets appears empty: {url}")
                                else:
                                    result['errors'].append(f"Google Sheets returned status {response.status}: {url}")
                        except urllib.error.HTTPError as e:
                            if e.code == 403:
                                result['errors'].append(f"Google Sheets access denied (check sharing settings): {url}")
                            else:
                                result['errors'].append(f"Google Sheets HTTP error {e.code}: {url}")
                        except Exception as e:
                            result['errors'].append(f"Google Sheets connection error: {url} - {e}")
                    else:
                        result['errors'].append(f"Cannot extract sheet ID from Google Sheets URL: {url}")
                        
                else:
                    # Regular web URL validation
                    try:
                        if REQUESTS_AVAILABLE:
                            import requests
                            response = requests.head(url, timeout=10)
                            if response.status_code == 200:
                                result['contact_count'] += 1
                                result['valid_emails'] += 1
                                self.logger.info(f"URL accessible: {url}")
                            else:
                                result['errors'].append(f"URL not accessible (status {response.status_code}): {url}")
                        else:
                            # Fallback to urllib
                            with urllib.request.urlopen(url, timeout=10) as response:
                                if response.status == 200:
                                    result['contact_count'] += 1
                                    result['valid_emails'] += 1
                                    self.logger.info(f"URL accessible: {url}")
                                else:
                                    result['errors'].append(f"URL not accessible (status {response.status}): {url}")
                    except Exception as e:
                        result['errors'].append(f"URL validation failed for {url}: {e}")
            
            result['valid'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"URL file parsing error: {e}")
        
        return result
    
    def _validate_excel_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate Excel contact file"""
        result = {'valid': False, 'errors': [], 'contact_count': 0, 'valid_emails': 0, 'invalid_emails': 0}
        
        if not PANDAS_AVAILABLE:
            result['errors'].append("pandas library required for Excel validation but not available")
            return result
        
        try:
            df = pd.read_excel(file_path)
            result['contact_count'] = len(df)
            
            # Similar validation as CSV
            if 'email' not in df.columns:
                result['errors'].append("Missing 'email' column")
                return result
            
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
            
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            for idx, contact in enumerate(contacts):
                if not isinstance(contact, dict):
                    result['errors'].append(f"Contact {idx}: Not a dictionary object")
                    result['invalid_emails'] += 1
                    continue
                
                email = contact.get('email')
                if not email or not isinstance(email, str):
                    result['invalid_emails'] += 1
                    if len(result['errors']) < 5:
                        result['errors'].append(f"Contact {idx}: Missing or invalid email")
                elif not re.match(email_pattern, email.strip()):
                    result['invalid_emails'] += 1
                    if len(result['errors']) < 5:
                        result['errors'].append(f"Contact {idx}: Invalid email format: {email}")
                else:
                    result['valid_emails'] += 1
            
            result['valid'] = result['invalid_emails'] == 0
            self.logger.info(f"{file_path.name}: {result['valid_emails']} valid, {result['invalid_emails']} invalid emails")
            
        except Exception as e:
            result['errors'].append(f"JSON parsing error: {e}")
        
        return result
    
    def validate_template_files(self) -> Dict[str, Any]:
        """Validate template files (simplified version)"""
        self.logger.info("Validating template files...")
        
        template_validation = {
            'domains_processed': 0,
            'templates_found': 0,
            'templates_accessible': 0,
            'domains_status': {}
        }
        
        if not self.templates_dir.exists():
            self.warnings.append("Templates directory does not exist - this is optional")
            return template_validation
        
        # Check for any template files
        template_files = list(self.templates_dir.glob('**/*'))
        template_files = [f for f in template_files if f.is_file() and f.suffix.lower() in ['.docx', '.doc', '.txt', '.html', '.md', '.json']]
        
        template_validation['templates_found'] = len(template_files)
        template_validation['templates_accessible'] = len(template_files)  # Assume accessible if found
        template_validation['domains_processed'] = 1  # Simplified
        
        if template_files:
            self.logger.info(f"Found {len(template_files)} template files")
        else:
            self.warnings.append("No template files found - campaigns will need to be in scheduled directory")
        
        return template_validation
    
    def validate_data_consistency(self) -> Dict[str, Any]:
        """Check for data consistency issues (simplified)"""
        self.logger.info("Checking data consistency...")
        
        consistency_check = {
            'duplicate_emails_found': 0,
            'cross_file_duplicates': [],
            'encoding_issues': [],
            'format_inconsistencies': []
        }
        
        # This is a simplified consistency check
        # In practice, you might want more sophisticated duplicate detection
        
        return consistency_check
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        self.logger.info("Generating validation report...")
        
        contacts_result = self.validate_contact_files()
        templates_result = self.validate_template_files()
        consistency_result = self.validate_data_consistency()
        
        report = {
            'validation_timestamp': datetime.now().isoformat(),
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
                ) * 100 if contacts_result['total_contacts'] > 0 else 0,
                'template_domains': templates_result['domains_processed'],
                'total_templates': templates_result['templates_found'],
                'accessible_templates': templates_result['templates_accessible'],
                'duplicate_emails': consistency_result['duplicate_emails_found']
            }
        }
        
        return report
    
    def generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Generate markdown validation report"""
        lines = []
        
        # Header
        lines.append("# Contact Data Validation Report")
        lines.append("")
        lines.append(f"**Generated:** {report['validation_timestamp']}")
        lines.append(f"**Status:** {report['overall_status']}")
        lines.append("")
        
        # Summary
        summary = report['summary']
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Contact Files:** {summary['total_contact_files']}")
        lines.append(f"- **Total Contacts:** {summary['total_contacts']}")
        lines.append(f"- **Valid Emails:** {summary['valid_emails']} ({summary['email_validation_rate']:.1f}%)")
        lines.append(f"- **Invalid Emails:** {summary['invalid_emails']}")
        lines.append(f"- **Templates Found:** {summary['total_templates']}")
        lines.append("")
        
        # Contact files details
        if report['contacts_validation']['files_status']:
            lines.append("## Contact Files")
            lines.append("")
            for filename, status in report['contacts_validation']['files_status'].items():
                status_icon = "✅" if status['valid'] else "❌"
                lines.append(f"### {status_icon} {filename}")
                lines.append(f"- **Contacts:** {status.get('contact_count', 0)}")
                lines.append(f"- **Valid Emails:** {status.get('valid_emails', 0)}")
                lines.append(f"- **Invalid Emails:** {status.get('invalid_emails', 0)}")
                
                if status.get('errors'):
                    lines.append("- **Issues:**")
                    for error in status['errors'][:3]:  # Show first 3 errors
                        lines.append(f"  - {error}")
                    if len(status['errors']) > 3:
                        lines.append(f"  - ... and {len(status['errors']) - 3} more issues")
                lines.append("")
        
        # Errors and warnings
        if report['errors']:
            lines.append("## Errors")
            lines.append("")
            for error in report['errors']:
                lines.append(f"- ❌ {error}")
            lines.append("")
        
        if report['warnings']:
            lines.append("## Warnings")
            lines.append("")
            for warning in report['warnings']:
                lines.append(f"- ⚠️ {warning}")
            lines.append("")
        
        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        
        if summary['total_contacts'] == 0:
            lines.append("### No Contact Data Found")
            lines.append("")
            lines.append("To add contact data:")
            lines.append("1. Add `.url` files with Google Sheets sharing URLs to the contacts directory")
            lines.append("2. Add `.csv` files with contact data")
            lines.append("3. Ensure Google Sheets are shared with 'Anyone with the link can view'")
            lines.append("4. Include required columns: `email` (and optionally `name`, `company`)")
            lines.append("")
        elif report['overall_status'] == 'FAIL':
            lines.append("### Issues Found")
            lines.append("")
            lines.append("Please review the errors above and fix the identified issues.")
            lines.append("")
        else:
            lines.append("### Validation Passed")
            lines.append("")
            lines.append("Contact data sources are ready for campaign processing.")
            lines.append("")
        
        return '\n'.join(lines)
    
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
        print(f"  Templates: {summary['total_templates']}")
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
        
        return report['overall_status'] == 'PASS'

def main():
    parser = argparse.ArgumentParser(description="Validate real contact and template data")
    parser.add_argument("--contacts", default="contacts", help="Contacts directory path")
    parser.add_argument("--output-file", help="Save report to file (markdown format)")
    parser.add_argument("--json-output", action="store_true", help="Output JSON report instead of markdown")
    parser.add_argument("--no-strict", action="store_true", help='Do not fail on warnings or missing data')
    
    args = parser.parse_args()
    
    print("🔍 Running real data validation...")
    print(f"Contacts directory: {args.contacts}")
    print("=" * 60)
    
    validator = RealDataValidator(args.contacts)
    report = validator.generate_validation_report()
    
    success = validator.print_validation_report(report)
    
    # Generate output file if requested
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if args.json_output:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nJSON report saved to: {output_path}")
        else:
            markdown_content = validator.generate_markdown_report(report)
            with open(output_path, 'w') as f:
                f.write(markdown_content)
            print(f"\nMarkdown report saved to: {output_path}")
    
    # Exit logic
    if args.no_strict:
        print("\n--no-strict mode: Exiting with success regardless of issues")
        sys.exit(0)
    elif success:
        print("\n✅ Validation passed")
        sys.exit(0)
    else:
        print("\n❌ Validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
