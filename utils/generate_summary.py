#!/usr/bin/env python3
"""
generate_summary.py - Enhanced with Google Sheets Contact Display (Fixed for GitHub Actions)

Generates a markdown summary for email campaigns (DRY-RUN or LIVE)
Now includes actual Google Sheets contact data processing and display with fallback support
"""

import argparse
import os
import sys
import re
import json
import urllib.request
import urllib.error
import csv
from datetime import datetime
from pathlib import Path

# Check for optional libraries
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Info: Using urllib fallback instead of requests")

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
    """Parse Google Sheets URLs and extract actual contact data with fallback support"""
    
    def __init__(self):
        self.timeout = 15
        if REQUESTS_AVAILABLE:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (compatible; EmailCampaignSystem/1.0)'
            })
        else:
            self.session = None
    
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
        """Fetch actual data from Google Sheets URL with fallback methods"""
        contacts = []
        
        try:
            # Convert viewing URL to CSV export URL
            if '/edit' in url or '/d/' in url:
                sheet_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
                if not sheet_id_match:
                    print(f"Could not extract sheet ID from URL: {url}")
                    return contacts
                
                sheet_id = sheet_id_match.group(1)
                gid = '0'  # Default sheet
                
                # Extract gid if present
                if 'gid=' in url:
                    gid_match = re.search(r'gid=([0-9]+)', url)
                    if gid_match:
                        gid = gid_match.group(1)
                
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
                
                print(f"Fetching Google Sheets data from: {csv_url}")
                
                # Try requests first, then urllib fallback
                csv_content = None
                
                if REQUESTS_AVAILABLE and self.session:
                    try:
                        response = self.session.get(csv_url, timeout=self.timeout)
                        if response.status_code == 200:
                            csv_content = response.text
                            print(f"Successfully fetched via requests (HTTP {response.status_code})")
                        elif response.status_code == 403:
                            print("ERROR: Google Sheets access denied. Sheet may be private.")
                            print("Ensure sheet is shared with 'Anyone with the link can view'")
                        else:
                            print(f"ERROR: Failed to fetch Google Sheets via requests (HTTP {response.status_code})")
                    except Exception as e:
                        print(f"Requests method failed: {e}, trying urllib fallback...")
                
                # urllib fallback
                if csv_content is None:
                    try:
                        with urllib.request.urlopen(csv_url, timeout=self.timeout) as response:
                            if response.status == 200:
                                csv_content = response.read().decode('utf-8')
                                print(f"Successfully fetched via urllib (HTTP {response.status})")
                            elif response.status == 403:
                                print("ERROR: Google Sheets access denied. Sheet may be private.")
                                print("Ensure sheet is shared with 'Anyone with the link can view'")
                            else:
                                print(f"ERROR: Failed to fetch Google Sheets via urllib (HTTP {response.status})")
                    except urllib.error.HTTPError as e:
                        if e.code == 403:
                            print("ERROR: Google Sheets access denied (urllib). Check sharing settings.")
                        else:
                            print(f"ERROR: urllib HTTP error {e.code}")
                    except Exception as e:
                        print(f"urllib method also failed: {e}")
                
                # Parse CSV content if we got it
                if csv_content:
                    contacts = self.parse_csv_content(csv_content)
                    print(f"Successfully parsed {len(contacts)} contacts from Google Sheets")
                else:
                    print("Failed to fetch Google Sheets data with all methods")
                
        except Exception as e:
            print(f"Error fetching Google Sheets data: {str(e)}")
            
        return contacts
    
    def parse_csv_content(self, csv_content):
        """Parse CSV content and extract contact information with robust error handling"""
        contacts = []
        
        try:
            lines = csv_content.strip().split('\n')
            
            if len(lines) < 2:
                print("Warning: Google Sheets appears to have no data rows")
                return contacts
                
            # Use csv module for proper parsing
            csv_reader = csv.reader(lines)
            
            # Get header row
            try:
                headers = next(csv_reader)
                headers = [h.strip().lower() for h in headers]
            except StopIteration:
                print("Warning: No header row found in CSV data")
                return contacts
            
            # Find important columns
            email_col = None
            name_col = None
            company_col = None
            
            for i, header in enumerate(headers):
                if any(keyword in header for keyword in ['email', 'e-mail', 'mail']):
                    email_col = i
                elif any(keyword in header for keyword in ['name', 'contact', 'person']):
                    name_col = i
                elif any(keyword in header for keyword in ['company', 'organization', 'org']):
                    company_col = i
            
            if email_col is None:
                print("Warning: No email column found in Google Sheets data")
                print(f"Available headers: {headers}")
                return contacts
            
            # Parse data rows
            row_num = 2  # Start from 2 (1 is header)
            for row in csv_reader:
                try:
                    if len(row) <= email_col:
                        continue
                    
                    email = row[email_col].strip() if row[email_col] else ""
                    
                    if self.is_valid_email(email):
                        # Extract name
                        name = ""
                        if name_col is not None and len(row) > name_col and row[name_col]:
                            name = row[name_col].strip()
                        else:
                            # Fallback: use email username as name
                            name = email.split('@')[0].replace('.', ' ').title()
                        
                        # Extract company
                        company = ""
                        if company_col is not None and len(row) > company_col and row[company_col]:
                            company = row[company_col].strip()
                        
                        contact = {
                            'email': email,
                            'name': name,
                            'company': company,
                            'domain': email.split('@')[1],
                            'row': row_num,
                            'source': 'Google Sheets'
                        }
                        
                        # Add additional fields
                        for i, value in enumerate(row):
                            if i < len(headers) and i not in [email_col, name_col, company_col] and value and value.strip():
                                clean_header = headers[i].replace(' ', '_').replace('-', '_')
                                contact[clean_header] = value.strip()
                        
                        contacts.append(contact)
                        
                except Exception as e:
                    print(f"Error parsing row {row_num}: {str(e)}")
                    continue
                finally:
                    row_num += 1
            
        except Exception as e:
            print(f"Error parsing CSV content: {str(e)}")
        
        return contacts
    
    def is_valid_email(self, email):
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return re.match(pattern, email) is not None

