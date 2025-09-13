#!/usr/bin/env python3
"""
Enhanced fallback execution system for email campaigns.
Provides comprehensive campaign execution when main processor is unavailable.
"""

import sys
import os
import json
import pandas as pd
import glob
import time
import argparse
import re
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib


class EnhancedCampaignExecutor:
    """Enhanced campaign executor with comprehensive features."""
    
    def __init__(self, args):
        self.args = args
        self.contacts = []
        self.templates = []
        self.execution_stats = {
            'start_time': datetime.now(),
            'contacts_processed': 0,
            'emails_sent': 0,
            'personalizations_made': 0,
            'errors': 0,
            'warnings': 0
        }
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration."""
        self.log_messages = []
        
    def log(self, message, level='INFO'):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}"
        self.log_messages.append(log_entry)
        print(log_entry)
        
        if level == 'ERROR':
            self.execution_stats['errors'] += 1
        elif level == 'WARNING':
            self.execution_stats['warnings'] += 1
    
    def load_contacts(self):
        """Enhanced contact loading with multiple format support."""
        self.log("Loading contacts from multiple sources...")
        contacts_dir = Path(self.args.contacts)
        
        if not contacts_dir.exists():
            self.log(f"Contacts directory not found: {contacts_dir}", 'ERROR')
            return False
        
        # Load CSV files
        csv_files = list(contacts_dir.glob('*.csv'))
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                # Clean column names (remove spaces, lowercase)
                df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                
                for _, row in df.iterrows():
                    contact = {}
                    for col, value in row.items():
                        # Handle NaN values
                        contact[col] = str(value) if pd.notna(value) else ''
                    
                    contact['source'] = csv_file.name
                    contact['source_type'] = 'csv'
                    self.contacts.append(contact)
                
                self.log(f"Loaded {len(df)} contacts from {csv_file.name}")
                
            except Exception as e:
                self.log(f"Error loading CSV {csv_file}: {e}", 'ERROR')
        
        # Load Excel files
        excel_files = list(contacts_dir.glob('*.xlsx')) + list(contacts_dir.glob('*.xls'))
        for excel_file in excel_files:
            try:
                df = pd.read_excel(excel_file)
                df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                
                for _, row in df.iterrows():
                    contact = {}
                    for col, value in row.items():
                        contact[col] = str(value) if pd.notna(value) else ''
                    
                    contact['source'] = excel_file.name
                    contact['source_type'] = 'excel'
                    self.contacts.append(contact)
                
                self.log(f"Loaded {len(df)} contacts from {excel_file.name}")
                
            except Exception as e:
                self.log(f"Error loading Excel {excel_file}: {e}", 'ERROR')
        
        # Load JSON files
        json_files = list(contacts_dir.glob('*.json'))
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            item['source'] = json_file.name
                            item['source_type'] = 'json'
                            self.contacts.append(item)
                
                self.log(f"Loaded {len(data)} contacts from {json_file.name}")
                
            except Exception as e:
                self.log(f"Error loading JSON {json_file}: {e}", 'ERROR')
        
        # Apply contact source filter
        if self.args.contact_source:
            original_count = len(self.contacts)
            self.contacts = [c for c in self.contacts if c.get('source', '').startswith(self.args.contact_source)]
            self.log(f"Applied contact source filter '{self.args.contact_source}': {original_count} -> {len(self.contacts)}")
        
        self.log(f"Total contacts loaded: {len(self.contacts)}")
        return len(self.contacts) > 0
    
    def load_templates(self):
        """Load campaign templates from scheduled directory."""
        self.log("Loading campaign templates...")
        scheduled_dir = Path(self.args.scheduled)
        
        if not scheduled_dir.exists():
            self.log(f"Scheduled campaigns directory not found: {scheduled_dir}", 'ERROR')
            return False
        
        # Load text templates
        template_patterns = ['*.txt', '*.md']
        for pattern in template_patterns:
            for template_file in scheduled_dir.glob(pattern):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract subject from content if it starts with "Subject:"
                    lines = content.split('\n')
                    subject = "Campaign Email"
                    body = content
                    
                    if lines and lines[0].startswith('Subject:'):
                        subject = lines[0].replace('Subject:', '').strip()
                        body = '\n'.join(lines[1:]).strip()
                    
                    template = {
                        'name': template_file.name,
                        'subject': subject,
                        'body': body,
                        'content': content,
                        'type': 'text',
                        'path': str(template_file),
                        'variables': self.extract_template_variables(content)
                    }
                    
                    self.templates.append(template)
                    self.log(f"Loaded template: {template_file.name} ({len(template['variables'])} variables)")
                    
                except Exception as e:
                    self.log(f"Error loading template {template_file}: {e}", 'ERROR')
        
        # Apply campaign filter
        if self.args.campaign_filter:
            original_count = len(self.templates)
            self.templates = [t for t in self.templates if self.args.campaign_filter.lower() in t['name'].lower()]
            self.log(f"Applied campaign filter '{self.args.campaign_filter}': {original_count} -> {len(self.templates)}")
        
        self.log(f"Total templates loaded: {len(self.templates)}")
        return len(self.templates) > 0
    
    def extract_template_variables(self, content):
        """Extract template variables from content."""
        variables = re.findall(r'{{([^}]+)}}', content)
        return [var.strip() for var in variables]
    
    def personalize_template(self, template, contact):
        """Enhanced template personalization with multiple variables."""
        personalized_subject = template['subject']
        personalized_body = template['body']
        replacements_made = 0
        missing_variables = []
        
        for var in template['variables']:
            var_clean = var.strip()
            placeholder = f"{{{{{var}}}}}"
            
            # Try different key variations
            contact_value = None
            possible_keys = [var_clean, var_clean.lower(), var_clean.replace('_', ' '), var_clean.replace(' ', '_')]
            
            for key in possible_keys:
                if key in contact and contact[key] and str(contact[key]).strip():
                    contact_value = str(contact[key]).strip()
                    break
            
            if contact_value:
                personalized_subject = personalized_subject.replace(placeholder, contact_value)
                personalized_body = personalized_body.replace(placeholder, contact_value)
                replacements_made += 1
            else:
                missing_variables.append(var_clean)
                # Keep placeholder for missing variables or replace with default
                default_value = f"[{var_clean}]"
                personalized_subject = personalized_subject.replace(placeholder, default_value)
                personalized_body = personalized_body.replace(placeholder, default_value)
        
        return {
            'subject': personalized_subject,
            'body': personalized_body,
            'replacements_made': replacements_made,
            'missing_variables': missing_variables
        }
    
    def send_email(self, recipient_email, subject, body):
        """Send email using SMTP configuration."""
        if self.args.dry_run:
            return True  # Don't actually send in dry-run mode
        
        try:
            # Get SMTP configuration from environment
            smtp_host = os.getenv('SMTP_HOST')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_pass = os.getenv('SMTP_PASS')
            
            if not all([smtp_host, smtp_user, smtp_pass]):
                self.log("SMTP configuration incomplete - email sending disabled", 'WARNING')
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            self.log(f"Error sending email to {recipient_email}: {e}", 'ERROR')
            return False
    
    def apply_domain_filter(self):
        """Apply domain filter to contacts."""
        if not self.args.domain:
            return
        
        original_count = len(self.contacts)
        filtered_contacts = []
        
        for contact in self.contacts:
            contact_domain = contact.get('domain', '').lower()
            if contact_domain == self.args.domain.lower():
                filtered_contacts.append(contact)
        
        self.contacts = filtered_contacts
        self.log(f"Applied domain filter '{self.args.domain}': {original_count} -> {len(self.contacts)}")
    
    def execute_campaigns(self):
        """Execute all campaigns with enhanced processing."""
        self.log("Starting enhanced campaign execution...")
        self.log(f"Mode: {'DRY-RUN' if self.args.dry_run else 'LIVE'}")
        
        if not self.contacts:
            self.log("No contacts available for processing", 'ERROR')
            return False
        
        if not self.templates:
            self.log("No campaign templates available", 'ERROR')
            return False
        
        # Apply domain filter
        self.apply_domain_filter()
        
        total_processed = 0
        
        for template_idx, template in enumerate(self.templates):
            self.log(f"Processing template {template_idx + 1}/{len(self.templates)}: {template['name']}")
            
            template_processed = 0
            template_sent = 0
            batch_count = 0
            
            for contact_idx, contact in enumerate(self.contacts):
                try:
                    # Personalize template
                    personalized = self.personalize_template(template, contact)
                    
                    recipient_email = contact.get('email', contact.get('contact_email', ''))
                    recipient_name = contact.get('name', contact.get('contact_name', 'Unknown'))
                    
                    if not recipient_email or '@' not in recipient_email:
                        self.log(f"Invalid email for {recipient_name}: {recipient_email}", 'WARNING')
                        continue
                    
                    # Log personalization details
                    if self.args.debug or contact_idx < 3:
                        self.log(f"Personalized for {recipient_name}: {personalized['replacements_made']} substitutions")
                        if personalized['missing_variables']:
                            self.log(f"Missing variables: {personalized['missing_variables']}", 'WARNING')
                    
                    if self.args.dry_run:
                        # Dry-run mode: show preview
                        if self.args.debug or template_processed < 3:
                            self.log(f"--- DRY-RUN Preview for {recipient_name} ({recipient_email}) ---")
                            self.log(f"Subject: {personalized['subject']}")
                            self.log(f"Body preview (200 chars): {personalized['body'][:200]}...")
                            self.log(f"Personalizations: {personalized['replacements_made']}")
                            self.log("--- End Preview ---")
                    else:
                        # Live mode: send email
                        if self.send_email(recipient_email, personalized['subject'], personalized['body']):
                            template_sent += 1
                            self.execution_stats['emails_sent'] += 1
                    
                    template_processed += 1
                    total_processed += 1
                    self.execution_stats['contacts_processed'] += 1
                    self.execution_stats['personalizations_made'] += personalized['replacements_made']
                    
                    # Batch processing with delay
                    if template_processed % self.args.batch_size == 0:
                        batch_count += 1
                        self.log(f"Completed batch {batch_count} ({self.args.batch_size} contacts)")
                        
                        if not self.args.dry_run and self.args.batch_delay > 0:
                            self.log(f"Waiting {self.args.batch_delay} seconds before next batch...")
                            time.sleep(self.args.batch_delay)
                
                except Exception as e:
                    self.log(f"Error processing contact {contact.get('name', 'Unknown')}: {e}", 'ERROR')
                    continue
            
            self.log(f"Template '{template['name']}' completed: {template_processed} processed, {template_sent} sent")
        
        self.execution_stats['end_time'] = datetime.now()
        self.execution_stats['duration'] = (self.execution_stats['end_time'] - self.execution_stats['start_time']).total_seconds()
        
        self.log(f"Campaign execution completed: {total_processed} contacts processed")
        return True
    
    def save_execution_report(self):
        """Save comprehensive execution report."""
        tracking_dir = Path(self.args.tracking)
        tracking_dir.mkdir(parents=True, exist_ok=True)
        
        execution_report = {
            'execution_metadata': {
                'timestamp': datetime.now().isoformat(),
                'mode': 'dry-run' if self.args.dry_run else 'live',
                'executor': 'enhanced_fallback_execution.py',
                'version': '1.0'
            },
            'configuration': {
                'contacts_directory': str(self.args.contacts),
                'scheduled_directory': str(self.args.scheduled),
                'tracking_directory': str(self.args.tracking),
                'domain_filter': self.args.domain,
                'campaign_filter': self.args.campaign_filter,
                'contact_source_filter': self.args.contact_source,
                'batch_size': self.args.batch_size,
                'batch_delay': self.args.batch_delay,
                'force_validation': getattr(self.args, 'force_validation', False),
                'debug_mode': self.args.debug
            },
            'execution_statistics': self.execution_stats,
            'data_summary': {
                'total_contacts_loaded': len(self.contacts),
                'total_templates_loaded': len(self.templates),
                'contacts_by_source': self.get_contacts_by_source(),
                'templates_by_type': self.get_templates_by_type()
            },
            'logs': self.log_messages[-100:]  # Last 100 log messages
        }
        
        # Save detailed report
        report_file = tracking_dir / f'enhanced_execution_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        try:
            with open(report_file, 'w') as f:
                json.dump(execution_report, f, indent=2, default=str)
            self.log(f"Execution report saved: {report_file}")
        except Exception as e:
            self.log(f"Error saving execution report: {e}", 'ERROR')
        
        # Save simple log file
        log_file = tracking_dir / f'execution_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        try:
            with open(log_file, 'w') as f:
                f.write('\n'.join(self.log_messages))
            self.log(f"Execution log saved: {log_file}")
        except Exception as e:
            self.log(f"Error saving execution log: {e}", 'ERROR')
    
    def get_contacts_by_source(self):
        """Get contacts breakdown by source."""
        sources = {}
        for contact in self.contacts:
            source = contact.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        return sources
    
    def get_templates_by_type(self):
        """Get templates breakdown by type."""
        types = {}
        for template in self.templates:
            template_type = template.get('type', 'unknown')
            types[template_type] = types.get(template_type, 0) + 1
        return types
    
    def run(self):
        """Main execution method."""
        try:
            self.log("Enhanced Campaign Executor started")
            
            # Load data
            if not self.load_contacts():
                self.log("Failed to load contacts", 'ERROR')
                return 1
            
            if not self.load_templates():
                self.log("Failed to load templates", 'ERROR') 
                return 1
            
            # Execute campaigns
            if not self.execute_campaigns():
                self.log("Campaign execution failed", 'ERROR')
                return 1
            
            # Save report
            self.save_execution_report()
            
            # Print summary
            self.print_execution_summary()
            
            self.log("Enhanced Campaign Executor completed successfully")
            return 0
            
        except Exception as e:
            self.log(f"Fatal error in campaign executor: {e}", 'ERROR')
            return 1
    
    def print_execution_summary(self):
        """Print execution summary."""
        print("\n" + "="*60)
        print("ENHANCED CAMPAIGN EXECUTION SUMMARY")
        print("="*60)
        print(f"Mode: {'DRY-RUN' if self.args.dry_run else 'LIVE'}")
        print(f"Duration: {self.execution_stats.get('duration', 0):.1f} seconds")
        print(f"Contacts processed: {self.execution_stats['contacts_processed']}")
        print(f"Templates used: {len(self.templates)}")
        print(f"Personalizations made: {self.execution_stats['personalizations_made']}")
        if not self.args.dry_run:
            print(f"Emails sent: {self.execution_stats['emails_sent']}")
        print(f"Errors: {self.execution_stats['errors']}")
        print(f"Warnings: {self.execution_stats['warnings']}")
        
        if self.execution_stats['errors'] == 0:
            print("\n✓ EXECUTION SUCCESSFUL")
        elif self.execution_stats['errors'] < 5:
            print("\n⚠ EXECUTION COMPLETED WITH MINOR ISSUES")
        else:
            print("\n✗ EXECUTION COMPLETED WITH SIGNIFICANT ISSUES")
        
        print("="*60)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Enhanced Email Campaign Executor')
    
    # Required arguments
    parser.add_argument('--contacts', required=True, help='Contacts directory path')
    parser.add_argument('--scheduled', required=True, help='Scheduled campaigns directory')
    parser.add_argument('--tracking', required=True, help='Tracking directory')
    
    # Optional arguments
    parser.add_argument('--alerts', help='Alert email address')
    parser.add_argument('--feedback', help='Feedback email address')
    parser.add_argument('--domain', help='Target domain filter')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--campaign-filter', help='Campaign filter')
    parser.add_argument('--contact-source', help='Contact source filter')
    parser.add_argument('--force-validation', action='store_true', help='Force validation')
    parser.add_argument('--real-time-tracking', action='store_true', help='Enable real-time tracking')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size')
    parser.add_argument('--batch-delay', type=int, default=5, help='Batch delay in seconds')
    
    return parser.parse_args()


def main():
    """Main function."""
    try:
        args = parse_arguments()
        executor = EnhancedCampaignExecutor(args)
        return executor.run()
        
    except KeyboardInterrupt:
        print("\n✗ Execution interrupted by user")
        return 1
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
