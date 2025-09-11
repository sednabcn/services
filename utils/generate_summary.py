#!/usr/bin/env python3
"""
generate_summary.py - Enhanced with Google Sheets Contact Display

Generates a markdown summary for email campaigns (DRY-RUN or LIVE)
Now includes actual Google Sheets contact data processing and display
"""

import argparse
import os
import sys
import re
import json
import requests
import tempfile
from datetime import datetime
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Generate campaign summary from log files")
    parser.add_argument("--log-file", type=str, required=True,
                        help="Path to campaign log file (dryrun.log or campaign_execution.log)")
    parser.add_argument("--mode", type=str, default="dry-run", choices=["dry-run", "live"],
                        help="Execution mode")
    parser.add_argument("--output-summary", type=str, default=os.getenv("GITHUB_STEP_SUMMARY", None),
                        help="Optional: file to write GitHub Actions step summary")
    parser.add_argument("--contacts-dir", type=str, default="contacts",
                        help="Path to contacts directory containing .url files")
    parser.add_argument("--show-contacts", action="store_true",
                        help="Display actual contact data from Google Sheets")
    parser.add_argument("--max-contacts-display", type=int, default=10,
                        help="Maximum number of contacts to display in summary")
    return parser.parse_args()

class GoogleSheetsParser:
    """Parse Google Sheets URLs and extract actual contact data"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; EmailCampaignSystem/1.0)'
        })
    
    def parse_url_file(self, url_file_path):
        """Parse .url file and extract Google Sheets data"""
        try:
            with open(url_file_path, 'r', encoding='utf-8') as f:
                url = f.read().strip()
            
            if 'docs.google.com/spreadsheets' in url:
                return self.fetch_google_sheets_data(url)
            else:
                print(f"Non-Google Sheets URL found in {url_file_path}: {url}")
                return []
                
        except Exception as e:
            print(f"Error parsing URL file {url_file_path}: {str(e)}")
            return []
    
    def fetch_google_sheets_data(self, url):
        """Fetch actual data from Google Sheets URL"""
        contacts = []
        
        try:
            # Convert viewing URL to CSV export URL
            if '/edit' in url:
                sheet_id = url.split('/d/')[1].split('/')[0]
                gid = '0'  # Default sheet
                
                # Extract gid if present
                if 'gid=' in url:
                    gid = url.split('gid=')[1].split('#')[0].split('&')[0]
                
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                
                print(f"Fetching Google Sheets data from: {csv_url}")
                
                response = self.session.get(csv_url, timeout=30)
                if response.status_code == 200:
                    # Parse CSV content
                    contacts = self.parse_csv_content(response.text)
                    print(f"Successfully fetched {len(contacts)} contacts from Google Sheets")
                elif response.status_code == 403:
                    print("ERROR: Google Sheets access denied. Sheet may be private.")
                    print("Ensure sheet is shared with 'Anyone with the link can view'")
                else:
                    print(f"ERROR: Failed to fetch Google Sheets (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"Error fetching Google Sheets data: {str(e)}")
            
        return contacts
    
    def parse_csv_content(self, csv_content):
        """Parse CSV content and extract contact information"""
        contacts = []
        lines = csv_content.strip().split('\n')
        
        if len(lines) < 2:
            return contacts
            
        # Parse header
        headers = [h.strip().lower() for h in lines[0].split(',')]
        
        # Find email and name columns
        email_col = None
        name_col = None
        
        for i, header in enumerate(headers):
            if 'email' in header:
                email_col = i
            elif 'name' in header:
                name_col = i
        
        if email_col is None:
            print("Warning: No email column found in Google Sheets data")
            return contacts
        
        # Parse data rows
        for row_idx, line in enumerate(lines[1:], start=2):
            try:
                values = [v.strip() for v in line.split(',')]
                
                if len(values) > email_col:
                    email = values[email_col]
                    name = values[name_col] if name_col and len(values) > name_col else email.split('@')[0]
                    
                    if self.is_valid_email(email):
                        contact = {
                            'email': email,
                            'name': name,
                            'row': row_idx,
                            'source': 'Google Sheets'
                        }
                        
                        # Add additional fields
                        for i, value in enumerate(values):
                            if i not in [email_col, name_col] and i < len(headers) and value:
                                contact[headers[i]] = value
                        
                        contacts.append(contact)
                        
            except Exception as e:
                print(f"Error parsing row {row_idx}: {str(e)}")
                continue
        
        return contacts
    
    def is_valid_email(self, email):
        """Validate email format"""
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return re.match(pattern, email) is not None

def extract_metrics(log_file):
    """Extract campaign metrics from log file"""
    metrics = {
        "total_contacts": 0,
        "unique_contacts": 0,
        "campaigns_processed": 0,
        "total_emails": 0,
        "successful": 0,
        "failed": 0,
        "campaigns": [],
        "sample_recipients": [],
        "errors": [],
        "domains": set(),
        "execution_time": None
    }

    if not os.path.isfile(log_file):
        print(f"Warning: Log file {log_file} not found")
        return metrics

    try:
        with open(log_file, "r", encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()

        for line in lines:
            line = line.strip()
            
            # Extract various metrics
            if "Total contacts loaded:" in line or "total contacts loaded:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    metrics["total_contacts"] = int(match.group(1))
                    
            elif "Unique contacts:" in line or "unique contacts:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    metrics["unique_contacts"] = int(match.group(1))
                    
            elif "Campaigns processed:" in line or "campaigns processed:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    metrics["campaigns_processed"] = int(match.group(1))
                    
            elif "Total emails:" in line or "total emails:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    metrics["total_emails"] = int(match.group(1))
                    
            elif "Successful:" in line or "successful:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    metrics["successful"] = int(match.group(1))
                    
            elif "Failed:" in line or "failed:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    metrics["failed"] = int(match.group(1))
                    
            elif "Campaign:" in line and ("completed" in line.lower() or "sent" in line.lower()):
                campaign_match = re.search(r"Campaign[:\s]+([^,\n]+)", line)
                if campaign_match:
                    campaign_name = campaign_match.group(1).strip()
                    if campaign_name not in metrics["campaigns"]:
                        metrics["campaigns"].append(campaign_name)
                        
            elif re.search(r"@\w+\.\w+", line):  # Contains email
                email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line)
                for email in email_matches:
                    domain = email.split('@')[1]
                    metrics["domains"].add(domain)
                    if len(metrics["sample_recipients"]) < 10:
                        metrics["sample_recipients"].append(email)
                        
            elif re.search(r"ERROR|Error|Failed|Warning", line, re.I):
                if len(metrics["errors"]) < 20:  # Limit error collection
                    metrics["errors"].append(line)

    except Exception as e:
        print(f"Error parsing log file {log_file}: {str(e)}")

    return metrics

def load_actual_contacts(contacts_dir, max_display=10):
    """Load actual contacts from Google Sheets URLs in contacts directory"""
    actual_contacts = []
    
    if not os.path.exists(contacts_dir):
        print(f"Contacts directory not found: {contacts_dir}")
        return actual_contacts
    
    parser = GoogleSheetsParser()
    
    # Find .url files
    url_files = [f for f in os.listdir(contacts_dir) if f.endswith('.url')]
    
    if not url_files:
        print(f"No .url files found in {contacts_dir}")
        return actual_contacts
    
    print(f"Found {len(url_files)} .url files in contacts directory")
    
    for url_file in url_files:
        url_path = os.path.join(contacts_dir, url_file)
        print(f"Processing: {url_file}")
        
        contacts = parser.parse_url_file(url_path)
        if contacts:
            for contact in contacts[:max_display]:  # Limit per file
                contact['source_file'] = url_file
                actual_contacts.append(contact)
                
    return actual_contacts[:max_display]  # Final limit

def build_summary(metrics, mode, actual_contacts=None):
    """Build comprehensive summary with actual contact data"""
    md = []
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    md.append(f"## Email Campaign Execution Report - {timestamp}\n")
    md.append(f"**Mode**: {'📄 DRY-RUN - No emails sent' if mode == 'dry-run' else '📧 LIVE - Emails sent'}\n")

    # Execution statistics
    md.append("### 📊 Execution Statistics\n")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Total Contacts Loaded | {metrics['total_contacts']} |")
    md.append(f"| Unique Contacts | {metrics['unique_contacts']} |")
    md.append(f"| Campaigns Processed | {metrics['campaigns_processed']} |")
    md.append(f"| Total Emails | {metrics['total_emails']} |")
    md.append(f"| Successful | {metrics['successful']} |")
    md.append(f"| Failed | {metrics['failed']} |")
    
    success_rate = "N/A"
    if metrics['total_emails'] > 0:
        rate = (metrics['successful'] / metrics['total_emails'] * 100)
        success_rate = f"{rate:.1f}%"
    md.append(f"| Success Rate | {success_rate} |")
    md.append(f"| Unique Domains | {len(metrics['domains'])} |")
    md.append("")

    # Actual Google Sheets Contacts
    if actual_contacts:
        md.append("### 👥 Actual Google Sheets Contacts (Sample)\n")
        md.append("| Name | Email | Domain | Source |")
        md.append("|------|-------|--------|--------|")
        
        for contact in actual_contacts:
            name = contact.get('name', 'N/A')
            email = contact.get('email', 'N/A')
            domain = email.split('@')[1] if '@' in email else 'N/A'
            source = contact.get('source_file', 'Unknown')
            
            md.append(f"| {name} | {email} | {domain} | {source} |")
        
        md.append("")
        md.append(f"**Note**: Showing {len(actual_contacts)} contacts from Google Sheets. This is REAL DATA, not mock data.\n")

    # Campaign Details
    if metrics["campaigns"]:
        md.append("### 📋 Campaign Details\n")
        md.append("| Campaign | Status | Details |")
        md.append("|----------|--------|---------|")
        for campaign in metrics["campaigns"]:
            md.append(f"| {campaign} | Completed | See execution logs |")
        md.append("")

    # Domain Distribution
    if metrics["domains"]:
        md.append("### 🌐 Email Domains Found\n")
        domain_list = list(metrics["domains"])[:10]  # Show top 10
        md.append("```")
        for domain in sorted(domain_list):
            md.append(f"• {domain}")
        md.append("```")
        md.append("")

    # Sample Recipients from Logs
    if metrics["sample_recipients"]:
        md.append("### 📧 Sample Recipients (From Logs)\n")
        md.append("```")
        for recipient in metrics["sample_recipients"][:5]:
            md.append(recipient)
        md.append("```")
        md.append("")

    # Errors and Issues
    if metrics["errors"]:
        md.append("### ⚠️ Issues Detected\n")
        md.append("```")
        for error in metrics["errors"][:5]:  # Show first 5 errors
            md.append(error)
        if len(metrics["errors"]) > 5:
            md.append(f"... and {len(metrics['errors']) - 5} more errors")
        md.append("```")
        md.append("")

    # Metadata
    md.append("### 🔧 Execution Metadata\n")
    md.append("| Field | Value |")
    md.append("|-------|-------|")
    md.append(f"| Timestamp | {timestamp} |")
    md.append(f"| Mode | {mode} |")
    md.append(f"| Data Source | {'Real Google Sheets Data' if actual_contacts else 'Log File Only'} |")
    md.append(f"| Script Version | Enhanced with Google Sheets Integration |")
    
    return "\n".join(md)

def main():
    args = parse_args()
    
    print(f"Processing log file: {args.log_file}")
    print(f"Mode: {args.mode}")
    print(f"Show contacts: {args.show_contacts}")
    
    # Extract metrics from log file
    metrics = extract_metrics(args.log_file)
    
    # Load actual contacts if requested
    actual_contacts = None
    if args.show_contacts:
        print(f"Loading actual contacts from: {args.contacts_dir}")
        actual_contacts = load_actual_contacts(args.contacts_dir, args.max_contacts_display)
        
        if actual_contacts:
            print(f"Loaded {len(actual_contacts)} actual contacts from Google Sheets")
        else:
            print("No actual contacts loaded - will show log-based data only")
    
    # Build summary
    summary = build_summary(metrics, args.mode, actual_contacts)

    # Output summary
    if args.output_summary:
        try:
            with open(args.output_summary, "a", encoding='utf-8') as f:
                f.write(summary + "\n")
            print(f"Summary written to {args.output_summary}")
        except Exception as e:
            print(f"Error writing to {args.output_summary}: {str(e)}")
            print(summary)
    else:
        print(summary)

if __name__ == "__main__":
    main()