def extract_metrics(log_file):
    """Extract campaign metrics from log file with improved parsing"""
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
        "warnings": [],
        "domains": set(),
        "execution_time": None,
        "start_time": None,
        "end_time": None
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
            
            # Extract timestamps
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', line)
            if timestamp_match:
                if not metrics["start_time"]:
                    metrics["start_time"] = timestamp_match.group(1)
                metrics["end_time"] = timestamp_match.group(1)
            
            # Extract various metrics with multiple patterns
            patterns = [
                (r"(?:Total\s+)?contacts?\s+loaded[:\s]*(\d+)", "total_contacts"),
                (r"(?:Total\s+)?(\d+)\s+contacts?\s+loaded", "total_contacts"),
                (r"unique\s+contacts[:\s]*(\d+)", "unique_contacts"),
                (r"campaigns?\s+processed[:\s]*(\d+)", "campaigns_processed"),
                (r"processed[:\s]*(\d+)\s+campaigns?", "campaigns_processed"),
                (r"(?:total\s+)?emails?[:\s]*(\d+)", "total_emails"),
                (r"successful[:\s]*(\d+)", "successful"),
                (r"sent[:\s]*(\d+)", "successful"),
                (r"failed[:\s]*(\d+)", "failed"),
            ]
            
            for pattern, metric_key in patterns:
                match = re.search(pattern, line, re.I)
                if match:
                    try:
                        value = int(match.group(1))
                        metrics[metric_key] = max(metrics[metric_key], value)  # Take the highest value found
                    except ValueError:
                        continue
            
            # Extract campaign names
            campaign_patterns = [
                r"Campaign[:\s]+([^,\n\:]+?)(?:\s+(?:completed|processed|sent|finished))",
                r"Processing\s+campaign[:\s]+([^,\n\:]+)",
                r"=== CAMPAIGN[:\s]+([^=]+) ===",
            ]
            
            for pattern in campaign_patterns:
                match = re.search(pattern, line, re.I)
                if match:
                    campaign_name = match.group(1).strip()
                    if campaign_name and campaign_name not in metrics["campaigns"]:
                        metrics["campaigns"].append(campaign_name)
            
            # Extract email addresses and domains
            email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line)
            for email in email_matches:
                domain = email.split('@')[1].lower()
                metrics["domains"].add(domain)
                if len(metrics["sample_recipients"]) < 10:
                    metrics["sample_recipients"].append(email)
            
            # Categorize messages
            if re.search(r"ERROR|Error|CRITICAL|FATAL", line):
                if len(metrics["errors"]) < 10:  # Limit error collection
                    metrics["errors"].append(line)
            elif re.search(r"WARNING|Warning|WARN", line):
                if len(metrics["warnings"]) < 10:
                    metrics["warnings"].append(line)

        # Calculate execution time if we have start and end
        if metrics["start_time"] and metrics["end_time"]:
            try:
                from datetime import datetime
                start = datetime.fromisoformat(metrics["start_time"].replace('T', ' '))
                end = datetime.fromisoformat(metrics["end_time"].replace('T', ' '))
                duration = end - start
                metrics["execution_time"] = str(duration)
            except:
                pass

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
    try:
        url_files = [f for f in os.listdir(contacts_dir) if f.endswith('.url')]
    except Exception as e:
        print(f"Error reading contacts directory {contacts_dir}: {e}")
        return actual_contacts
    
    if not url_files:
        print(f"No .url files found in {contacts_dir}")
        return actual_contacts
    
    print(f"Found {len(url_files)} .url files in contacts directory")
    
    for url_file in url_files:
        url_path = os.path.join(contacts_dir, url_file)
        print(f"Processing: {url_file}")
        
        try:
            contacts = parser.parse_url_file(url_path)
            if contacts:
                for contact in contacts[:max_display]:  # Limit per file
                    contact['source_file'] = url_file
                    actual_contacts.append(contact)
                    
                    if len(actual_contacts) >= max_display:
                        break
            else:
                print(f"No contacts loaded from {url_file}")
                
        except Exception as e:
            print(f"Error processing {url_file}: {e}")
            continue
        
        if len(actual_contacts) >= max_display:
            break
                
    return actual_contacts[:max_display]  # Final limit

def build_summary(metrics, mode, actual_contacts=None):
    """Build comprehensive summary with actual contact data"""
    md = []
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Title with clear mode indication
    mode_emoji = "🔄" if mode == "dry-run" else "📧"
    mode_text = "DRY-RUN - No emails sent" if mode == "dry-run" else "LIVE - Emails sent"
    
    md.append(f"## {mode_emoji} Email Campaign Execution Report")
    md.append(f"**Generated:** {timestamp}")
    md.append(f"**Mode:** {mode_text}")
    md.append("")

    # Execution statistics
    md.append("### 📊 Execution Statistics")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Total Contacts Loaded | {metrics['total_contacts']} |")
    
    if metrics['unique_contacts'] > 0:
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
    
    if metrics['execution_time']:
        md.append(f"| Execution Time | {metrics['execution_time']} |")
    
    md.append("")

    # Actual Google Sheets Contacts
    if actual_contacts:
        md.append("### 👥 Actual Google Sheets Contacts (Sample)")
        md.append("")
        md.append("| Name | Email | Domain | Company | Source |")
        md.append("|------|-------|--------|---------|--------|")
        
        for contact in actual_contacts:
            name = contact.get('name', 'N/A')
            email = contact.get('email', 'N/A')
            domain = contact.get('domain', email.split('@')[1] if '@' in email else 'N/A')
            company = contact.get('company', 'N/A')
            source = contact.get('source_file', 'Unknown')
            
            md.append(f"| {name} | {email} | {domain} | {company} | {source} |")
        
        md.append("")
        md.append(f"**✅ Real Data Confirmation:** Showing {len(actual_contacts)} actual contacts from Google Sheets. This is LIVE DATA, not mock data.")
        md.append("")

    else:
        md.append("### ⚠️ Contact Data Status")
        md.append("")
        md.append("No real contact data was loaded from Google Sheets. Possible reasons:")
        md.append("- No .url files found in contacts directory")
        md.append("- Google Sheets not accessible (check sharing settings)")  
        md.append("- Network connectivity issues")
        md.append("")

    # Campaign Details
    if metrics["campaigns"]:
        md.append("### 📋 Campaign Details")
        md.append("")
        md.append("| Campaign | Status | Details |")
        md.append("|----------|--------|---------|")
        for campaign in metrics["campaigns"]:
            status = "✅ Completed" if mode == "live" else "🔄 Simulated"
            md.append(f"| {campaign} | {status} | See execution logs |")
        md.append("")

    # Domain Distribution
    if metrics["domains"]:
        md.append("### 🌐 Email Domains Found")
        md.append("")
        domain_list = list(metrics["domains"])[:15]  # Show top 15
        md.append("```")
        for domain in sorted(domain_list):
            md.append(f"• {domain}")
        if len(metrics["domains"]) > 15:
            md.append(f"... and {len(metrics['domains']) - 15} more domains")
        md.append("```")
        md.append("")

    # Sample Recipients from Logs
    if metrics["sample_recipients"]:
        md.append("### 📧 Sample Recipients (From Logs)")
        md.append("")
        md.append("```")
        for recipient in metrics["sample_recipients"][:8]:
            md.append(recipient)
        if len(metrics["sample_recipients"]) > 8:
            md.append(f"... and {len(metrics['sample_recipients']) - 8} more")
        md.append("```")
        md.append("")

    # Issues and warnings
    if metrics["errors"]:
        md.append("### ❌ Errors Detected")
        md.append("")
        md.append("```")
        for error in metrics["errors"][:5]:  # Show first 5 errors
            md.append(error)
        if len(metrics["errors"]) > 5:
            md.append(f"... and {len(metrics['errors']) - 5} more errors")
        md.append("```")
        md.append("")

    if metrics["warnings"]:
        md.append("### ⚠️ Warnings")
        md.append("")
        md.append("```")
        for warning in metrics["warnings"][:3]:  # Show first 3 warnings
            md.append(warning)
        if len(metrics["warnings"]) > 3:
            md.append(f"... and {len(metrics['warnings']) - 3} more warnings")
        md.append("```")
        md.append("")

    # Metadata
    md.append("### 🔧 Execution Metadata")
    md.append("")
    md.append("| Field | Value |")
    md.append("|-------|-------|")
    md.append(f"| Timestamp | {timestamp} |")
    md.append(f"| Mode | {mode.upper()} |")
    md.append(f"| Data Source | {'Real Google Sheets Data' if actual_contacts else 'Log File Only'} |")
    md.append(f"| Contact Sources | {len(actual_contacts) if actual_contacts else 0} contacts from Google Sheets |")
    md.append(f"| Script Version | Enhanced with Google Sheets Integration + GitHub Actions Compatible |")
    
    if metrics['start_time']:
        md.append(f"| Execution Started | {metrics['start_time']} |")
    if metrics['end_time']:
        md.append(f"| Execution Completed | {metrics['end_time']} |")
    
    md.append("")
    
    return "\n".join(md)

def main():
    args = parse_args()
    
    print(f"Processing log file: {args.log_file}")
    print(f"Mode: {args.mode}")
    print(f"Show contacts: {args.show_contacts}")
    print(f"Output file: {args.output_summary}")
    
    # Extract metrics from log file
    print("Extracting metrics from log file...")
    metrics = extract_metrics(args.log_file)
    print(f"Found {metrics['campaigns_processed']} campaigns, {metrics['total_contacts']} contacts")
    
    # Load actual contacts if requested
    actual_contacts = None
    if args.show_contacts:
        print(f"Loading actual contacts from: {args.contacts_dir}")
        actual_contacts = load_actual_contacts(args.contacts_dir, args.max_contacts_display)
        
        if actual_contacts:
            print(f"✅ Loaded {len(actual_contacts)} actual contacts from Google Sheets")
        else:
            print("⚠️ No actual contacts loaded - will show log-based data only")
    
    # Build summary
    print("Building summary report...")
    summary = build_summary(metrics, args.mode, actual_contacts)

    # Output summary
    if args.output_summary:
        try:
            # Ensure directory exists
            output_path = Path(args.output_summary)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(args.output_summary, "w", encoding='utf-8') as f:
                f.write(summary + "\n")
            print(f"✅ Summary written to {args.output_summary}")
        except Exception as e:
            print(f"❌ Error writing to {args.output_summary}: {str(e)}")
            print("Outputting to stdout instead:")
            print(summary)
    else:
        print("No output file specified, printing summary:")
        print(summary)

    print("Summary generation completed successfully")

if __name__ == "__main__":
    main()
